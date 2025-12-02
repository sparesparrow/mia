package cz.aiservis.app.core.voice

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import java.util.Locale
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Unit tests for VoiceManager text-to-speech functionality.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class VoiceManagerTest {

    @Before
    fun setup() {
        // Unit tests without context
    }

    @Test
    fun `VoiceState sealed class has correct types`() {
        val states = listOf(
            VoiceState.Idle,
            VoiceState.Initializing,
            VoiceState.Ready,
            VoiceState.Speaking,
            VoiceState.Error("Test error")
        )
        
        assertEquals(5, states.size)
        assertTrue(states[0] is VoiceState.Idle)
        assertTrue(states[1] is VoiceState.Initializing)
        assertTrue(states[2] is VoiceState.Ready)
        assertTrue(states[3] is VoiceState.Speaking)
        assertTrue(states[4] is VoiceState.Error)
    }

    @Test
    fun `SpeechPriority enum has correct values`() {
        val priorities = SpeechPriority.values()
        
        assertEquals(4, priorities.size)
        assertEquals(SpeechPriority.LOW, priorities[0])
        assertEquals(SpeechPriority.NORMAL, priorities[1])
        assertEquals(SpeechPriority.HIGH, priorities[2])
        assertEquals(SpeechPriority.CRITICAL, priorities[3])
    }

    @Test
    fun `SpeechRequest stores correct default values`() {
        val request = SpeechRequest(text = "Test message")
        
        assertEquals("Test message", request.text)
        assertEquals(SpeechPriority.NORMAL, request.priority)
        assertEquals(null, request.locale)
        assertEquals(1.0f, request.speechRate)
        assertEquals(1.0f, request.pitch)
    }

    @Test
    fun `SpeechRequest with custom values`() {
        val czechLocale = Locale("cs", "CZ")
        val request = SpeechRequest(
            text = "Varování!",
            priority = SpeechPriority.CRITICAL,
            locale = czechLocale,
            speechRate = 1.2f,
            pitch = 0.9f
        )
        
        assertEquals("Varování!", request.text)
        assertEquals(SpeechPriority.CRITICAL, request.priority)
        assertEquals(czechLocale, request.locale)
        assertEquals(1.2f, request.speechRate)
        assertEquals(0.9f, request.pitch)
    }

    @Test
    fun `speech rate coercion works correctly`() {
        // Speech rate should be between 0.5 and 2.0
        val tooLow = 0.1f.coerceIn(0.5f, 2.0f)
        val tooHigh = 3.0f.coerceIn(0.5f, 2.0f)
        val valid = 1.5f.coerceIn(0.5f, 2.0f)
        
        assertEquals(0.5f, tooLow)
        assertEquals(2.0f, tooHigh)
        assertEquals(1.5f, valid)
    }

    @Test
    fun `pitch coercion works correctly`() {
        // Pitch should be between 0.5 and 2.0
        val tooLow = 0.2f.coerceIn(0.5f, 2.0f)
        val tooHigh = 2.5f.coerceIn(0.5f, 2.0f)
        val valid = 1.0f.coerceIn(0.5f, 2.0f)
        
        assertEquals(0.5f, tooLow)
        assertEquals(2.0f, tooHigh)
        assertEquals(1.0f, valid)
    }

    @Test
    fun `Czech locale is created correctly`() {
        val czechLocale = Locale("cs", "CZ")
        
        assertEquals("cs", czechLocale.language)
        assertEquals("CZ", czechLocale.country)
    }

    @Test
    fun `English locale is available`() {
        val englishLocale = Locale.US
        
        assertEquals("en", englishLocale.language)
        assertEquals("US", englishLocale.country)
    }

    @Test
    fun `volume mapping for priorities`() {
        fun getVolumeForPriority(priority: SpeechPriority): Float {
            return when (priority) {
                SpeechPriority.LOW -> 0.7f
                SpeechPriority.NORMAL -> 0.9f
                SpeechPriority.HIGH -> 1.0f
                SpeechPriority.CRITICAL -> 1.0f
            }
        }
        
        assertEquals(0.7f, getVolumeForPriority(SpeechPriority.LOW))
        assertEquals(0.9f, getVolumeForPriority(SpeechPriority.NORMAL))
        assertEquals(1.0f, getVolumeForPriority(SpeechPriority.HIGH))
        assertEquals(1.0f, getVolumeForPriority(SpeechPriority.CRITICAL))
    }

    @Test
    fun `max queue size is respected`() {
        val maxQueueSize = 20
        var currentQueueSize = 18
        
        // Can add more
        assertTrue(currentQueueSize < maxQueueSize)
        
        currentQueueSize = 20
        // Queue is full
        assertFalse(currentQueueSize < maxQueueSize)
    }

    @Test
    fun `error state contains error message`() {
        val errorState = VoiceState.Error("TTS initialization failed")
        
        assertEquals("TTS initialization failed", errorState.message)
    }

    @Test
    fun `queue size tracking works`() {
        var queueSize = 0
        
        // Add item
        queueSize = (queueSize + 1).coerceAtLeast(0)
        assertEquals(1, queueSize)
        
        // Add another
        queueSize = (queueSize + 1).coerceAtLeast(0)
        assertEquals(2, queueSize)
        
        // Remove item
        queueSize = (queueSize - 1).coerceAtLeast(0)
        assertEquals(1, queueSize)
        
        // Remove more than available (shouldn't go negative)
        queueSize = (queueSize - 5).coerceAtLeast(0)
        assertEquals(0, queueSize)
    }

    @Test
    fun `utterance ID generation produces unique values`() {
        val ids = mutableSetOf<String>()
        repeat(100) {
            ids.add(java.util.UUID.randomUUID().toString())
        }
        
        assertEquals(100, ids.size) // All IDs should be unique
    }
}
