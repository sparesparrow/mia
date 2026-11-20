package cz.mia.app.core.voice

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import cz.mia.app.R
import cz.mia.app.core.networking.PiConnectionProvider
import dagger.hilt.android.AndroidEntryPoint
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import javax.inject.Inject

/** User-started phone microphone stream for the Pi voice pipeline (REQ-AND-027). */
@AndroidEntryPoint
class MicStreamService : Service() {
    @Inject lateinit var piConnection: PiConnectionProvider

    private val mainHandler = Handler(Looper.getMainLooper())
    private val running = AtomicBoolean(false)
    private val client by lazy {
        OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .pingInterval(20, TimeUnit.SECONDS)
            .build()
    }
    private var socket: WebSocket? = null
    private var recorder: AudioRecord? = null
    private var captureThread: Thread? = null
    @Volatile private var retryAttempt = 0
    @Volatile private var retryScheduled = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopStreaming()
            return START_NOT_STICKY
        }
        if (!hasMicPermission()) {
            stopSelf(startId)
            return START_NOT_STICKY
        }
        if (running.compareAndSet(false, true)) {
            startAsForeground()
            connect()
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        stopStreaming()
        client.dispatcher.executorService.shutdown()
        super.onDestroy()
    }

    private fun connect() {
        if (!running.get()) return
        stopCapture()
        val target = piConnection.current()
        val request = Request.Builder()
            .url(target.wsBaseUrl.trimEnd('/') + "/ws/audio")
            .apply { target.authHeaders().forEach { (name, value) -> header(name, value) } }
            .build()
        socket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                if (socket !== webSocket) return
                val format = JSONObject()
                    .put("v", 1)
                    .put("fmt", "s16le")
                    .put("rate", SAMPLE_RATE)
                    .put("ch", 1)
                    .put("frame_ms", FRAME_MS)
                    .toString()
                if (!webSocket.send(format)) scheduleReconnect("Could not start the audio stream")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                if (socket !== webSocket) return
                val message = try { JSONObject(text) } catch (_: Exception) { return }
                if (message.optBoolean("ok", false)) {
                    retryAttempt = 0
                    startCapture(webSocket)
                } else if (message.optString("mic") == "open") {
                    updateNotification("Microphone connected to the Pi")
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                if (socket !== webSocket) return
                scheduleReconnect(reason.ifBlank { "Pi audio link closed" })
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                if (socket !== webSocket) return
                scheduleReconnect(t.message ?: "Pi audio link failed")
            }
        })
    }

    private fun startCapture(webSocket: WebSocket) {
        if (!running.get() || socket !== webSocket || captureThread?.isAlive == true) return
        if (!hasMicPermission()) {
            updateNotification("Microphone permission was removed")
            stopStreaming()
            return
        }
        try {
            val minimum = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            if (minimum <= 0) throw IllegalStateException("Phone does not support 16 kHz audio capture")
            val audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(minimum, FRAME_BYTES * 6),
            )
            if (audioRecord.state != AudioRecord.STATE_INITIALIZED) {
                audioRecord.release()
                throw IllegalStateException("Could not open the phone microphone")
            }
            audioRecord.startRecording()
            recorder = audioRecord
            updateNotification("Streaming the phone microphone to the Pi")
            captureThread = Thread({ captureFrames(audioRecord, webSocket) }, "mia-phone-mic").apply {
                isDaemon = true
                start()
            }
        } catch (error: Exception) {
            scheduleReconnect(error.message ?: "Could not start microphone capture")
        }
    }

    private fun captureFrames(audioRecord: AudioRecord, webSocket: WebSocket) {
        val frame = ByteArray(FRAME_BYTES)
        try {
            while (running.get() && socket === webSocket) {
                var offset = 0
                while (offset < frame.size && running.get() && socket === webSocket) {
                    val count = audioRecord.read(frame, offset, frame.size - offset)
                    if (count <= 0) throw IllegalStateException("Phone microphone read failed ($count)")
                    offset += count
                }
                if (offset == frame.size) {
                    // Keep the OkHttp queue bounded to six 30 ms frames when the USB link is congested.
                    if (webSocket.queueSize() < FRAME_BYTES * MAX_QUEUED_FRAMES) {
                        if (!webSocket.send(frame.copyOf())) throw IllegalStateException("Pi audio link is closed")
                    }
                }
            }
        } catch (error: Exception) {
            if (running.get() && socket === webSocket) {
                scheduleReconnect(error.message ?: "Microphone capture stopped")
            }
        }
    }

    private fun scheduleReconnect(reason: String) {
        if (!running.get() || retryScheduled) return
        retryScheduled = true
        val oldSocket = socket
        socket = null
        oldSocket?.cancel()
        stopCapture()
        val delaySeconds = minOf(30, 1 shl retryAttempt.coerceAtMost(5))
        retryAttempt = (retryAttempt + 1).coerceAtMost(5)
        updateNotification("Reconnecting to Pi audio")
        mainHandler.postDelayed({
            retryScheduled = false
            if (running.get()) connect()
        }, delaySeconds * 1000L)
    }

    private fun stopCapture() {
        val current = recorder
        recorder = null
        if (current != null) {
            try { current.stop() } catch (_: IllegalStateException) { }
            current.release()
        }
        captureThread = null
    }

    private fun stopStreaming() {
        if (!running.getAndSet(false)) {
            stopSelf()
            return
        }
        mainHandler.removeCallbacksAndMessages(null)
        retryScheduled = false
        stopCapture()
        socket?.close(1000, "user stopped microphone")
        socket = null
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    private fun hasMicPermission(): Boolean = ContextCompat.checkSelfPermission(
        this,
        Manifest.permission.RECORD_AUDIO,
    ) == PackageManager.PERMISSION_GRANTED

    private fun startAsForeground() {
        val notification = buildNotification("Connecting to the Pi voice service")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun updateNotification(text: String) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification(text))
    }

    private fun buildNotification(text: String): Notification {
        createNotificationChannel()
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_car)
            .setContentTitle("MIA phone microphone")
            .setContentText(text)
            .setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .addAction(
                android.R.drawable.ic_media_pause,
                "Stop",
                PendingIntent.getService(
                    this,
                    0,
                    Intent(this, MicStreamService::class.java).setAction(ACTION_STOP),
                    PendingIntent.FLAG_UPDATE_CURRENT or
                        (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0),
                ),
            )
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "MIA microphone", NotificationManager.IMPORTANCE_LOW),
            )
        }
    }

    companion object {
        const val ACTION_START = "cz.mia.app.voice.MIC_START"
        const val ACTION_STOP = "cz.mia.app.voice.MIC_STOP"
        private const val CHANNEL_ID = "mia_phone_microphone"
        private const val NOTIFICATION_ID = 271
        private const val SAMPLE_RATE = 16000
        private const val FRAME_MS = 30
        private const val FRAME_BYTES = SAMPLE_RATE * FRAME_MS / 1000 * 2
        private const val MAX_QUEUED_FRAMES = 6

        fun start(context: Context) {
            val intent = Intent(context, MicStreamService::class.java).setAction(ACTION_START)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            context.startService(Intent(context, MicStreamService::class.java).setAction(ACTION_STOP))
        }
    }
}
