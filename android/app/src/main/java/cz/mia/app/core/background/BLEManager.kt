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

    /** Cleanup resources */
    suspend fun cleanup()
}

@Singleton
class BLEManagerImpl @Inject constructor(
    @ApplicationContext private val context: Context
) : BLEManager {

    companion object {
        private const val TAG = "BLEManager"

        // Standard SPP UUID for ELM327/OBD-II adapters
        val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
    }

    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var retryCount = 0
    private val maxRetries = 3

    // Bluetooth components
    private var bluetoothAdapter: BluetoothAdapter? = null
    private var bluetoothLeScanner: BluetoothLeScanner? = null
    private var bluetoothGatt: BluetoothGatt? = null

    // BLE characteristics
    private var txCharacteristic: BluetoothGattCharacteristic? = null
    private var rxCharacteristic: BluetoothGattCharacteristic? = null

    // State management
    private val _connectionState = MutableStateFlow<BleConnectionState>(BleConnectionState.Disconnected)
    override val connectionState: StateFlow<BleConnectionState> = _connectionState.asStateFlow()

    private val _discoveredDevices = MutableStateFlow<List<BleDeviceInfo>>(emptyList())
    override val discoveredDevices: StateFlow<List<BleDeviceInfo>> = _discoveredDevices.asStateFlow()

    // Communication buffers
    private val responseBuffer = mutableListOf<ByteArray>()
    private val commandChannel = Channel<String>(Channel.UNLIMITED)
    private val responseChannel = Channel<String>(Channel.UNLIMITED)

    override suspend fun initialize() {
        withContext(Dispatchers.Main) {
            try {
                val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
                bluetoothAdapter = bluetoothManager.adapter
                bluetoothLeScanner = bluetoothAdapter?.bluetoothLeScanner

                if (bluetoothAdapter == null || bluetoothLeScanner == null) {
                    _connectionState.value = BleConnectionState.Error("Bluetooth not available")
                    return@withContext
                }

                if (!bluetoothAdapter!!.isEnabled) {
                    _connectionState.value = BleConnectionState.Error("Bluetooth is disabled")
                    return@withContext
                }

                Log.i(TAG, "BLE Manager initialized successfully")

            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize BLE", e)
                _connectionState.value = BleConnectionState.Error("Initialization failed: ${e.message}")
            }
        }
    }

    @SuppressLint("MissingPermission")
    override suspend fun startScanning() {
        if (!PermissionHelper.hasBluetoothPermissions(context)) {
            _connectionState.value = BleConnectionState.Error("Missing Bluetooth permissions")
            return
        }

        withContext(Dispatchers.Main) {
            try {
                _connectionState.value = BleConnectionState.Scanning
                _discoveredDevices.value = emptyList()

                val scanSettings = ScanSettings.Builder()
                    .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                    .setCallbackType(ScanSettings.CALLBACK_TYPE_ALL_MATCHES)
                    .build()

                val scanFilters = listOf(
                    ScanFilter.Builder()
                        .setServiceUuid(ParcelUuid(SPP_UUID))
                        .build()
                )

                bluetoothLeScanner?.startScan(scanFilters, scanSettings, scanCallback)

                // Auto-stop scan after 30 seconds
                scope.launch {
                    delay(30000)
                    stopScanning()
                }

                Log.i(TAG, "Started BLE scanning")

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
            if (_connectionState.value == BleConnectionState.Scanning) {
                _connectionState.value = BleConnectionState.Disconnected
            }
            Log.i(TAG, "Stopped BLE scanning")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to stop scanning", e)
        }
    }

    private val scanCallback = object : ScanCallback() {
        @SuppressLint("MissingPermission")
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device
            val deviceInfo = BleDeviceInfo(
                name = device.name ?: "Unknown",
                address = device.address,
                rssi = result.rssi
            )

            val currentDevices = _discoveredDevices.value.toMutableList()
            val existingIndex = currentDevices.indexOfFirst { it.address == device.address }

            if (existingIndex >= 0) {
                currentDevices[existingIndex] = deviceInfo
            } else {
                currentDevices.add(deviceInfo)
            }

            _discoveredDevices.value = currentDevices
            Log.d(TAG, "Found BLE device: ${device.name} (${device.address})")
        }

        override fun onScanFailed(errorCode: Int) {
            Log.e(TAG, "BLE scan failed with error: $errorCode")
            _connectionState.value = BleConnectionState.Error("Scan failed: error $errorCode")
        }
    }

    @SuppressLint("MissingPermission")
    override suspend fun connectWithRetry(deviceAddress: String): Boolean {
        if (!PermissionHelper.hasBluetoothPermissions(context)) {
            _connectionState.value = BleConnectionState.Error("Missing Bluetooth permissions")
            return false
        }

        return withContext(Dispatchers.Main) {
            retryCount = 0

            while (retryCount < maxRetries) {
                retryCount++
                try {
                    _connectionState.value = BleConnectionState.Connecting
                    Log.i(TAG, "Attempting to connect to $deviceAddress (attempt $retryCount)")

                    val device = bluetoothAdapter?.getRemoteDevice(deviceAddress)
                    if (device == null) {
                        _connectionState.value = BleConnectionState.Error("Device not found")
                        return@withContext false
                    }

                    // Connect with timeout
                    val connected = withTimeoutOrNull(10000) {
                        suspendCancellableCoroutine { continuation ->
                            bluetoothGatt = device.connectGatt(context, false, object : BluetoothGattCallback() {
                                override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
                                    when (newState) {
                                        BluetoothProfile.STATE_CONNECTED -> {
                                            Log.i(TAG, "Connected to GATT server")
                                            gatt.discoverServices()
                                        }
                                        BluetoothProfile.STATE_DISCONNECTED -> {
                                            Log.i(TAG, "Disconnected from GATT server")
                                            _connectionState.value = BleConnectionState.Disconnected
                                            cleanupGatt()
                                            if (!continuation.isCompleted) {
                                                continuation.resume(false)
                                            }
                                        }
                                    }
                                }

                                override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
                                    if (status == BluetoothGatt.GATT_SUCCESS) {
                                        Log.i(TAG, "Services discovered")
                                        setupCharacteristics(gatt)
                                        _connectionState.value = BleConnectionState.Connected
                                        continuation.resume(true)
                                    } else {
                                        Log.e(TAG, "Service discovery failed: $status")
                                        continuation.resume(false)
                                    }
                                }

                                override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
                                    val data = characteristic.value
                                    if (data != null) {
                                        responseBuffer.add(data)
                                        checkForCompleteResponse()
                                    }
                                }
                            })

                            // Start connection
                            bluetoothGatt?.connect()
                        }
                    } ?: false

                    if (connected) {
                        Log.i(TAG, "Successfully connected to $deviceAddress")
                        return@withContext true
                    } else {
                        Log.w(TAG, "Connection attempt failed, retrying...")
                        delay(1000L * retryCount) // Simple exponential backoff
                    }

                } catch (e: Exception) {
                    Log.e(TAG, "Connection error", e)
                    delay(1000L * retryCount) // Simple exponential backoff
                }
            }

            _connectionState.value = BleConnectionState.Error("Failed to connect after $retryCount attempts")
            false
        }
    }

    private fun setupCharacteristics(gatt: BluetoothGatt) {
        for (service in gatt.services) {
            if (service.uuid == SPP_UUID) {
                for (characteristic in service.characteristics) {
                    when (characteristic.properties) {
                        BluetoothGattCharacteristic.PROPERTY_WRITE,
                        BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE -> {
                            txCharacteristic = characteristic
                        }
                        BluetoothGattCharacteristic.PROPERTY_READ,
                        BluetoothGattCharacteristic.PROPERTY_NOTIFY -> {
                            rxCharacteristic = characteristic
                            gatt.setCharacteristicNotification(characteristic, true)
                        }
                    }
                }
                break
            }
        }
    }

    private fun checkForCompleteResponse() {
        // Simple implementation - look for '>' terminator
        val combined = ByteArray(responseBuffer.sumOf { it.size })
        var offset = 0
        for (bytes in responseBuffer) {
            bytes.copyInto(combined, offset)
            offset += bytes.size
        }
        val response = String(combined, Charsets.UTF_8)
        if (response.endsWith(">")) {
            scope.launch {
                responseChannel.send(response.trim())
            }
            responseBuffer.clear()
        }
    }

    @SuppressLint("MissingPermission")
    override suspend fun sendCommand(command: String): String? {
        return withContext(Dispatchers.Main) {
            if (!isConnected() || txCharacteristic == null) {
                return@withContext null
            }

            try {
                val data = (command + "\r").toByteArray(Charsets.UTF_8)
                txCharacteristic?.setValue(data)
                bluetoothGatt?.writeCharacteristic(txCharacteristic)

                // Wait for response with timeout
                withTimeoutOrNull(5000) {
                    responseChannel.receive()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send command", e)
                null
            }
        }
    }

    @SuppressLint("MissingPermission")
    override suspend fun disconnect() {
        withContext(Dispatchers.Main) {
            try {
                bluetoothGatt?.disconnect()
                cleanupInternal()
                _connectionState.value = BleConnectionState.Disconnected
            } catch (e: Exception) {
                Log.e(TAG, "Disconnect failed", e)
            }
        }
    }

    override fun isConnected(): Boolean {
        return bluetoothGatt != null &&
               _connectionState.value == BleConnectionState.Connected
    }

    private fun cleanupInternal() {
        bluetoothGatt?.close()
        bluetoothGatt = null
        txCharacteristic = null
        rxCharacteristic = null
        responseBuffer.clear()
    }

    private fun cleanupGatt() {
        try {
            bluetoothGatt?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing GATT", e)
        } finally {
            bluetoothGatt = null
            txCharacteristic = null
            rxCharacteristic = null
        }
    }

    override suspend fun cleanup() {
        stopScanning()
        if (isConnected()) {
            disconnect()
        }
        cleanupInternal()
    }
}