package cz.mia.app.core.voice.mic

import android.Manifest
import android.annotation.SuppressLint
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
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import cz.mia.app.MainActivity
import cz.mia.app.R
import cz.mia.app.core.networking.PiConnectionProvider
import cz.mia.app.core.voice.console.OkHttpVoiceSocketFactory
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import javax.inject.Inject

/**
 * Streams the phone's microphone to the Pi's `/ws/audio` (ADR-0021, REQ-AND-027). Started by the user from the
 * Voice tab while the app is in the foreground (an Android 14 rule), as a foreground service of type
 * `microphone` with a notification that has a Stop action. The microphone is always read, so the buffer never
 * overruns, but frames leave the phone only while [MicStreamController.talking] is true (push-to-talk).
 */
@AndroidEntryPoint
class MicStreamService : Service() {
    @Inject lateinit var piConnection: PiConnectionProvider

    @Inject lateinit var okHttpClient: OkHttpClient

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var client: MicStreamClient? = null
    private var capture: Thread? = null

    @Volatile private var running = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            shutDown()
            return START_NOT_STICKY
        }
        if (running) return START_NOT_STICKY
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            Log.w(TAG, "RECORD_AUDIO not granted; not starting")
            stopSelf()
            return START_NOT_STICKY
        }
        ServiceCompat.startForeground(this, NOTIFICATION_ID, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        running = true
        MicStreamController.setEnabled(true)
        val target = piConnection.current()
        val stream = MicStreamClient(
            url = target.wsBaseUrl.trimEnd('/') + "/ws/audio",
            headers = target.authHeaders(),
            factory = OkHttpVoiceSocketFactory(okHttpClient),
            scope = scope,
        )
        client = stream
        scope.launch { stream.link.collect { MicStreamController.setLink(it) } }
        stream.start()
        capture = Thread({ captureLoop(stream) }, "mia-mic-capture").also { it.start() }
        return START_NOT_STICKY
    }

    @SuppressLint("MissingPermission") // checked in onStartCommand
    private fun captureLoop(stream: MicStreamClient) {
        val minimum = AudioRecord.getMinBufferSize(
            MicProtocol.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        val recorder = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            MicProtocol.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            maxOf(minimum, MicProtocol.FRAME_BYTES * 8),
        )
        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            Log.w(TAG, "AudioRecord did not initialise")
            recorder.release()
            scope.launch { shutDown() }
            return
        }
        val framer = MicFramer()
        val buffer = ByteArray(MicProtocol.FRAME_BYTES)
        var wasTalking = false
        try {
            recorder.startRecording()
            while (running) {
                val read = recorder.read(buffer, 0, buffer.size)
                if (read <= 0) continue
                val talking = MicStreamController.talking.value
                if (!talking) {
                    if (wasTalking) framer.reset()
                    wasTalking = false
                    continue
                }
                wasTalking = true
                for (frame in framer.add(buffer, read)) stream.sendFrame(frame)
            }
        } finally {
            runCatching { recorder.stop() }
            recorder.release()
        }
    }

    private fun shutDown() {
        running = false
        client?.stop()
        client = null
        MicStreamController.setEnabled(false)
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        running = false
        client?.stop()
        MicStreamController.setEnabled(false)
        capture?.join(500)
        scope.cancel()
        super.onDestroy()
    }

    private fun notification(): android.app.Notification {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Phone microphone", NotificationManager.IMPORTANCE_LOW),
        )
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
        )
        val stop = PendingIntent.getService(
            this, 1,
            Intent(this, MicStreamService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_car)
            .setContentTitle("MIA is using your microphone")
            .setContentText("Sent to the Pi only while MIA is listening")
            .setOngoing(true)
            .setContentIntent(open)
            .addAction(0, "Stop", stop)
            .build()
    }

    companion object {
        const val ACTION_START = "cz.mia.app.mic.START"
        const val ACTION_STOP = "cz.mia.app.mic.STOP"
        private const val CHANNEL_ID = "phone_mic"
        private const val NOTIFICATION_ID = 4127
        private const val TAG = "MicStreamService"
    }
}
