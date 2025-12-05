package cz.mia.app.core.voice

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.util.Locale
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume

/**
 * Voice synthesis state.
 */
sealed class VoiceState {
    object Idle : VoiceState()
    object Initializing : VoiceState()
    object Ready : VoiceState()
    object Speaking : VoiceState()
    data class Error(val message: String) : VoiceState()
}

/**
 * Speech priority levels.
 */
enum class SpeechPriority {
    LOW,
    NORMAL,
    HIGH,
    CRITICAL
}

/**
 * Speech request with priority.
 */
data class SpeechRequest(
    val text: String,
    val priority: SpeechPriority = SpeechPriority.NORMAL,
    val locale: Locale? = null,
    val speechRate: Float = 1.0f,
    val pitch: Float = 1.0f
)

/**
 * Voice Manager interface for text-to-speech alerts.
 */
interface VoiceManager {
    /** Current voice state */
    val state: StateFlow<VoiceState>
    
    /** Current speech queue size */
    val queueSize: StateFlow<Int>
    
    /** Speak text with default settings */
    suspend fun speak(text: String)
    
    /** Speak with custom settings */
    suspend fun speak(request: SpeechRequest)
    
    /** Speak immediately (interrupts current speech) */
    suspend fun speakNow(text: String, priority: SpeechPriority = SpeechPriority.CRITICAL)
    
    /** Stop current speech */
    fun stop()
    
    /** Clear speech queue */
    fun clearQueue()
    
    /** Set default locale */
    fun setLocale(locale: Locale): Boolean
    
    /** Set speech rate (0.5 to 2.0) */
    fun setSpeechRate(rate: Float)
    
    /** Set pitch (0.5 to 2.0) */
    fun setPitch(pitch: Float)
    
    /** Check if TTS is available */
    fun isAvailable(): Boolean
    
    /** Get available locales */
    fun getAvailableLocales(): Set<Locale>
}

@Singleton
class VoiceManagerImpl @Inject constructor(
    @ApplicationContext private val context: Context
) : VoiceManager {

    companion object {
        private const val TAG = "VoiceManager"
        
        // Default locales to try
        private val CZECH_LOCALE = Locale("cs", "CZ")
        private val ENGLISH_LOCALE = Locale.US
        
        private const val DEFAULT_SPEECH_RATE = 1.0f
        private const val DEFAULT_PITCH = 1.0f
        private const val MAX_QUEUE_SIZE = 20
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    
    private var tts: TextToSpeech? = null
    private var isInitialized = false
    
    private val speechQueue = Channel<SpeechRequest>(Channel.UNLIMITED)
    private val activeUtterances = mutableMapOf<String, () -> Unit>()
    
    private val audioManager: AudioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private var audioFocusRequest: AudioFocusRequest? = null
    
    private val _state = MutableStateFlow<VoiceState>(VoiceState.Initializing)
    override val state: StateFlow<VoiceState> = _state.asStateFlow()
    
    private val _queueSize = MutableStateFlow(0)
    override val queueSize: StateFlow<Int> = _queueSize.asStateFlow()
    
    private var currentLocale: Locale = CZECH_LOCALE
    private var currentSpeechRate = DEFAULT_SPEECH_RATE
    private var currentPitch = DEFAULT_PITCH

    init {
        initializeTTS()
        startQueueProcessor()
    }

    private fun initializeTTS() {
        _state.value = VoiceState.Initializing
        
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                isInitialized = true
                
                // Try Czech first, fallback to English
                val czechResult = tts?.setLanguage(CZECH_LOCALE)
                if (czechResult == TextToSpeech.LANG_MISSING_DATA || 
                    czechResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                    
                    Log.w(TAG, "Czech locale not available, falling back to English")
                    val englishResult = tts?.setLanguage(ENGLISH_LOCALE)
                    if (englishResult == TextToSpeech.LANG_AVAILABLE || 
                        englishResult == TextToSpeech.LANG_COUNTRY_AVAILABLE) {
                        currentLocale = ENGLISH_LOCALE
                    }
                } else {
                    currentLocale = CZECH_LOCALE
                }
                
                tts?.setSpeechRate(currentSpeechRate)
                tts?.setPitch(currentPitch)
                
                setupUtteranceListener()
                
                _state.value = VoiceState.Ready
                Log.d(TAG, "TTS initialized with locale: $currentLocale")
                
            } else {
                Log.e(TAG, "TTS initialization failed with status: $status")
                _state.value = VoiceState.Error("TTS initialization failed")
            }
        }
    }

    private fun setupUtteranceListener() {
        tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                Log.d(TAG, "Speech started: $utteranceId")
                _state.value = VoiceState.Speaking
            }

            override fun onDone(utteranceId: String?) {
                Log.d(TAG, "Speech completed: $utteranceId")
                utteranceId?.let { 
                    activeUtterances.remove(it)?.invoke()
                }
                updateQueueSize(-1)
                if (_queueSize.value == 0) {
                    releaseAudioFocus()
                    _state.value = VoiceState.Ready
                }
            }

            override fun onError(utteranceId: String?) {
                Log.e(TAG, "Speech error: $utteranceId")
                utteranceId?.let { activeUtterances.remove(it) }
                updateQueueSize(-1)
            }
            
            @Deprecated("Deprecated in API 21")
            override fun onError(utteranceId: String?, errorCode: Int) {
                Log.e(TAG, "Speech error: $utteranceId, code: $errorCode")
                utteranceId?.let { activeUtterances.remove(it) }
                updateQueueSize(-1)
            }
        })
    }

    private fun startQueueProcessor() {
        scope.launch {
            for (request in speechQueue) {
                if (!isInitialized) continue
                
                // Request audio focus
                requestAudioFocus()
                
                // Apply request-specific settings
                request.locale?.let { tts?.setLanguage(it) }
                tts?.setSpeechRate(request.speechRate)
                tts?.setPitch(request.pitch)
                
                val utteranceId = UUID.randomUUID().toString()
                
                val params = Bundle().apply {
                    putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, utteranceId)
                    putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, getVolumeForPriority(request.priority))
                }
                
                val result = tts?.speak(request.text, TextToSpeech.QUEUE_ADD, params, utteranceId)
                
                if (result == TextToSpeech.SUCCESS) {
                    updateQueueSize(1)
                } else {
                    Log.e(TAG, "Failed to queue speech: ${request.text}")
                }
                
                // Reset to defaults
                tts?.setLanguage(currentLocale)
                tts?.setSpeechRate(currentSpeechRate)
                tts?.setPitch(currentPitch)
            }
        }
    }

    private fun getVolumeForPriority(priority: SpeechPriority): Float {
        return when (priority) {
            SpeechPriority.LOW -> 0.7f
            SpeechPriority.NORMAL -> 0.9f
            SpeechPriority.HIGH -> 1.0f
            SpeechPriority.CRITICAL -> 1.0f
        }
    }

    override suspend fun speak(text: String) {
        speak(SpeechRequest(text))
    }

    override suspend fun speak(request: SpeechRequest) {
        if (!isInitialized) {
            Log.w(TAG, "TTS not initialized, dropping speech: ${request.text}")
            return
        }
        
        if (_queueSize.value >= MAX_QUEUE_SIZE) {
            Log.w(TAG, "Speech queue full, dropping: ${request.text}")
            return
        }
        
        speechQueue.send(request)
    }

    override suspend fun speakNow(text: String, priority: SpeechPriority) {
        if (!isInitialized) {
            Log.w(TAG, "TTS not initialized")
            return
        }
        
        // Stop current speech
        stop()
        
        // Speak immediately
        requestAudioFocus()
        
        val utteranceId = UUID.randomUUID().toString()
        val params = Bundle().apply {
            putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, utteranceId)
            putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, getVolumeForPriority(priority))
        }
        
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, params, utteranceId)
    }

    override fun stop() {
        tts?.stop()
        activeUtterances.clear()
        _queueSize.value = 0
        releaseAudioFocus()
        _state.value = VoiceState.Ready
    }

    override fun clearQueue() {
        // Create new channel to clear queue
        while (speechQueue.tryReceive().isSuccess) {
            // Drain queue
        }
        _queueSize.value = 0
    }

    override fun setLocale(locale: Locale): Boolean {
        val result = tts?.setLanguage(locale)
        return if (result == TextToSpeech.LANG_AVAILABLE || 
                   result == TextToSpeech.LANG_COUNTRY_AVAILABLE) {
            currentLocale = locale
            true
        } else {
            Log.w(TAG, "Locale not available: $locale")
            false
        }
    }

    override fun setSpeechRate(rate: Float) {
        currentSpeechRate = rate.coerceIn(0.5f, 2.0f)
        tts?.setSpeechRate(currentSpeechRate)
    }

    override fun setPitch(pitch: Float) {
        currentPitch = pitch.coerceIn(0.5f, 2.0f)
        tts?.setPitch(currentPitch)
    }

    override fun isAvailable(): Boolean = isInitialized

    override fun getAvailableLocales(): Set<Locale> {
        return tts?.availableLanguages ?: emptySet()
    }

    private fun requestAudioFocus() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (audioFocusRequest == null) {
                audioFocusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                    .setAudioAttributes(AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANT)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build())
                    .build()
            }
            audioFocusRequest?.let { audioManager.requestAudioFocus(it) }
        } else {
            @Suppress("DEPRECATION")
            audioManager.requestAudioFocus(
                null,
                AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
            )
        }
    }

    private fun releaseAudioFocus() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            audioFocusRequest?.let { audioManager.abandonAudioFocusRequest(it) }
        } else {
            @Suppress("DEPRECATION")
            audioManager.abandonAudioFocus(null)
        }
    }

    private fun updateQueueSize(delta: Int) {
        _queueSize.value = (_queueSize.value + delta).coerceAtLeast(0)
    }

    /**
     * Cleanup resources.
     */
    fun shutdown() {
        stop()
        tts?.shutdown()
        tts = null
        isInitialized = false
        _state.value = VoiceState.Idle
    }
}
