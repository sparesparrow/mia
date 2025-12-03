package cz.aiservis.app.core.background

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Rect
import android.util.Log
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.core.resolutionselector.AspectRatioStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import cz.aiservis.app.core.camera.AnprPostprocessor
import cz.aiservis.app.core.security.PlateHasher
import cz.aiservis.app.core.storage.PreferencesRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.util.UUID
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Detection state for ANPR system.
 */
sealed class ANPRState {
    object Idle : ANPRState()
    object Initializing : ANPRState()
    object Active : ANPRState()
    object Paused : ANPRState()
    data class Error(val message: String) : ANPRState()
}

/**
 * Detected plate information (before hashing).
 */
data class DetectedPlate(
    val rawText: String,
    val normalizedText: String,
    val confidence: Float,
    val boundingBox: Rect?
)

/**
 * ANPR Manager interface for license plate recognition.
 */
interface ANPRManager {
    /** Flow of ANPR detection events */
    val events: Flow<ANPREvent>
    
    /** Current detection state */
    val state: StateFlow<ANPRState>
    
    /** Last detected plate (for UI display) */
    val lastDetectedPlate: StateFlow<DetectedPlate?>
    
    /** Detection statistics */
    val detectionStats: StateFlow<DetectionStats>
    
    /** Start plate detection */
    suspend fun startDetection()
    
    /** Stop detection */
    suspend fun stopDetection()
    
    /** Bind camera preview (call from UI) */
    fun bindPreview(previewView: PreviewView, lifecycleOwner: LifecycleOwner)
    
    /** Check if detection is active */
    fun isActive(): Boolean
    
    /** Set confidence threshold */
    fun setConfidenceThreshold(threshold: Float)
}

/**
 * Statistics for ANPR detection.
 */
data class DetectionStats(
    val totalFramesProcessed: Long = 0,
    val platesDetected: Long = 0,
    val validPlatesEmitted: Long = 0,
    val averageConfidence: Float = 0f,
    val lastDetectionTime: Long = 0
)

/**
 * ANPR Event emitted when a plate is detected.
 */
data class ANPREvent(
    val plateHash: String,
    val confidence: Float,
    val snapshotId: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
    val region: String = "CZ"
)

@Singleton
class ANPRManagerImpl @Inject constructor(
    @ApplicationContext private val context: Context,
    private val prefs: PreferencesRepository
) : ANPRManager {

    companion object {
        private const val TAG = "ANPRManager"
        
        private const val TARGET_WIDTH = 1280
        private const val TARGET_HEIGHT = 720
        
        private const val DEFAULT_CONFIDENCE_THRESHOLD = 0.65f
        private const val MIN_PLATE_LENGTH = 4
        private const val MAX_PLATE_LENGTH = 10
        
        // Debounce same plate detections
        private const val DEBOUNCE_TIME_MS = 3000L
        
        // Plate pattern regex (European/CZ plates)
        private val PLATE_PATTERN = Regex("^[A-Z0-9]{4,10}$")
        
        // HMAC secret for plate hashing (in production, this would be securely stored)
        private val HASH_SECRET = "ai-servis-anpr-secret".toByteArray(Charsets.UTF_8)
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var cameraExecutor: ExecutorService? = null
    
    private val textRecognizer: TextRecognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    
    private var cameraProvider: ProcessCameraProvider? = null
    private var imageAnalysis: ImageAnalysis? = null
    private var preview: Preview? = null
    
    private val _events = MutableSharedFlow<ANPREvent>(replay = 0, extraBufferCapacity = 10)
    override val events: Flow<ANPREvent> = _events.asSharedFlow()
    
    private val _state = MutableStateFlow<ANPRState>(ANPRState.Idle)
    override val state: StateFlow<ANPRState> = _state.asStateFlow()
    
    private val _lastDetectedPlate = MutableStateFlow<DetectedPlate?>(null)
    override val lastDetectedPlate: StateFlow<DetectedPlate?> = _lastDetectedPlate.asStateFlow()
    
    private val _detectionStats = MutableStateFlow(DetectionStats())
    override val detectionStats: StateFlow<DetectionStats> = _detectionStats.asStateFlow()
    
    private var confidenceThreshold = DEFAULT_CONFIDENCE_THRESHOLD
    private val recentPlates = mutableMapOf<String, Long>() // plateHash -> lastSeenTime

    override suspend fun startDetection() = withContext(Dispatchers.Main) {
        if (_state.value is ANPRState.Active) {
            Log.d(TAG, "Detection already active")
            return@withContext
        }
        
        _state.value = ANPRState.Initializing
        
        try {
            cameraExecutor = Executors.newSingleThreadExecutor()
            
            cameraProvider = getCameraProvider()
            
            imageAnalysis = ImageAnalysis.Builder()
                .setTargetResolution(Size(TARGET_WIDTH, TARGET_HEIGHT))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { analysis ->
                    analysis.setAnalyzer(cameraExecutor!!, PlateAnalyzer())
                }
            
            preview = Preview.Builder()
                .setTargetResolution(Size(TARGET_WIDTH, TARGET_HEIGHT))
                .build()
            
            _state.value = ANPRState.Active
            Log.d(TAG, "ANPR detection started")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start detection", e)
            _state.value = ANPRState.Error("Failed to start: ${e.message}")
        }
    }

    override suspend fun stopDetection() {
        withContext(Dispatchers.Main) {
            try {
                cameraProvider?.unbindAll()
                cameraExecutor?.shutdown()
                cameraExecutor = null
                
                recentPlates.clear()
                _state.value = ANPRState.Idle
                Log.d(TAG, "ANPR detection stopped")
                
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping detection", e)
            }
        }
    }

    override fun bindPreview(previewView: PreviewView, lifecycleOwner: LifecycleOwner) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        
        cameraProviderFuture.addListener({
            try {
                val provider = cameraProviderFuture.get()
                cameraProvider = provider
                
                provider.unbindAll()
                
                val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                
                preview?.setSurfaceProvider(previewView.surfaceProvider)
                
                val useCases = mutableListOf<androidx.camera.core.UseCase>()
                preview?.let { useCases.add(it) }
                imageAnalysis?.let { useCases.add(it) }
                
                if (useCases.isNotEmpty()) {
                    provider.bindToLifecycle(
                        lifecycleOwner,
                        cameraSelector,
                        *useCases.toTypedArray()
                    )
                }
                
                Log.d(TAG, "Camera preview bound successfully")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to bind camera preview", e)
                _state.value = ANPRState.Error("Camera bind failed: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(context))
    }

    override fun isActive(): Boolean = _state.value is ANPRState.Active

    override fun setConfidenceThreshold(threshold: Float) {
        confidenceThreshold = threshold.coerceIn(0.1f, 1.0f)
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

    private inner class PlateAnalyzer : ImageAnalysis.Analyzer {
        
        @SuppressLint("UnsafeOptInUsageError")
        override fun analyze(imageProxy: ImageProxy) {
            val mediaImage = imageProxy.image
            
            if (mediaImage == null) {
                imageProxy.close()
                return
            }
            
            updateStats { it.copy(totalFramesProcessed = it.totalFramesProcessed + 1) }
            
            val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
            
            textRecognizer.process(image)
                .addOnSuccessListener { visionText ->
                    processTextResult(visionText)
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "Text recognition failed", e)
                }
                .addOnCompleteListener {
                    imageProxy.close()
                }
        }
        
        private fun processTextResult(visionText: Text) {
            val candidates = mutableListOf<DetectedPlate>()
            
            for (block in visionText.textBlocks) {
                for (line in block.lines) {
                    val rawText = line.text
                    val normalized = AnprPostprocessor.normalize(rawText)
                    
                    // Filter for plate-like text
                    if (isPlateCandidate(normalized)) {
                        val confidence = calculateConfidence(line, normalized)
                        
                        candidates.add(DetectedPlate(
                            rawText = rawText,
                            normalizedText = normalized,
                            confidence = confidence,
                            boundingBox = line.boundingBox
                        ))
                    }
                }
            }
            
            // Process best candidate
            candidates.maxByOrNull { it.confidence }?.let { bestPlate ->
                if (bestPlate.confidence >= confidenceThreshold) {
                    updateStats { it.copy(platesDetected = it.platesDetected + 1) }
                    processPlateDet(bestPlate)
                }
            }
        }
        
        private fun isPlateCandidate(text: String): Boolean {
            if (text.length < MIN_PLATE_LENGTH || text.length > MAX_PLATE_LENGTH) {
                return false
            }
            return PLATE_PATTERN.matches(text)
        }
        
        private fun calculateConfidence(line: Text.Line, normalized: String): Float {
            var baseConfidence = line.confidence
            
            // Apply region heuristics
            scope.launch {
                val region = prefs.anprRegion.first()
                val (_, bonus) = AnprPostprocessor.applyRegionHeuristics(normalized, region)
                baseConfidence = AnprPostprocessor.tuneConfidence(baseConfidence, bonus)
            }
            
            // Boost confidence for typical plate length (7-8 chars for CZ plates)
            if (normalized.length in 7..8) {
                baseConfidence += 0.05f
            }
            
            return baseConfidence.coerceIn(0f, 1f)
        }
        
        private fun processPlateDet(plate: DetectedPlate) {
            scope.launch {
                val region = prefs.anprRegion.first()
                val (finalPlate, bonus) = AnprPostprocessor.applyRegionHeuristics(plate.normalizedText, region)
                val finalConfidence = AnprPostprocessor.tuneConfidence(plate.confidence, bonus)
                
                // Hash the plate for privacy
                val plateHash = PlateHasher.hmacSha256(finalPlate, HASH_SECRET)
                
                // Check debounce
                val now = System.currentTimeMillis()
                val lastSeen = recentPlates[plateHash]
                
                if (lastSeen == null || (now - lastSeen) > DEBOUNCE_TIME_MS) {
                    recentPlates[plateHash] = now
                    
                    // Clean old entries
                    recentPlates.entries.removeIf { now - it.value > DEBOUNCE_TIME_MS * 2 }
                    
                    val snapshotId = UUID.randomUUID().toString()
                    
                    val event = ANPREvent(
                        plateHash = plateHash,
                        confidence = finalConfidence,
                        snapshotId = snapshotId,
                        region = region
                    )
                    
                    _events.emit(event)
                    _lastDetectedPlate.value = plate.copy(confidence = finalConfidence)
                    
                    updateStats { stats ->
                        stats.copy(
                            validPlatesEmitted = stats.validPlatesEmitted + 1,
                            averageConfidence = ((stats.averageConfidence * (stats.validPlatesEmitted - 1)) + finalConfidence) / stats.validPlatesEmitted,
                            lastDetectionTime = now
                        )
                    }
                    
                    Log.d(TAG, "Plate detected: ${plate.normalizedText.take(3)}*** (conf: $finalConfidence)")
                }
            }
        }
    }
    
    private fun updateStats(update: (DetectionStats) -> DetectionStats) {
        _detectionStats.value = update(_detectionStats.value)
    }
    
    /**
     * MVP helper to emit a processed event from a raw OCR result (for testing/simulation).
     */
    suspend fun emitRawOcr(rawText: String, baseConfidence: Float, snapshotId: String? = null) {
        val region = prefs.anprRegion.first()
        val (normPlate, bonus) = AnprPostprocessor.applyRegionHeuristics(rawText, region)
        val tuned = AnprPostprocessor.tuneConfidence(baseConfidence, bonus)
        val plateHash = PlateHasher.hmacSha256(normPlate, HASH_SECRET)
        _events.emit(ANPREvent(plateHash = plateHash, confidence = tuned, snapshotId = snapshotId, region = region))
    }
}
