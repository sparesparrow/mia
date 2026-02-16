package cz.mia.app.features.led

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.data.remote.dto.LEDState
import cz.mia.app.data.remote.websocket.TelemetryWebSocket
import cz.mia.app.data.remote.websocket.WebSocketState
import com.google.gson.Gson
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LEDMonitorViewModel @Inject constructor(
    private val gson: Gson
) : ViewModel() {

    companion object {
        private const val TAG = "LEDMonitorViewModel"
    }

    private var webSocket: TelemetryWebSocket? = null

    private val _ledState = MutableStateFlow<LEDState?>(null)
    val ledState: StateFlow<LEDState?> = _ledState.asStateFlow()

    private val _webSocketState = MutableStateFlow<WebSocketState>(WebSocketState.Disconnected)
    val webSocketState: StateFlow<WebSocketState> = _webSocketState.asStateFlow()

    private val _serviceStatuses = MutableStateFlow<Map<String, Boolean>>(
        mapOf(
            "API" to true,
            "GPIO" to true,
            "Serial" to false,
            "OBD" to true,
            "MQTT" to true,
            "Camera" to false
        )
    )
    val serviceStatuses: StateFlow<Map<String, Boolean>> = _serviceStatuses.asStateFlow()

    fun initializeWebSocket(baseUrl: String) {
        if (webSocket != null) {
            Log.d(TAG, "WebSocket already initialized")
            return
        }

        webSocket = TelemetryWebSocket(baseUrl, gson)

        viewModelScope.launch {
            webSocket?.stateFlow?.collectLatest { state ->
                _webSocketState.value = state
                when (state) {
                    is WebSocketState.Connected -> {
                        Log.d(TAG, "WebSocket connected, subscribing to LED updates")
                    }
                    is WebSocketState.Disconnected -> {
                        Log.d(TAG, "WebSocket disconnected")
                    }
                    is WebSocketState.Error -> {
                        Log.e(TAG, "WebSocket error: ${state.message}")
                    }
                    else -> {}
                }
            }
        }

        viewModelScope.launch {
            webSocket?.ledStateFlow?.collectLatest { ledState ->
                _ledState.value = ledState
                // Update service statuses from LED state
                ledState.serviceStatus?.let { statusString ->
                    val statuses = parseServiceStatus(statusString)
                    _serviceStatuses.value = statuses
                }
            }
        }

        connectWebSocket()
    }

    fun connectWebSocket() {
        webSocket?.connect()
    }

    fun disconnectWebSocket() {
        webSocket?.disconnect()
    }

    private fun parseServiceStatus(statusString: String): Map<String, Boolean> {
        val statuses = mutableMapOf<String, Boolean>()
        statusString.split(",").forEach { status ->
            val parts = status.split(":")
            if (parts.size == 2) {
                val service = parts[0]
                val state = parts[1].lowercase()
                statuses[service] = state == "healthy" || state == "active"
            }
        }
        return statuses
    }

    // LED Control Methods

    fun setLedMode(mode: String) {
        webSocket?.setLedMode(mode)
        Log.d(TAG, "Set LED mode: $mode")
    }

    fun setAiState(aiState: String) {
        webSocket?.setAiState(aiState)
        Log.d(TAG, "Set AI state: $aiState")
    }

    fun setLedBrightness(brightness: Int) {
        webSocket?.setLedBrightness(brightness)
        Log.d(TAG, "Set LED brightness: $brightness")
    }

    fun setLedColor(r: Int, g: Int, b: Int) {
        webSocket?.setLedColor(r, g, b)
        Log.d(TAG, "Set LED color: RGB($r, $g, $b)")
    }

    fun triggerEmergency() {
        webSocket?.triggerEmergency()
        Log.d(TAG, "Triggered emergency mode")
    }

    fun clearEmergency() {
        webSocket?.clearEmergency()
        Log.d(TAG, "Cleared emergency mode")
    }

    fun startAnimation(animation: String, speed: Int = 100) {
        webSocket?.startAnimation(animation, speed)
        Log.d(TAG, "Started animation: $animation at speed $speed")
    }

    fun stopAnimation() {
        webSocket?.stopAnimation()
        Log.d(TAG, "Stopped animation")
    }

    // Convenience methods for common actions

    fun setDriveMode() {
        setLedMode("drive")
    }

    fun setParkedMode() {
        setLedMode("parked")
    }

    fun setNightMode() {
        setLedMode("night")
    }

    fun setServiceMode() {
        setLedMode("service")
    }

    override fun onCleared() {
        super.onCleared()
        webSocket?.cleanup()
        webSocket = null
    }
}