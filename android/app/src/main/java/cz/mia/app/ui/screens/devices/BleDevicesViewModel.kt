package cz.mia.app.ui.screens.devices

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.background.BLEManager
import cz.mia.app.core.background.BleConnectionState
import cz.mia.app.core.background.BleDeviceInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * UI state for the BLE devices screen.
 */
data class BleDevicesUiState(
    val isScanning: Boolean = false,
    val discoveredDevices: List<BleDeviceInfo> = emptyList(),
    val connectedDevice: BleDeviceInfo? = null,
    val connectionState: BleConnectionState = BleConnectionState.Disconnected,
    val errorMessage: String? = null,
    val isInitialized: Boolean = false
)

/**
 * ViewModel for managing BLE device discovery and connection.
 */
@HiltViewModel
class BleDevicesViewModel @Inject constructor(
    private val bleManager: BLEManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(BleDevicesUiState())
    val uiState: StateFlow<BleDevicesUiState> = _uiState.asStateFlow()
    
    private var connectedDeviceAddress: String? = null

    init {
        observeBleState()
        observeDiscoveredDevices()
        initializeBle()
    }
    
    private fun observeBleState() {
        bleManager.connectionState
            .onEach { state ->
                _uiState.update { current ->
                    current.copy(
                        connectionState = state,
                        isScanning = state is BleConnectionState.Scanning,
                        errorMessage = when (state) {
                            is BleConnectionState.Error -> state.message
                            else -> null
                        },
                        connectedDevice = when (state) {
                            is BleConnectionState.Connected -> {
                                connectedDeviceAddress?.let { address ->
                                    current.discoveredDevices.find { it.address == address }
                                }
                            }
                            else -> null
                        }
                    )
                }
            }
            .launchIn(viewModelScope)
    }
    
    private fun observeDiscoveredDevices() {
        bleManager.discoveredDevices
            .onEach { devices ->
                _uiState.update { current ->
                    current.copy(discoveredDevices = devices)
                }
            }
            .launchIn(viewModelScope)
    }
    
    private fun initializeBle() {
        viewModelScope.launch {
            bleManager.initialize()
            _uiState.update { it.copy(isInitialized = true) }
        }
    }
    
    /**
     * Start scanning for BLE devices.
     */
    fun startScanning() {
        viewModelScope.launch {
            clearError()
            bleManager.startScanning()
        }
    }
    
    /**
     * Stop scanning for BLE devices.
     */
    fun stopScanning() {
        bleManager.stopScanning()
    }
    
    /**
     * Toggle scanning state.
     */
    fun toggleScanning() {
        if (_uiState.value.isScanning) {
            stopScanning()
        } else {
            startScanning()
        }
    }
    
    /**
     * Connect to a BLE device by address.
     */
    fun connectToDevice(address: String) {
        viewModelScope.launch {
            clearError()
            connectedDeviceAddress = address
            val success = bleManager.connectWithRetry(address)
            if (!success) {
                _uiState.update { current ->
                    current.copy(
                        errorMessage = "Failed to connect to device"
                    )
                }
                connectedDeviceAddress = null
            }
        }
    }
    
    /**
     * Disconnect from the current device.
     */
    fun disconnect() {
        viewModelScope.launch {
            bleManager.disconnect()
            connectedDeviceAddress = null
        }
    }
    
    /**
     * Clear any error message.
     */
    fun clearError() {
        _uiState.update { current ->
            current.copy(errorMessage = null)
        }
    }
    
    /**
     * Refresh the device list by restarting scanning.
     */
    fun refresh() {
        viewModelScope.launch {
            stopScanning()
            startScanning()
        }
    }
    
    /**
     * Send a command to the connected device.
     */
    fun sendCommand(command: String, onResult: (String?) -> Unit) {
        viewModelScope.launch {
            val result = bleManager.sendCommand(command)
            onResult(result)
        }
    }
    
    /**
     * Check if currently connected to a device.
     */
    fun isConnected(): Boolean = bleManager.isConnected()
    
    override fun onCleared() {
        super.onCleared()
        // Note: cleanup is handled by the singleton BLEManager's lifecycle
        // We don't call cleanup here as it would affect other consumers
    }
}
