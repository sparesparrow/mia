package cz.mia.app.core.voice.console

// @req REQ-AND-016 REQ-VOICE-017

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class VoiceConsoleModelTest {
    private fun fold(vararg events: ConsoleEvent): VoiceConsoleState =
        events.foldIndexed(VoiceConsoleState()) { i, state, event -> state.reduce(event, i.toLong()) }

    @Test
    fun `state changes and resting feedback move the machine state and the led`() {
        val state = fold(
            ConsoleEvent.StateChanged("idle", "window"),
            ConsoleEvent.Feedback("window", "yellow_countdown", "double_beep"),
        )
        assertEquals("window", state.machineState)
        assertEquals("yellow_countdown", state.led)
        assertEquals("double_beep", state.tone)
        assertNull(state.cue)
        assertEquals(LedPattern.BLINK, state.ledLook.pattern)
    }

    @Test
    fun `a transient cue shows on the led but is not a resting state`() {
        val state = fold(
            ConsoleEvent.StateChanged("idle", "listening"),
            ConsoleEvent.Feedback("wake_caught", "white_brief", "rising_beep"),
        )
        assertEquals("listening", state.machineState)
        assertEquals("wake_caught", state.cue)
        assertEquals("white_brief", state.led)
        assertEquals(LedPattern.BRIEF, state.ledLook.pattern)
    }

    @Test
    fun `the next resting feedback clears the cue`() {
        val state = fold(
            ConsoleEvent.Feedback("cancelled", "off", "falling_beep"),
            ConsoleEvent.Feedback("idle", "off", "none"),
        )
        assertNull(state.cue)
        assertEquals("idle", state.machineState)
    }

    @Test
    fun `confirming and window look different even though both are yellow`() {
        assertEquals(LedLooks.of("yellow_solid").argb, LedLooks.of("yellow_countdown").argb)
        assertTrue(LedLooks.of("yellow_solid").pattern != LedLooks.of("yellow_countdown").pattern)
    }

    @Test
    fun `an unknown led name is visible rather than off`() {
        val look = LedLooks.of("ultraviolet")
        assertEquals(LedPattern.SOLID, look.pattern)
        assertTrue(look != LedLooks.of("off"))
    }

    @Test
    fun `spoken phrases and the transcript are kept and a warning is marked`() {
        val state = fold(
            ConsoleEvent.Transcript("zapni svetla", 1),
            ConsoleEvent.Spoken("chain.announce", mapOf("parts" to "lights.on", "seconds" to "5.0"), 0, 1),
            ConsoleEvent.Spoken("warn.coolant", mapOf("value" to "112"), 1, 2),
        )
        assertEquals("zapni svetla", state.transcript)
        assertEquals(listOf("chain.announce (parts=lights.on, seconds=5.0)", "! warn.coolant (value=112)"), state.spoken.map { it.text })
    }

    @Test
    fun `the verbosity is the one the machine reports`() {
        assertEquals(null, VoiceConsoleState().verbosity)
        val state = fold(ConsoleEvent.Settings(VerbosityLevel.CHATTY), ConsoleEvent.Settings(VerbosityLevel.QUIET))
        assertEquals(VerbosityLevel.QUIET, state.verbosity)
        assertEquals("verbosity quiet", state.log.last().text)
    }

    @Test
    fun `the event queue is bounded and newest last`() {
        var state = VoiceConsoleState()
        repeat(VoiceConsoleState.MAX_LOG + 20) { state = state.reduce(ConsoleEvent.Transcript("t$it", it.toLong()), it.toLong()) }
        assertEquals(VoiceConsoleState.MAX_LOG, state.log.size)
        assertEquals("t${VoiceConsoleState.MAX_LOG + 19}", state.log.last().text)
        assertEquals("t20", state.log.first().text)
    }
}
