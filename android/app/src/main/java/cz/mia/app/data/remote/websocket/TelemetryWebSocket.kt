package cz.mia.app.data.remote.websocket

import android.util.Log
import com.google.gson.Gson
import cz.mia.app.data.remote.dto.TelemetryReading
import cz.mia.app.data.remote.dto.WebSocketSubscription
import cz.mia.app.data.remote.dto.WebSocketMessage
import cz.mia.app.data.remote.dto.LEDState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import org.java_websocket.client.WebSocketClient
import org.java_websocket.handshake.ServerHandshake
import java.net.URI

/**
 * WebSocket connection states.
 */
sealed class WebSocketState {
    object Disconnected : WebSocketState()
    object Connecting : WebSocketState()
    object Connected : WebSocketState()
    data class Error(val message: String, val throwable: Throwable? = null) : WebSocketState()
}

/**
 * WebSocket client for real-time telemetry data.
 * Note: Not using @Singleton/@Inject to avoid eager initialization issues.
 * Instantiate manually when needed.
 */
class TelemetryWebSocket(
    private val wsBaseUrl: String,
    private val gson: Gson
) {
    companion object {
        private const val TAG = "TelemetryWebSocket"
        private const val RECONNECT_DELAY_MS = 5000L
        private const val MAX_RECONNECT_ATTEMPTS = 5
        private const val TELEMETRY_ENDPOINT = "/ws/telemetry"
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    private var webSocketClient: WebSocketClient? = null
    private var reconnectAttempts = 0
    private var isManualDisconnect = false
    
    private val subscribedDevices = mutableSetOf<String>()
    
    private val _telemetryFlow = MutableSharedFlow<TelemetryReading>(
        replay = 0,
        extraBufferCapacity = 64
    )
    val telemetryFlow: SharedFlow<TelemetryReading> = _telemetryFlow.asSharedFlow()

    private val _ledStateFlow = MutableSharedFlow<LEDState>(
        replay = 0,
        extraBufferCapacity = 16
    )
    val ledStateFlow: SharedFlow<LEDState> = _ledStateFlow.asSharedFlow()

    private val _stateFlow = MutableSharedFlow<WebSocketState>(
        replay = 1,
        extraBufferCapacity = 8
    )
    val stateFlow: SharedFlow<WebSocketState> = _stateFlow.asSharedFlow()

    init {
        // Initialize state lazily to avoid issues during DI construction
        try {
            scope.launch {
                _stateFlow.emit(WebSocketState.Disconnected)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error initializing state", e)
        }
      }
    
    /**
     * Connect to the WebSocket server.
     */
    fun connect() {
        if (webSocketClient?.isOpen == true) {
            Log.d(TAG, "Already connected")
            return
        }
        
        isManualDisconnect = false
        reconnectAttempts = 0
        
        scope.launch {
            try {
                _stateFlow.emit(WebSocketState.Connecting)
                createAndConnectClient()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to connect", e)
                _stateFlow.emit(WebSocketState.Error("Connection failed: ${e.message}", e))
                scheduleReconnect()
            }
        }
    }
    
    /**
     * Disconnect from the WebSocket server.
     */
    fun disconnect() {
        isManualDisconnect = true
        scope.launch {
            try {
                webSocketClient?.close()
            } catch (e: Exception) {
                Log.e(TAG, "Error closing WebSocket", e)
            } finally {
                webSocketClient = null
                _stateFlow.emit(WebSocketState.Disconnected)
            }
        }
    }
    
    /**
     * Subscribe to telemetry updates for a specific device.
     */
    fun subscribeToDevice(deviceId: String) {
        subscribedDevices.add(deviceId)
        sendSubscription("subscribe", deviceId)
    }
    
    /**
     * Unsubscribe from telemetry updates for a specific device.
     */
    fun unsubscribeFromDevice(deviceId: String) {
        subscribedDevices.remove(deviceId)
        sendSubscription("unsubscribe", deviceId)
    }
    
    /**
     * Check if connected to the WebSocket server.
     */
    fun isConnected(): Boolean = webSocketClient?.isOpen == true
    
    private fun createAndConnectClient() {
        val uri = URI("$wsBaseUrl$TELEMETRY_ENDPOINT")
        
        webSocketClient = object : WebSocketClient(uri) {
            override fun onOpen(handshakedata: ServerHandshake?) {
                Log.d(TAG, "WebSocket connected")
                reconnectAttempts = 0
                scope.launch {
                    _stateFlow.emit(WebSocketState.Connected)
                    // Resubscribe to previously subscribed devices
                    subscribedDevices.forEach { deviceId ->
                        sendSubscription("subscribe", deviceId)
                    }
                }
            }
            
            override fun onMessage(message: String?) {
                message?.let { msg ->
                    try {
                        // Try to parse as new WebSocketMessage format first
                        val wsMessage = gson.fromJson(msg, WebSocketMessage::class.java)

                        scope.launch {
                            // Emit telemetry if present
                            wsMessage.telemetry?.let { telemetry ->
                                // Convert telemetry map to individual TelemetryReading objects
                                telemetry.forEach { (deviceId, deviceData) ->
                                    if (deviceData is Map<*, *>) {
                                        val dataMap = deviceData as Map<String, Any>
                                        // Extract common telemetry fields
                                        val rpm = (dataMap["rpm"] as? Number)?.toDouble()
                                        val speed = (dataMap["speed_kmh"] as? Number)?.toDouble()
                                        val temp = (dataMap["coolant_temp_c"] as? Number)?.toDouble()

                                        rpm?.let {
                                            _telemetryFlow.emit(TelemetryReading(
                                                deviceId = deviceId,
                                                timestamp = wsMessage.timestamp,
                                                sensor = "rpm",
                                                value = it,
                                                unit = "rpm"
                                            ))
                                        }
                                        speed?.let {
                                            _telemetryFlow.emit(TelemetryReading(
                                                deviceId = deviceId,
                                                timestamp = wsMessage.timestamp,
                                                sensor = "speed",
                                                value = it,
                                                unit = "km/h"
                                            ))
                                        }
                                        temp?.let {
                                            _telemetryFlow.emit(TelemetryReading(
                                                deviceId = deviceId,
                                                timestamp = wsMessage.timestamp,
                                                sensor = "temperature",
                                                value = it,
                                                unit = "°C"
                                            ))
                                        }
                                    }
                                }
                            }

                            // Emit LED state if present
                            wsMessage.ledState?.let { ledState ->
                                _ledStateFlow.emit(ledState)
                            }
                        }
                    } catch (e: Exception) {
                        // Fallback to old TelemetryReading format for backward compatibility
                        try {
                            val reading = gson.fromJson(msg, TelemetryReading::class.java)
                            scope.launch {
                                _telemetryFlow.emit(reading)
                            }
                        } catch (fallbackException: Exception) {
                            Log.e(TAG, "Failed to parse WebSocket message: $msg", e)
                        }
                    }
                }
            }
            
            override fun onClose(code: Int, reason: String?, remote: Boolean) {
                Log.d(TAG, "WebSocket closed: code=$code, reason=$reason, remote=$remote")
                scope.launch {
                    _stateFlow.emit(WebSocketState.Disconnected)
                    if (!isManualDisconnect && remote) {
                        scheduleReconnect()
                    }
                }
            }
            
            override fun onError(ex: Exception?) {
                Log.e(TAG, "WebSocket error", ex)
                scope.launch {
                    _stateFlow.emit(WebSocketState.Error(ex?.message ?: "Unknown error", ex))
                }
            }
        }
        
        webSocketClient?.connect()
    }
    
    private fun sendSubscription(action: String, deviceId: String) {
        if (webSocketClient?.isOpen != true) {
            Log.w(TAG, "Cannot send subscription - not connected")
            return
        }
        
        try {
            val subscription = WebSocketSubscription(
                action = action,
                deviceId = deviceId
            )
            val json = gson.toJson(subscription)
            webSocketClient?.send(json)
            Log.d(TAG, "Sent $action for device: $deviceId")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to send subscription", e)
        }
    }
    
    private fun scheduleReconnect() {
        if (isManualDisconnect) return
        
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            Log.w(TAG, "Max reconnect attempts reached")
            scope.launch {
                _stateFlow.emit(WebSocketState.Error("Max reconnect attempts reached"))
            }
            return
        }
        
        reconnectAttempts++
        val delayMs = RECONNECT_DELAY_MS * reconnectAttempts
        
        Log.d(TAG, "Scheduling reconnect attempt $reconnectAttempts in ${delayMs}ms")
        
        scope.launch {
            delay(delayMs)
            if (!isManualDisconnect) {
                connect()
            }
        }
    }
    
    /**
     * Clean up resources.
     */
    fun cleanup() {
        disconnect()
        subscribedDevices.clear()
    }
}
