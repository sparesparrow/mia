package cz.mia.app.core.voice

// @req REQ-AND-009 REQ-AND-019

import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.shadows.ShadowTextToSpeech

/** Drives the real [VoiceManagerImpl] against Robolectric's text-to-speech engine. */
@RunWith(RobolectricTestRunner::class)
class VoiceManagerImplTest {
    private lateinit var voice: VoiceManagerImpl
    private lateinit var engine: ShadowTextToSpeech

    @Before
    fun setUp() {
        ShadowTextToSpeech.reset()
        voice = VoiceManagerImpl(ApplicationProvider.getApplicationContext())
        engine = shadowOf(ShadowTextToSpeech.getLastTextToSpeechInstance())
        engine.onInitListener.onInit(TextToSpeech.SUCCESS)
        idle()
    }

    private fun idle() = shadowOf(Looper.getMainLooper()).idle()

    @Test
    fun `speak adds to the engine's queue`() = runBlocking {
        voice.speak(SpeechRequest("Palivo 12 procent.", SpeechPriority.HIGH))
        idle()

        assertEquals("Palivo 12 procent.", engine.lastSpokenText)
        assertEquals(TextToSpeech.QUEUE_ADD, engine.queueMode)
    }

    @Test
    fun `speakNow flushes the queue and speaks at once`() = runBlocking {
        voice.speak(SpeechRequest("Older prompt"))
        idle()
        voice.speakNow("Teplota motoru 112 stupňů.", SpeechPriority.CRITICAL)

        assertEquals("Teplota motoru 112 stupňů.", engine.lastSpokenText)
        assertEquals(TextToSpeech.QUEUE_FLUSH, engine.queueMode)
    }

    @Test
    fun `at most twenty unfinished utterances are handed to the engine and later requests are dropped`() = runBlocking {
        // Robolectric's engine reports every utterance finished at once; a real one is still speaking.
        ShadowTextToSpeech.getLastTextToSpeechInstance().setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) = Unit
            override fun onDone(utteranceId: String?) = Unit
            @Deprecated("Deprecated in API 21")
            override fun onError(utteranceId: String?) = Unit
        })
        repeat(25) { i ->
            voice.speak(SpeechRequest("Prompt $i"))
            idle()
        }

        assertEquals(20, engine.spokenTextList.size)
        assertEquals("Prompt 19", engine.spokenTextList.last())
    }
}
