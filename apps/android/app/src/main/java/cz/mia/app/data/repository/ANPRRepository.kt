package cz.mia.app.data.repository

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import cz.mia.app.BuildConfig
import cz.mia.app.presentation.screens.anpr.PlateDetection
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton


@Singleton
class ANPRRepository @Inject constructor() {

    companion object {
        private const val TAG = "ANPRRepository"
    }

    private val apiBaseUrl = BuildConfig.API_BASE_URL.trimEnd('/')
    private val wsStreamUrl = "${BuildConfig.WS_BASE_URL.trimEnd('/')}/anpr/stream"

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var onPlateDetected: ((PlateDetection) -> Unit)? = null
    private var onError: ((String) -> Unit)? = null
    private var onConnected: (() -> Unit)? = null

    suspend fun triggerCapture(deviceId: String = "esp32-camera") = withContext(Dispatchers.IO) {
        try {
            val json = JSONObject().apply {
                put("device_id", deviceId)
                put("capture_count", 1)
                put("quality", 85)
                put("auto_process", true)
            }

            val body = json.toString().toRequestBody("application/json".toMediaType())

            val request = Request.Builder()
                .url("$apiBaseUrl/anpr/capture")
                .post(body)
                .build()

            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw Exception("Capture failed: ${response.code}")
                }
                Log.d(TAG, "Capture triggered: ${response.body?.string()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error triggering capture: ${e.message}")
            onError?.invoke("Failed to trigger capture: ${e.message}")
            throw e
        }
    }

    suspend fun uploadImageForProcessing(imageFile: File, autoCheckEdalnice: Boolean = true) {
        withContext(Dispatchers.IO) {
            try {
                val requestBody = MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart("file", imageFile.name, imageFile.asRequestBody("image/jpeg".toMediaType()))
                    .addFormDataPart("auto_check_edalnice", autoCheckEdalnice.toString())
                    .build()

                val request = Request.Builder()
                    .url("$apiBaseUrl/anpr/process")
                    .post(requestBody)
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        throw Exception("Image processing failed: ${response.code}")
                    }

                    val responseBody = response.body?.string() ?: return@use
                    val jsonResponse = JSONObject(responseBody)
                    val scanResults = jsonResponse.optJSONArray("scan_results")

                    scanResults?.let { results ->
                        for (i in 0 until results.length()) {
                            val result = results.getJSONObject(i)
                            val plate = result.getString("plate")
                            val confidence = result.getDouble("confidence").toFloat()
                            val isExempted = result.getBoolean("is_exempted")
                            val exemptionReason = result.optString("exemption_reason")

                            val detection = PlateDetection(
                                plate = plate,
                                confidence = confidence,
                                isExempted = isExempted,
                                exemptionReason = exemptionReason.takeIf { it.isNotEmpty() }
                            )

                            onPlateDetected?.invoke(detection)
                        }
                    }

                    Log.d(TAG, "Image processed successfully")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error processing image: ${e.message}")
                onError?.invoke("Failed to process image: ${e.message}")
                throw e
            }
        }
    }

    suspend fun getScanHistory(limit: Int = 50, offset: Int = 0) = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$apiBaseUrl/anpr/history?limit=$limit&offset=$offset")
                .get()
                .build()

            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw Exception("Failed to fetch history: ${response.code}")
                }
                response.body?.string() ?: "{}"
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching scan history: ${e.message}")
            onError?.invoke("Failed to fetch history: ${e.message}")
            throw e
        }
    }

    suspend fun getAlerts(limit: Int = 20) = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$apiBaseUrl/anpr/alerts?limit=$limit")
                .get()
                .build()

            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw Exception("Failed to fetch alerts: ${response.code}")
                }
                response.body?.string() ?: "{}"
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching alerts: ${e.message}")
            onError?.invoke("Failed to fetch alerts: ${e.message}")
            throw e
        }
    }

    suspend fun connectToWebSocket(
        onPlateDetected: (PlateDetection) -> Unit,
        onError: (String) -> Unit,
        onConnected: () -> Unit
    ) = withContext(Dispatchers.Main) {
        this@ANPRRepository.onPlateDetected = onPlateDetected
        this@ANPRRepository.onError = onError
        this@ANPRRepository.onConnected = onConnected

        try {
            val request = Request.Builder().url(wsStreamUrl).build()
            val listener = ANPRWebSocketListener(
                onPlateDetected = onPlateDetected,
                onError = onError,
                onConnected = onConnected
            )
            webSocket = httpClient.newWebSocket(request, listener)
        } catch (e: Exception) {
            Log.e(TAG, "Error connecting to WebSocket: ${e.message}")
            onError("Failed to connect to WebSocket: ${e.message}")
        }
    }

    fun disconnectWebSocket() {
        webSocket?.close(1000, "Normal closure")
        webSocket = null
    }

    fun sendWebSocketMessage(message: JSONObject) {
        webSocket?.send(message.toString())
    }

    private class ANPRWebSocketListener(
        private val onPlateDetected: (PlateDetection) -> Unit,
        private val onError: (String) -> Unit,
        private val onConnected: () -> Unit
    ) : WebSocketListener() {

        override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
            Log.d(TAG, "WebSocket connected")
            onConnected()
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            try {
                val message = JSONObject(text)

                when (message.optString("type")) {
                    "plate_detected" -> {
                        val data = message.getJSONObject("data")
                        val detection = PlateDetection(
                            plate = data.getString("plate"),
                            confidence = data.getDouble("confidence").toFloat(),
                            isExempted = data.getBoolean("is_exempted"),
                            exemptionReason = data.optString("exemption_reason").takeIf { it.isNotEmpty() }
                        )
                        onPlateDetected(detection)
                    }

                    "pong" -> {
                        Log.d(TAG, "Pong received")
                    }

                    else -> {
                        Log.d(TAG, "Unknown message type: ${message.optString("type")}")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error parsing WebSocket message: ${e.message}")
                onError("Failed to parse message: ${e.message}")
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
            Log.e(TAG, "WebSocket failure: ${t.message}")
            onError("WebSocket connection failed: ${t.message}")
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.d(TAG, "WebSocket closed: $reason (code: $code)")
        }
    }
}
