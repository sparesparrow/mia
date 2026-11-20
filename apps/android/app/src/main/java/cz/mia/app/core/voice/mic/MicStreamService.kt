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
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import cz.mia.app.MainActivity
import cz.mia.app.R
import cz.mia.app.core.networking.PiConnectionProvider
import cz.mia.app.core.voice.console.OkHttpVoiceSocketFactory
import cz.mia.app.utils.PermissionHelper
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
        val hasRecordPermission = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO,
        ) == PackageManager.PERMISSION_GRANTED
        if (!hasRecordPermission || !PermissionHelper.hasNotificationPermission(this)) {
            Log.w(TAG, "Required microphone service permission missing; not starting")
            stopSelfResult(startId)
            return START_NOT_STICKY
        }
        try {
            ServiceCompat.startForeground(this, NOTIFICATION_ID, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } catch (e: SecurityException) {
            Log.w(TAG, "Android rejected microphone foreground service start", e)
            stopSelfResult(startId)
            return START_NOT_STICKY
        }
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
        val framer = MicFramer()
        val buffer = ByteArray(MicProtocol.FRAME_BYTES)
        var wasTalking = false
        var recorder: AudioRecord? = null
        var consecutiveErrors = 0
        try {
            while (running) {
                val current = recorder ?: createAudioRecord().also { recorder = it }
                if (current == null) {
                    consecutiveErrors++
                    if (!retryRecorder(consecutiveErrors)) break
                    continue
                }
                try {
                    if (current.recordingState != AudioRecord.RECORDSTATE_RECORDING) current.startRecording()
                } catch (e: IllegalStateException) {
                    Log.w(TAG, "AudioRecord could not start; recreating it", e)
                    current.release()
                    recorder = null
                    consecutiveErrors++
                    if (!retryRecorder(consecutiveErrors)) break
                    continue
                }
                val read = try {
                    current.read(buffer, 0, buffer.size)
                } catch (e: IllegalStateException) {
                    Log.w(TAG, "AudioRecord read failed; recreating it", e)
                    AudioRecord.ERROR_INVALID_OPERATION
                }
                if (read < 0) {
                    // Android reports ERROR_DEAD_OBJECT when the recorder must be recreated. Treat every negative
                    // result this way, and bound retries so a persistent hardware error cannot spin this thread.
                    Log.w(TAG, "AudioRecord.read returned $read; recreating recorder")
                    current.release()
                    recorder = null
                    framer.reset()
                    consecutiveErrors++
                    if (!retryRecorder(consecutiveErrors)) break
                    continue
                }
                if (read == 0) {
                    try {
                        Thread.sleep(10)
                    } catch (_: InterruptedException) {
                        Thread.currentThread().interrupt()
                        break
                    }
                    continue
                }
                consecutiveErrors = 0
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
            recorder?.let {
                runCatching { it.stop() }
                it.release()
            }
        }
        if (running) scope.launch { shutDown() }
    }

    @SuppressLint("MissingPermission") // checked in onStartCommand
    private fun createAudioRecord(): AudioRecord? {
        val minimum = AudioRecord.getMinBufferSize(
            MicProtocol.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        val recorder = runCatching {
            AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                MicProtocol.SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(minimum, MicProtocol.FRAME_BYTES * 8),
            )
        }.getOrElse {
            Log.w(TAG, "AudioRecord construction failed", it)
            return null
        }
        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            Log.w(TAG, "AudioRecord did not initialise")
            recorder.release()
            return null
        }
        return recorder
    }

    private fun retryRecorder(consecutiveErrors: Int): Boolean {
        if (consecutiveErrors >= MAX_RECORDER_RETRIES) {
            Log.e(TAG, "AudioRecord failed $consecutiveErrors consecutive times; stopping microphone service")
            return false
        }
        try {
            Thread.sleep(RECORDER_RETRY_DELAY_MS * consecutiveErrors)
        } catch (_: InterruptedException) {
            Thread.currentThread().interrupt()
            return false
        }
        return running
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
        val pendingIntentFlags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_IMMUTABLE
        } else {
            0
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Phone microphone", NotificationManager.IMPORTANCE_LOW),
            )
        }
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), pendingIntentFlags,
        )
        val stop = PendingIntent.getService(
            this, 1,
            Intent(this, MicStreamService::class.java).setAction(ACTION_STOP),
            pendingIntentFlags,
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
        private const val MAX_RECORDER_RETRIES = 3
        private const val RECORDER_RETRY_DELAY_MS = 100L
    }
}
