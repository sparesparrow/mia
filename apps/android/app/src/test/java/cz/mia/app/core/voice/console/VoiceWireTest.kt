package cz.mia.app.core.voice.console

// @req REQ-AND-016

import MiaVoice.Led
import MiaVoice.State
import MiaVoice.Tone
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }

class VoiceWireTest {
    private val fixtures = VoiceFixtures.load()

    private fun commandFor(name: String): ConsoleCommand = when (name) {
        "wake" -> ConsoleCommand.Wake
        "go_now" -> ConsoleCommand.GoNow
        "cancel" -> ConsoleCommand.Cancel
        "confirm" -> ConsoleCommand.Confirm
        "deny" -> ConsoleCommand.Deny
        "end_dictation" -> ConsoleCommand.EndDictation
        "verbosity_quiet" -> ConsoleCommand.SetVerbosity(VerbosityLevel.QUIET)
        "verbosity_normal" -> ConsoleCommand.SetVerbosity(VerbosityLevel.NORMAL)
        "verbosity_chatty" -> ConsoleCommand.SetVerbosity(VerbosityLevel.CHATTY)
        else -> error("fixture command $name has no console equivalent")
    }

    @Test
    fun `fixture file has every kind of case`() {
        assertEquals(setOf("open", "command", "event", "reply"), fixtures.map { it.type }.toSet())
    }

    @Test
    fun `console commands encode to the very bytes the Pi codec writes`() {
        val commands = fixtures.filter { it.type == "command" }
        assertEquals(9, commands.size)
        for (fixture in commands) {
            val envelope = WireEnvelope(
                VoiceWire.SERVICE_VOICE, fixture.session, WireOp.DATA, null, fixture.seq,
                VoiceWire.encodeCommand(commandFor(fixture.command)),
            )
            assertEquals(fixture.name, fixture.bytes.toHex(), VoiceWire.encodeEnvelope(envelope).toHex())
        }
    }

    @Test
    fun `an open request encodes to the bytes the Pi codec writes`() {
        val open = fixtures.single { it.type == "open" }
        val envelope = WireEnvelope(VoiceWire.SERVICE_VOICE, open.session, WireOp.OPEN, null, open.seq, ByteArray(0))
        assertArrayEquals(open.bytes, VoiceWire.encodeEnvelope(envelope))
    }

    @Test
    fun `events written by the Pi decode to what the fixture says`() {
        val events = fixtures.filter { it.type == "event" }
        assertTrue(events.size >= 7)
        for (fixture in events) {
            val envelope = VoiceWire.decodeEnvelope(fixture.bytes)
            assertEquals(fixture.name, fixture.session, envelope.sessionId)
            assertEquals(fixture.name, fixture.seq, envelope.seq)
            val decoded = VoiceWire.decodeEvent(envelope.payload)
            val expect = fixture.event
            when (expect["kind"].asString) {
                "state_changed" -> assertEquals(
                    fixture.name,
                    ConsoleEvent.StateChanged(expect["previous"].asString, expect["current"].asString),
                    decoded,
                )
                "feedback" -> assertEquals(
                    fixture.name,
                    ConsoleEvent.Feedback(expect["state"].asString, expect["led"].asString, expect["tone"].asString),
                    decoded,
                )
                "spoken" -> assertEquals(
                    fixture.name,
                    ConsoleEvent.Spoken(
                        expect["phrase"].asString,
                        expect["params"].asJsonObject.entrySet().associate { it.key to it.value.asString },
                        expect["priority"].asInt,
                        expect["utterance_id"].asLong,
                    ),
                    decoded,
                )
                "transcript" -> assertEquals(
                    fixture.name,
                    ConsoleEvent.Transcript(expect["text"].asString, expect["utterance_id"].asLong),
                    decoded,
                )
                else -> fail("unknown fixture kind in ${fixture.name}")
            }
        }
    }

    @Test
    fun `replies carry their status and no payload`() {
        for (fixture in fixtures.filter { it.type == "reply" }) {
            val envelope = VoiceWire.decodeEnvelope(fixture.bytes)
            assertEquals(fixture.name, fixture.status, envelope.status.toString().lowercase())
            assertEquals(fixture.name, 0, envelope.payload.size)
            assertEquals(fixture.name, VoiceWire.VERSION, envelope.version)
        }
    }

    @Test
    fun `envelope round trips`() {
        val original = WireEnvelope(VoiceWire.SERVICE_VOICE, "s", WireOp.CLOSE, WireStatus.NOT_PERMITTED, 4_000_000_000L, byteArrayOf(1, 2, 3))
        assertEquals(original, VoiceWire.decodeEnvelope(VoiceWire.encodeEnvelope(original)))
    }

    @Test
    fun `garbage is a wire exception and nothing else`() {
        val samples = listOf(ByteArray(0), ByteArray(40) { 0x7f }, "not a flatbuffer".toByteArray(), fixtures.first { it.type == "event" }.bytes.copyOf(14))
        for (bytes in samples) {
            try {
                VoiceWire.decodeEnvelope(bytes)
                fail("accepted ${bytes.size} bytes")
            } catch (expected: VoiceWireException) {
                // fine
            }
        }
        val payload = VoiceWire.decodeEnvelope(fixtures.first { it.type == "event" }.bytes).payload
        for (cut in listOf(0, 3, payload.size / 2)) {
            try {
                VoiceWire.decodeEvent(payload.copyOf(cut))
            } catch (expected: VoiceWireException) {
                // fine
            }
        }
    }

    @Test
    fun `a command payload is not an event`() {
        try {
            VoiceWire.decodeEvent(VoiceWire.encodeCommand(ConsoleCommand.GoNow))
            fail("a command was accepted as an event")
        } catch (expected: VoiceWireException) {
            // fine
        }
    }

    @Test
    fun `random byte damage never escapes as another exception`() {
        val rng = java.util.Random(7)
        val good = fixtures.first { it.name == "event_spoken_announce" }.bytes
        repeat(2000) {
            val bytes = good.copyOf()
            repeat(1 + rng.nextInt(4)) { bytes[rng.nextInt(bytes.size)] = rng.nextInt(256).toByte() }
            val cut = if (rng.nextInt(3) == 0) bytes.copyOf(rng.nextInt(bytes.size)) else bytes
            try {
                VoiceWire.decodeEvent(VoiceWire.decodeEnvelope(cut).payload)
            } catch (expected: VoiceWireException) {
                // fine
            }
        }
    }

    @Test
    fun `led and tone names of the schema all have a look or a known tone`() {
        val schemaLeds = Led.names.map { VoiceWire.snake(it) }.toSet()
        assertEquals(schemaLeds, LedLooks.known)
        assertTrue(Tone.names.size > 1 && State.names.size == 8)
    }
}
