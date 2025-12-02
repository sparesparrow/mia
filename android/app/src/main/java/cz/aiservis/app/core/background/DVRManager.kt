package cz.aiservis.app.core.background

import android.Manifest
import android.annotation.SuppressLint
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import androidx.camera.core.CameraSelector
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.FileOutputOptions
import androidx.camera.video.MediaStoreOutputOptions
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.Recording
import androidx.camera.video.VideoCapture
import androidx.camera.video.VideoRecordEvent
import androidx.core.content.ContextCompat
import androidx.core.content.PermissionChecker
import androidx.lifecycle.LifecycleOwner
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import cz.aiservis.app.data.db.ClipEntity
import cz.aiservis.app.data.db.ClipsDao
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * DVR recording state.
 */
sealed class DVRState {
    object Idle : DVRState()
    object Initializing : DVRState()
    object Recording : DVRState()
    object Paused : DVRState()
    object SavingClip : DVRState()
    data class Error(val message: String) : DVRState()
}

/**
 * DVR clip event types.
 */
enum class ClipEventType {
    RECORDING_STARTED,
    RECORDING_STOPPED,
    EVENT_CLIP_SAVED,
    BUFFER_FULL,
    BUFFER_ROTATED,
    OFFLOAD_READY,
    STORAGE_LOW,
    ERROR
}

/**
 * Event emitted by DVR manager.
 */
data class ClipEvent(
    val type: ClipEventType,
    val clipId: Long? = null,
    val reason: String? = null,
    val filePath: String? = null,
    val timestamp: Long = System.currentTimeMillis()
)

/**
 * DVR recording statistics.
 */
data class DVRStats(
    val totalRecordingTimeMs: Long = 0,
    val totalClipsSaved: Int = 0,
    val totalStorageUsedBytes: Long = 0,
    val currentBufferSizeMs: Int = 0,
    val lastClipTime: Long = 0
)

/**
 * DVR Manager interface for video recording.
 */
interface DVRManager {
    /** Event flow for clip events */
    val clipEvents: SharedFlow<ClipEvent>
    
    /** Current recording state */
    val state: StateFlow<DVRState>
    
    /** Recording statistics */
    val stats: StateFlow<DVRStats>
    
    /** Start continuous recording */
    fun startRecording()
    
    /** Stop recording */
    fun stopRecording()
    
    /** Trigger event clip extraction */
    fun triggerEventClip(reason: String)
    
    /** Check if currently recording */
    fun isRecording(): Boolean
    
    /** Bind camera for recording (call from UI with lifecycle) */
    suspend fun bindCamera(lifecycleOwner: LifecycleOwner)
    
    /** Set rolling buffer duration (in seconds) */
    fun setBufferDuration(seconds: Int)
    
    /** Get list of pending clips for offload */
    suspend fun getPendingOffloadClips(): List<ClipEntity>
    
    /** Mark clip as offloaded */
    suspend fun markClipOffloaded(clipId: Long)
    
    /** Clean up old clips based on retention policy */
    suspend fun cleanupOldClips(retentionDays: Int): Int
}

@Singleton
class DVRManagerImpl @Inject constructor(
    @ApplicationContext private val context: Context,
    private val clipsDao: ClipsDao,
    private val coroutineScope: CoroutineScope
) : DVRManager {

    companion object {
        private const val TAG = "DVRManager"
        
        private const val DEFAULT_BUFFER_DURATION_SEC = 60
        private const val DEFAULT_CLIP_DURATION_SEC = 30
        private const val MAX_CLIP_SIZE_BYTES = 100_000_000L // 100MB
        private const val MIN_FREE_SPACE_BYTES = 500_000_000L // 500MB minimum free space
        
        private const val VIDEO_QUALITY = Quality.HD
        private const val CLIPS_DIRECTORY = "ai-servis-clips"
        
        private val DATE_FORMAT = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
    }

    private val _clipEvents = MutableSharedFlow<ClipEvent>(extraBufferCapacity = 10)
    override val clipEvents: SharedFlow<ClipEvent> = _clipEvents.asSharedFlow()
    
    private val _state = MutableStateFlow<DVRState>(DVRState.Idle)
    override val state: StateFlow<DVRState> = _state.asStateFlow()
    
    private val _stats = MutableStateFlow(DVRStats())
    override val stats: StateFlow<DVRStats> = _stats.asStateFlow()

    @Volatile
    private var isRecordingActive = false
    private var bufferDurationSec = DEFAULT_BUFFER_DURATION_SEC
    
    private var cameraProvider: ProcessCameraProvider? = null
    private var videoCapture: VideoCapture<Recorder>? = null
    private var currentRecording: Recording? = null
    
    private var currentSegmentStartTime: Long = 0
    private var recordingStartTime: Long = 0
    
    private val clipDirectory: File by lazy {
        File(context.filesDir, CLIPS_DIRECTORY).apply { 
            if (!exists()) mkdirs() 
        }
    }
    
    private val rollingBuffer = mutableListOf<File>()

    override fun startRecording() {
        if (isRecordingActive) {
            Log.d(TAG, "Recording already active")
            return
        }
        
        if (!hasRequiredPermissions()) {
            _state.value = DVRState.Error("Missing camera/storage permissions")
            return
        }
        
        if (!hasEnoughStorage()) {
            _state.value = DVRState.Error("Insufficient storage space")
            emitEvent(ClipEventType.STORAGE_LOW)
            return
        }
        
        isRecordingActive = true
        recordingStartTime = System.currentTimeMillis()
        _state.value = DVRState.Recording
        
        scheduleOffloadWork()
        scheduleBufferRotation()
        
        emitEvent(ClipEventType.RECORDING_STARTED)
        Log.d(TAG, "DVR recording started")
    }

    override fun stopRecording() {
        if (!isRecordingActive) return
        
        isRecordingActive = false
        
        try {
            currentRecording?.stop()
            currentRecording = null
            
            val totalTime = System.currentTimeMillis() - recordingStartTime
            updateStats { it.copy(totalRecordingTimeMs = it.totalRecordingTimeMs + totalTime) }
            
            _state.value = DVRState.Idle
            emitEvent(ClipEventType.RECORDING_STOPPED)
            Log.d(TAG, "DVR recording stopped")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping recording", e)
            _state.value = DVRState.Error("Failed to stop recording: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    override suspend fun bindCamera(lifecycleOwner: LifecycleOwner) = withContext(Dispatchers.Main) {
        try {
            _state.value = DVRState.Initializing
            
            cameraProvider = getCameraProvider()
            
            val qualitySelector = QualitySelector.from(VIDEO_QUALITY)
            val recorder = Recorder.Builder()
                .setQualitySelector(qualitySelector)
                .build()
            
            videoCapture = VideoCapture.withOutput(recorder)
            
            cameraProvider?.unbindAll()
            
            cameraProvider?.bindToLifecycle(
                lifecycleOwner,
                CameraSelector.DEFAULT_BACK_CAMERA,
                videoCapture
            )
            
            Log.d(TAG, "Camera bound for video recording")
            
            if (isRecordingActive) {
                startNewSegment()
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to bind camera", e)
            _state.value = DVRState.Error("Camera bind failed: ${e.message}")
        }
    }

    override fun triggerEventClip(reason: String) {
        if (!isRecordingActive) {
            Log.w(TAG, "Cannot trigger clip - not recording")
            return
        }
        
        coroutineScope.launch(Dispatchers.IO) {
            try {
                _state.value = DVRState.SavingClip
                
                val timestamp = System.currentTimeMillis()
                val sanitizedReason = reason.replace(Regex("[^a-zA-Z0-9]"), "_").take(30)
                val fileName = "${DATE_FORMAT.format(Date(timestamp))}_${sanitizedReason}.mp4"
                
                val clipFile = File(clipDirectory, fileName)
                
                // If we have buffer segments, combine them
                val clipDurationMs = if (rollingBuffer.isNotEmpty()) {
                    saveBufferToClip(clipFile)
                } else {
                    // Create placeholder if no actual video yet
                    createPlaceholderClip(clipFile)
                    DEFAULT_CLIP_DURATION_SEC * 1000
                }
                
                val clipSize = if (clipFile.exists()) clipFile.length() else 0L
                
                val clip = ClipEntity(
                    ts = timestamp,
                    reason = reason,
                    filePath = clipFile.absolutePath,
                    durationMs = clipDurationMs,
                    sizeBytes = clipSize,
                    offloaded = false
                )
                
                clipsDao.insert(clip)
                
                updateStats { stats ->
                    stats.copy(
                        totalClipsSaved = stats.totalClipsSaved + 1,
                        totalStorageUsedBytes = stats.totalStorageUsedBytes + clipSize,
                        lastClipTime = timestamp
                    )
                }
                
                _state.value = DVRState.Recording
                emitEvent(ClipEventType.EVENT_CLIP_SAVED, clipId = clip.id, reason = reason, filePath = clipFile.absolutePath)
                
                Log.d(TAG, "Event clip saved: ${clipFile.name} (${clipSize / 1024}KB)")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to trigger event clip", e)
                _state.value = DVRState.Recording
                emitEvent(ClipEventType.ERROR, reason = "Failed to save clip: ${e.message}")
            }
        }
    }

    override fun isRecording(): Boolean = isRecordingActive

    override fun setBufferDuration(seconds: Int) {
        bufferDurationSec = seconds.coerceIn(10, 300)
        Log.d(TAG, "Buffer duration set to $bufferDurationSec seconds")
    }

    override suspend fun getPendingOffloadClips(): List<ClipEntity> = withContext(Dispatchers.IO) {
        clipsDao.snapshotRecent(100).filter { !it.offloaded }
    }

    override suspend fun markClipOffloaded(clipId: Long) = withContext(Dispatchers.IO) {
        clipsDao.markOffloaded(clipId)
        Log.d(TAG, "Clip $clipId marked as offloaded")
    }

    override suspend fun cleanupOldClips(retentionDays: Int): Int = withContext(Dispatchers.IO) {
        val threshold = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(retentionDays.toLong())
        val deleted = clipsDao.deleteOlderThan(threshold)
        
        // Also clean up files
        clipDirectory.listFiles()?.forEach { file ->
            if (file.lastModified() < threshold) {
                file.delete()
            }
        }
        
        Log.d(TAG, "Cleaned up $deleted old clips")
        deleted
    }

    @SuppressLint("MissingPermission")
    private fun startNewSegment() {
        val recorder = videoCapture?.output ?: return
        
        val timestamp = System.currentTimeMillis()
        val fileName = "segment_${DATE_FORMAT.format(Date(timestamp))}.mp4"
        val segmentFile = File(clipDirectory, fileName)
        
        val outputOptions = FileOutputOptions.Builder(segmentFile).build()
        
        currentRecording = recorder.prepareRecording(context, outputOptions)
            .also { recording ->
                if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) 
                    == PackageManager.PERMISSION_GRANTED) {
                    recording.withAudioEnabled()
                }
            }
            .start(ContextCompat.getMainExecutor(context)) { event ->
                when (event) {
                    is VideoRecordEvent.Start -> {
                        currentSegmentStartTime = System.currentTimeMillis()
                        Log.d(TAG, "Segment recording started: ${segmentFile.name}")
                    }
                    is VideoRecordEvent.Finalize -> {
                        if (event.hasError()) {
                            Log.e(TAG, "Segment recording error: ${event.error}")
                            emitEvent(ClipEventType.ERROR, reason = "Recording error: ${event.error}")
                        } else {
                            Log.d(TAG, "Segment finalized: ${segmentFile.name}")
                            addToRollingBuffer(segmentFile)
                        }
                    }
                }
            }
    }

    private fun addToRollingBuffer(segmentFile: File) {
        synchronized(rollingBuffer) {
            rollingBuffer.add(segmentFile)
            
            // Calculate total buffer duration and remove old segments
            var totalDurationMs = 0L
            val segmentDurationMs = DEFAULT_CLIP_DURATION_SEC * 1000L
            
            while (rollingBuffer.size > 0 && totalDurationMs > bufferDurationSec * 1000) {
                val oldSegment = rollingBuffer.removeAt(0)
                oldSegment.delete()
                totalDurationMs -= segmentDurationMs
            }
            
            updateStats { it.copy(currentBufferSizeMs = (rollingBuffer.size * segmentDurationMs).toInt()) }
        }
        
        emitEvent(ClipEventType.BUFFER_ROTATED)
    }

    private fun saveBufferToClip(outputFile: File): Int {
        synchronized(rollingBuffer) {
            if (rollingBuffer.isEmpty()) {
                return 0
            }
            
            // For simplicity, copy the last segment
            // In production, you'd use FFmpeg or MediaMuxer to combine segments
            val lastSegment = rollingBuffer.lastOrNull()
            if (lastSegment?.exists() == true) {
                lastSegment.copyTo(outputFile, overwrite = true)
                return DEFAULT_CLIP_DURATION_SEC * 1000
            }
            
            return 0
        }
    }

    private fun createPlaceholderClip(file: File) {
        // Create a small placeholder file for testing
        file.writeText("placeholder")
    }

    private suspend fun getCameraProvider(): ProcessCameraProvider = suspendCancellableCoroutine { cont ->
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        cameraProviderFuture.addListener({
            try {
                cont.resume(cameraProviderFuture.get())
            } catch (e: Exception) {
                cont.resumeWithException(e)
            }
        }, ContextCompat.getMainExecutor(context))
    }

    private fun hasRequiredPermissions(): Boolean {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == 
            PackageManager.PERMISSION_GRANTED
    }

    private fun hasEnoughStorage(): Boolean {
        val stat = android.os.StatFs(clipDirectory.absolutePath)
        val availableBytes = stat.availableBlocksLong * stat.blockSizeLong
        return availableBytes > MIN_FREE_SPACE_BYTES
    }

    private fun scheduleBufferRotation() {
        // Buffer rotation is handled by segment finalization
    }

    private fun scheduleOffloadWork() {
        val offloadWork = PeriodicWorkRequestBuilder<DvrOffloadWorker>(
            1, TimeUnit.HOURS
        ).build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "dvr_offload_work",
            ExistingPeriodicWorkPolicy.KEEP,
            offloadWork
        )
    }

    private fun emitEvent(
        type: ClipEventType, 
        clipId: Long? = null, 
        reason: String? = null,
        filePath: String? = null
    ) {
        coroutineScope.launch {
            _clipEvents.emit(ClipEvent(type, clipId, reason, filePath))
        }
    }

    private fun updateStats(update: (DVRStats) -> DVRStats) {
        _stats.value = update(_stats.value)
    }
}
