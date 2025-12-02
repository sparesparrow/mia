package cz.aiservis.app.data.remote.websocket

import android.util.Log
import com.google.gson.Gson
import cz.aiservis.app.data.remote.dto.TelemetryReading
import cz.aiservis.app.data.remote.dto.WebSocketSubscription
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
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton

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
 */
@Singleton
class TelemetryWebSocket @Inject constructor(
    @Named("ws_base_url") private val wsBaseUrl: String,
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
    
    private val _stateFlow = MutableSharedFlow<WebSocketState>(
        replay = 1,
        extraBufferCapacity = 8
    )
    val stateFlow: SharedFlow<WebSocketState> = _stateFlow.asSharedFlow()
    
    init {
        scope.launch {
            _stateFlow.emit(WebSocketState.Disconnected)
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
                        val reading = gson.fromJson(msg, TelemetryReading::class.java)
                        scope.launch {
                            _telemetryFlow.emit(reading)
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse telemetry message: $msg", e)
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
