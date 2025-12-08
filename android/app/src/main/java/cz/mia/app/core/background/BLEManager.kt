package cz.mia.app.core.background

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattService
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Build
import android.os.ParcelUuid
import android.util.Log
import cz.mia.app.core.networking.Backoff
import cz.mia.app.utils.PermissionHelper
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume

/**
 * BLE connection states for OBD-II adapter communication.
 */
sealed class BleConnectionState {
    object Disconnected : BleConnectionState()
    object Scanning : BleConnectionState()
    object Connecting : BleConnectionState()
    object Connected : BleConnectionState()
    data class Error(val message: String) : BleConnectionState()
}

/**
 * Discovered BLE device info.
 */
data class BleDeviceInfo(
    val name: String?,
    val address: String,
    val rssi: Int
)

/**
 * BLE Manager interface for OBD-II Bluetooth communication.
 */
interface BLEManager {
    /** Current connection state */
    val connectionState: StateFlow<BleConnectionState>
    
    /** List of discovered OBD devices during scanning */
    val discoveredDevices: StateFlow<List<BleDeviceInfo>>
    
    /** Initialize BLE manager and check for Bluetooth availability */
    suspend fun initialize()
    
    /** Disconnect from current device */
    suspend fun disconnect()
    
    /** Connect to device with retry logic */
    suspend fun connectWithRetry(deviceAddress: String): Boolean
    
    /** Start scanning for OBD-II Bluetooth devices */
    suspend fun startScanning()
    
    /** Stop scanning */
    fun stopScanning()
    
    /** Send OBD command and receive response */
    suspend fun sendCommand(command: String): String?
    
    /** Check if connected to a device */
    fun isConnected(): Boolean
    
    /** Cleanup resources and cancel all operations */
    suspend fun cleanup() {
        // Default no-op implementation
    }
}

@Singleton
class BLEManagerImpl @Inject constructor(
    @ApplicationContext private val context: Context
) : BLEManager {

    companion object {
        private const val TAG = "BLEManager"
        
        // Standard SPP UUID for ELM327/OBD-II adapters
        val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
        
        // Nordic UART Service UUIDs (used by some OBD adapters)
        val NUS_SERVICE_UUID: UUID = UUID.fromString("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        val NUS_TX_CHAR_UUID: UUID = UUID.fromString("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
        val NUS_RX_CHAR_UUID: UUID = UUID.fromString("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
        
        // Common OBD adapter device names
        private val OBD_DEVICE_NAMES = listOf("OBD", "ELM327", "VGATE", "VEEPEAK", "BAFX")
        
        private const val SCAN_TIMEOUT_MS = 10_000L
        private const val COMMAND_TIMEOUT_MS = 5_000L
        private const val CONNECTION_TIMEOUT_MS = 15_000L
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    private val bluetoothManager: BluetoothManager? = 
        context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager?.adapter
    private var bluetoothLeScanner: BluetoothLeScanner? = null
    
    private var bluetoothGatt: BluetoothGatt? = null
    private var txCharacteristic: BluetoothGattCharacteristic? = null
    private var rxCharacteristic: BluetoothGattCharacteristic? = null
    
    private val _connectionState = MutableStateFlow<BleConnectionState>(BleConnectionState.Disconnected)
    override val connectionState: StateFlow<BleConnectionState> = _connectionState.asStateFlow()
    
    private val _discoveredDevices = MutableStateFlow<List<BleDeviceInfo>>(emptyList())
    override val discoveredDevices: StateFlow<List<BleDeviceInfo>> = _discoveredDevices.asStateFlow()
    
    private val responseChannel = Channel<String>(Channel.BUFFERED)
    private var connectionDeferred: CompletableDeferred<Boolean>? = null
    
    private val responseBuffer = StringBuilder()
    
    private val gattCallback = object : BluetoothGattCallback() {
        @SuppressLint("MissingPermission")
        override fun onConnectionStateChange(gatt: BluetoothGatt?, status: Int, newState: Int) {
            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    Log.d(TAG, "Connected to GATT server")
                    _connectionState.value = BleConnectionState.Connecting
                    gatt?.discoverServices()
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    Log.d(TAG, "Disconnected from GATT server")
                    _connectionState.value = BleConnectionState.Disconnected
                    connectionDeferred?.complete(false)
                    cleanup()
                }
            }
        }
        
        @SuppressLint("MissingPermission")
        override fun onServicesDiscovered(gatt: BluetoothGatt?, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d(TAG, "Services discovered")
                
                // Find the UART service and characteristics
                val nusService = gatt?.getService(NUS_SERVICE_UUID)
                if (nusService != null) {
                    txCharacteristic = nusService.getCharacteristic(NUS_TX_CHAR_UUID)
                    rxCharacteristic = nusService.getCharacteristic(NUS_RX_CHAR_UUID)
                    
                    // Enable notifications on RX characteristic
                    rxCharacteristic?.let { rx ->
                        gatt.setCharacteristicNotification(rx, true)
                        val descriptor = rx.getDescriptor(
                            UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
                        )
                        descriptor?.let {
                            it.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                            gatt.writeDescriptor(it)
                        }
                    }
                    
                    _connectionState.value = BleConnectionState.Connected
                    connectionDeferred?.complete(true)
                } else {
                    // Try to find any writable characteristic for OBD commands
                    gatt?.services?.forEach { service ->
                        service.characteristics?.forEach { char ->
                            if (char.properties and BluetoothGattCharacteristic.PROPERTY_WRITE != 0) {
                                txCharacteristic = char
                            }
                            if (char.properties and BluetoothGattCharacteristic.PROPERTY_NOTIFY != 0) {
                                rxCharacteristic = char
                                gatt.setCharacteristicNotification(char, true)
                            }
                        }
                    }
                    
                    if (txCharacteristic != null) {
                        _connectionState.value = BleConnectionState.Connected
                        connectionDeferred?.complete(true)
                    } else {
                        _connectionState.value = BleConnectionState.Error("No compatible UART service found")
                        connectionDeferred?.complete(false)
                    }
                }
            } else {
                Log.e(TAG, "Service discovery failed with status: $status")
                _connectionState.value = BleConnectionState.Error("Service discovery failed")
                connectionDeferred?.complete(false)
            }
        }
        
        @Deprecated("Deprecated in API 33")
        override fun onCharacteristicChanged(
            gatt: BluetoothGatt?,
            characteristic: BluetoothGattCharacteristic?
        ) {
            characteristic?.value?.let { data ->
                handleIncomingData(String(data, Charsets.UTF_8))
            }
        }
        
        override fun onCharacteristicChanged(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
            value: ByteArray
        ) {
            handleIncomingData(String(value, Charsets.UTF_8))
        }
    }
    
    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult?) {
            result?.device?.let { device ->
                @SuppressLint("MissingPermission")
                val deviceInfo = BleDeviceInfo(
                    name = device.name,
                    address = device.address,
                    rssi = result.rssi
                )
                
                // Filter for OBD-related devices
                val isObdDevice = device.name?.let { name ->
                    OBD_DEVICE_NAMES.any { name.contains(it, ignoreCase = true) }
                } ?: false
                
                if (isObdDevice) {
                    val currentList = _discoveredDevices.value.toMutableList()
                    if (currentList.none { it.address == deviceInfo.address }) {
                        currentList.add(deviceInfo)
                        _discoveredDevices.value = currentList
                    }
                }
            }
        }
        
        override fun onScanFailed(errorCode: Int) {
            Log.e(TAG, "Scan failed with error: $errorCode")
            _connectionState.value = BleConnectionState.Error("Scan failed: $errorCode")
        }
    }
    
    private fun handleIncomingData(data: String) {
        responseBuffer.append(data)
        
        // OBD responses typically end with ">" prompt
        if (data.contains(">") || data.contains("\r")) {
            val response = responseBuffer.toString()
                .replace("\r", "")
                .replace("\n", "")
                .replace(">", "")
                .trim()
            
            if (response.isNotEmpty()) {
                scope.launch {
                    responseChannel.send(response)
                }
            }
            responseBuffer.clear()
        }
    }
    
    @SuppressLint("MissingPermission")
    override suspend fun initialize() = withContext(Dispatchers.Main) {
        if (bluetoothAdapter == null) {
            _connectionState.value = BleConnectionState.Error("Bluetooth not supported")
            return@withContext
        }
        
        if (!bluetoothAdapter.isEnabled) {
            _connectionState.value = BleConnectionState.Error("Bluetooth is disabled")
            return@withContext
        }
        
        bluetoothLeScanner = bluetoothAdapter.bluetoothLeScanner
        Log.d(TAG, "BLE Manager initialized")
    }
    
    @SuppressLint("MissingPermission")
    override suspend fun startScanning() {
        withContext(Dispatchers.Main) {
            if (bluetoothLeScanner == null) {
                initialize()
            }
            
            _discoveredDevices.value = emptyList()
            _connectionState.value = BleConnectionState.Scanning
            
            val scanSettings = ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .build()
            
            try {
                bluetoothLeScanner?.startScan(null, scanSettings, scanCallback)
                Log.d(TAG, "Started BLE scanning")
                
                // Auto-stop after timeout
                scope.launch {
                    delay(SCAN_TIMEOUT_MS)
                    stopScanning()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start scanning", e)
                _connectionState.value = BleConnectionState.Error("Scan failed: ${e.message}")
            }
        }
    }
    
    @SuppressLint("MissingPermission")
    override fun stopScanning() {
        try {
            bluetoothLeScanner?.stopScan(scanCallback)
            if (_connectionState.value is BleConnectionState.Scanning) {
                _connectionState.value = BleConnectionState.Disconnected
            }
            Log.d(TAG, "Stopped BLE scanning")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to stop scanning", e)
        }
    }
    
    @SuppressLint("MissingPermission")
    override suspend fun connectWithRetry(deviceAddress: String): Boolean {
        val delays = Backoff.exponential(baseMs = 250, maxMs = 8000, attempts = 6)
        
        for (d in delays) {
            if (tryConnect(deviceAddress)) {
                return true
            }
            delay(d)
        }
        return false
    }
    
    @SuppressLint("MissingPermission")
    private suspend fun tryConnect(address: String): Boolean = withContext(Dispatchers.Main) {
        stopScanning()
        
        val device = bluetoothAdapter?.getRemoteDevice(address)
        if (device == null) {
            _connectionState.value = BleConnectionState.Error("Device not found")
            return@withContext false
        }
        
        connectionDeferred = CompletableDeferred()
        _connectionState.value = BleConnectionState.Connecting
        
        try {
            bluetoothGatt = device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
            
            val result = withTimeoutOrNull(CONNECTION_TIMEOUT_MS) {
                connectionDeferred?.await() ?: false
            } ?: false
            
            if (result) {
                // Initialize OBD adapter with basic commands
                delay(500)
                sendCommand("ATZ")  // Reset
                delay(1000)
                sendCommand("ATE0") // Echo off
                sendCommand("ATL0") // Linefeeds off
                sendCommand("ATS0") // Spaces off
                sendCommand("ATSP0") // Auto protocol
            }
            
            return@withContext result
        } catch (e: Exception) {
            Log.e(TAG, "Connection failed", e)
            _connectionState.value = BleConnectionState.Error("Connection failed: ${e.message}")
            return@withContext false
        }
    }
    
    @SuppressLint("MissingPermission")
    override suspend fun disconnect() {
        withContext(Dispatchers.Main) {
            try {
                bluetoothGatt?.disconnect()
                cleanup()
                _connectionState.value = BleConnectionState.Disconnected
            } catch (e: Exception) {
                Log.e(TAG, "Disconnect failed", e)
            }
        }
    }
    
    @SuppressLint("MissingPermission")
    override suspend fun cleanup() {
        withContext(Dispatchers.Main) {
            bluetoothGatt?.close()
            bluetoothGatt = null
            txCharacteristic = null
            rxCharacteristic = null
            responseBuffer.clear()
        }
    }
    
    @SuppressLint("MissingPermission")
    override suspend fun sendCommand(command: String): String? = withContext(Dispatchers.IO) {
        val gatt = bluetoothGatt
        val tx = txCharacteristic
        
        if (gatt == null || tx == null) {
            Log.e(TAG, "Not connected or no TX characteristic")
            return@withContext null
        }
        
        try {
            val commandWithCR = "$command\r"
            val bytes = commandWithCR.toByteArray(Charsets.UTF_8)

            withContext(Dispatchers.Main) {
                try {
                    // Use proper API versioning for Android 13+
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        val result = gatt.writeCharacteristic(tx, bytes, BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT)
                        if (result != 0) { // BluetoothStatusCodes.SUCCESS = 0
                            Log.e(TAG, "Failed to initiate write for command: $command, status: $result")
                            return@withContext null
                        }
                    } else {
                        @Suppress("DEPRECATION")
                        tx.value = bytes
                        @Suppress("DEPRECATION")
                        val success = gatt.writeCharacteristic(tx)
                        if (!success) {
                            Log.e(TAG, "Failed to initiate write for command: $command")
                            return@withContext null
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Exception during write for command: $command", e)
                    return@withContext null
                }
            }

            // Wait for response with timeout
            return@withContext withTimeoutOrNull(COMMAND_TIMEOUT_MS) {
                responseChannel.receive()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to send command: $command", e)
            return@withContext null
        }
    }
    
    override fun isConnected(): Boolean = _connectionState.value is BleConnectionState.Connected
}

// Dummy import for descriptor constant
private object BluetoothGattDescriptor {
    val ENABLE_NOTIFICATION_VALUE: ByteArray = byteArrayOf(0x01, 0x00)
}
