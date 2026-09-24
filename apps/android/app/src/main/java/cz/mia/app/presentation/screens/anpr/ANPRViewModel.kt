package cz.mia.app.presentation.screens.anpr

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import cz.mia.app.data.repository.ANPRRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

data class PlateDetection(
    val plate: String,
    val confidence: Float,
    val isExempted: Boolean = false,
    val exemptionReason: String? = null,
    val timestamp: Long = System.currentTimeMillis()
)

data class ANPRUiState(
    val isCapturing: Boolean = false,
    val detectedPlates: List<PlateDetection> = emptyList(),
    val lastDetection: PlateDetection? = null,
    val isCheckingEdalnice: Boolean = false,
    val error: String? = null,
    val websocketConnected: Boolean = false,
    val captureStats: CaptureStats = CaptureStats()
)

data class CaptureStats(
    val totalScans: Int = 0,
    val exemptedVehicles: Int = 0,
    val totalVehicles: Int = 0
)

@HiltViewModel
class ANPRViewModel @Inject constructor(
    private val repository: ANPRRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ANPRUiState())
    val uiState: StateFlow<ANPRUiState> = _uiState.asStateFlow()

    init {
        // Initialize WebSocket connection
        connectWebSocket()
    }

    private fun connectWebSocket() {
        viewModelScope.launch {
            repository.connectToWebSocket(
                onPlateDetected = { plate ->
                    addDetection(plate)
                },
                onError = { error ->
                    _uiState.value = _uiState.value.copy(
                        error = error,
                        websocketConnected = false
                    )
                },
                onConnected = {
                    _uiState.value = _uiState.value.copy(websocketConnected = true)
                }
            )
        }
    }

    fun startCapture(deviceId: String = "esp32-camera") {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isCapturing = true,
                error = null
            )

            try {
                repository.triggerCapture(deviceId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isCapturing = false,
                    error = "Failed to start capture: ${e.message}"
                )
            }
        }
    }

    fun stopCapture() {
        _uiState.value = _uiState.value.copy(isCapturing = false)
    }

    fun addDetection(plate: PlateDetection) {
        viewModelScope.launch {
            val currentState = _uiState.value
            val newPlates = (currentState.detectedPlates + plate).takeLast(10)
            
            val exemptCount = if (plate.isExempted) 1 else 0
            val newStats = currentState.captureStats.copy(
                totalScans = currentState.captureStats.totalScans + 1,
                exemptedVehicles = currentState.captureStats.exemptedVehicles + exemptCount,
                totalVehicles = currentState.captureStats.totalVehicles + 1
            )

            _uiState.value = currentState.copy(
                detectedPlates = newPlates,
                lastDetection = plate,
                captureStats = newStats
            )
        }
    }

    fun clearDetections() {
        _uiState.value = _uiState.value.copy(
            detectedPlates = emptyList(),
            lastDetection = null
        )
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    override fun onCleared() {
        super.onCleared()
        repository.disconnectWebSocket()
    }
}
