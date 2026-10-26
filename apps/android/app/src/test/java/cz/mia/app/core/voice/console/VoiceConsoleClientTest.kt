package cz.mia.app.core.voice.console

// @req REQ-AND-016 REQ-VOICE-017 REQ-AND-017

import cz.mia.app.features.voice.VoiceConsoleViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

private class FakeSocket(val url: String, val headers: Map<String, String>, val listener: VoiceSocketListener) : VoiceSocket {
    val sent = mutableListOf<WireEnvelope>()
    var closed = false
    var accept = true

    override fun send(data: ByteArray): Boolean {
        if (!accept) return false
        sent += VoiceWire.decodeEnvelope(data)
        return true
    }

    override fun close() {
        closed = true
    }

    fun deliver(envelope: WireEnvelope) = listener.onMessage(VoiceWire.encodeEnvelope(envelope))

    fun reply(to: WireEnvelope, status: WireStatus) =
        deliver(WireEnvelope(VoiceWire.SERVICE_VOICE, to.sessionId, to.op, status, to.seq, ByteArray(0)))

    fun event(sessionId: String, seq: Long, payloadOf: ConsoleEvent) =
        deliver(WireEnvelope(VoiceWire.SERVICE_VOICE, sessionId, WireOp.DATA, null, seq, eventPayload(payloadOf)))

    private fun eventPayload(event: ConsoleEvent): ByteArray {
        val fixture = VoiceFixtures.load().first { it.type == "event" && matches(it, event) }
        return VoiceWire.decodeEnvelope(fixture.bytes).payload
    }

    private fun matches(fixture: VoiceFixture, event: ConsoleEvent): Boolean =
        VoiceWire.decodeEvent(VoiceWire.decodeEnvelope(fixture.bytes).payload) == event
}

// The two Settings events in the shared fixture; the fake socket sends their bytes.
private val QUIET_SETTINGS = ConsoleEvent.Settings(VerbosityLevel.QUIET, "mia", listOf("mia"), "en", listOf("en"))
private val CHATTY_SETTINGS =
    ConsoleEvent.Settings(VerbosityLevel.CHATTY, "rimmer", listOf("mia", "holly", "rimmer"), "cs", listOf("cs", "en"))

private class FakeFactory : VoiceSocketFactory {
    val sockets = mutableListOf<FakeSocket>()
    var openImmediately = false

    override fun open(url: String, headers: Map<String, String>, listener: VoiceSocketListener): VoiceSocket {
        val socket = FakeSocket(url, headers, listener)
        sockets += socket
        if (openImmediately) listener.onOpen()
        return socket
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class VoiceConsoleClientTest {
    private val scope = TestScope(StandardTestDispatcher())
    private val factory = FakeFactory()
    private val client = VoiceConsoleClient(
        url = "ws://pi:8000/ws/voice",
        headers = mapOf("X-API-Key" to "test-key"),
        factory = factory,
        scope = scope,
        sessionId = "console-test",
        now = { 1L },
        reconnectDelaysMs = listOf(100L, 200L),
    )

    private fun connected(): FakeSocket {
        client.connect()
        val socket = factory.sockets.last()
        socket.listener.onOpen()
        val open = socket.sent.single { it.op == WireOp.OPEN }
        socket.reply(open, WireStatus.OK)
        return socket
    }

    @Test
    fun `it opens a session on connect and is connected only after the Pi says ok`() {
        client.connect()
        assertEquals(ConnectionState.CONNECTING, client.state.value.connection)
        val socket = factory.sockets.single()
        assertEquals("ws://pi:8000/ws/voice", socket.url)
        assertEquals(mapOf("X-API-Key" to "test-key"), socket.headers)
        socket.listener.onOpen()
        val open = socket.sent.single()
        assertEquals(WireOp.OPEN, open.op)
        assertEquals("console-test", open.sessionId)
        assertEquals(ConnectionState.CONNECTING, client.state.value.connection)
        socket.reply(open, WireStatus.OK)
        assertEquals(ConnectionState.CONNECTED, client.state.value.connection)
    }

    @Test
    fun `a transport that opens before the factory returns still sends its open request once`() {
        factory.openImmediately = true
        client.connect()
        assertEquals(1, factory.sockets.single().sent.count { it.op == WireOp.OPEN })
    }

    @Test
    fun `button presses become console commands once the session is open`() {
        val socket = connected()
        assertTrue(client.send(ConsoleCommand.GoNow))
        assertTrue(client.send(ConsoleCommand.Cancel))
        val data = socket.sent.filter { it.op == WireOp.DATA }
        assertEquals(2, data.size)
        assertEquals(listOf(true, true), data.map { it.sessionId == "console-test" && it.service == VoiceWire.SERVICE_VOICE })
        assertEquals(data[0].seq + 1, data[1].seq)
        assertEquals(
            listOf(
                VoiceWire.encodeCommand(ConsoleCommand.GoNow).toList(),
                VoiceWire.encodeCommand(ConsoleCommand.Cancel).toList(),
            ),
            data.map { it.payload.toList() },
        )
    }

    @Test
    fun `nothing is sent before the session is open`() {
        assertFalse(client.send(ConsoleCommand.Wake))
        client.connect()
        assertFalse(client.send(ConsoleCommand.Wake))
        assertTrue(factory.sockets.single().sent.none { it.op == WireOp.DATA })
        assertEquals(LogKind.ERROR, client.state.value.log.last().kind)
    }

    @Test
    fun `events from the Pi update the led the state and the event queue`() {
        val socket = connected()
        socket.event("console-test", 10, ConsoleEvent.StateChanged("idle", "window"))
        socket.event("console-test", 11, ConsoleEvent.Feedback("window", "yellow_countdown", "double_beep"))
        val state = client.state.value
        assertEquals("window", state.machineState)
        assertEquals("yellow_countdown", state.led)
        assertTrue(state.log.any { it.kind == LogKind.STATE })
    }

    @Test
    fun `a refused command shows as an error and keeps the connection`() {
        val socket = connected()
        client.send(ConsoleCommand.Confirm)
        socket.reply(socket.sent.last(), WireStatus.NOT_PERMITTED)
        val state = client.state.value
        assertEquals(ConnectionState.CONNECTED, state.connection)
        assertEquals("confirm: NOT_PERMITTED", state.lastError)
        assertEquals(LogKind.ERROR, state.log.last().kind)
    }

    @Test
    fun `the verbosity shown is the one the machine reports, not the one sent`() {
        val socket = connected()
        assertEquals(null, client.state.value.verbosity)
        socket.event("console-test", 2, QUIET_SETTINGS)
        assertEquals(VerbosityLevel.QUIET, client.state.value.verbosity)

        client.send(ConsoleCommand.SetVerbosity(VerbosityLevel.CHATTY))
        socket.reply(socket.sent.last(), WireStatus.OK)
        assertEquals(VerbosityLevel.QUIET, client.state.value.verbosity)
        socket.event("console-test", 3, CHATTY_SETTINGS)
        assertEquals(VerbosityLevel.CHATTY, client.state.value.verbosity)
    }

    @Test
    fun `a lost or closed connection forgets the verbosity`() {
        val socket = connected()
        socket.event(
            "console-test", 2,
            CHATTY_SETTINGS,
        )
        assertEquals("rimmer", client.state.value.persona)
        socket.listener.onFailure("reset")
        assertEquals(null, client.state.value.verbosity)
        assertEquals(null, client.state.value.persona)
        assertEquals(emptyList<String>(), client.state.value.languages)

        val again = connected()
        again.event("console-test", 2, QUIET_SETTINGS)
        client.disconnect()
        assertEquals(null, client.state.value.verbosity)
    }

    @Test
    fun `persona and language requests are sent and logged, and only the machine's report moves the selection`() {
        val socket = connected()
        assertTrue(client.send(ConsoleCommand.SwitchPersona("holly")))
        assertTrue(client.send(ConsoleCommand.SetLanguage("cs")))
        val sent = socket.sent.filter { it.op == WireOp.DATA }
        assertEquals(2, sent.size)
        sent.forEach { socket.reply(it, WireStatus.OK) }
        assertEquals(listOf("ok: persona holly", "ok: language cs"), client.state.value.log.takeLast(2).map { it.text })
        assertEquals(null, client.state.value.persona)
    }

    @Test
    fun `a refused session closes the socket and reports why`() {
        client.connect()
        val socket = factory.sockets.single()
        socket.listener.onOpen()
        socket.reply(socket.sent.single(), WireStatus.NOT_PERMITTED)
        assertTrue(socket.closed)
        assertNotNull(client.state.value.lastError)
        assertEquals(ConnectionState.CONNECTING, client.state.value.connection)
    }

    @Test
    fun `a damaged frame is logged and the next one still works`() {
        val socket = connected()
        socket.listener.onMessage(byteArrayOf(1, 2, 3))
        assertEquals(LogKind.ERROR, client.state.value.log.last().kind)
        socket.event("console-test", 12, ConsoleEvent.StateChanged("idle", "window"))
        assertEquals("window", client.state.value.machineState)
    }

    @Test
    fun `a lost connection is retried with growing delays and gives up`() {
        val first = connected()
        first.listener.onFailure("reset")
        assertEquals(ConnectionState.DISCONNECTED, client.state.value.connection)
        scope.advanceTimeBy(99)
        scope.runCurrent()
        assertEquals(1, factory.sockets.size)
        scope.advanceTimeBy(2)
        scope.runCurrent()
        assertEquals(2, factory.sockets.size)

        factory.sockets.last().listener.onFailure("reset again")
        scope.advanceTimeBy(199)
        scope.runCurrent()
        assertEquals(2, factory.sockets.size)
        scope.advanceTimeBy(2)
        scope.runCurrent()
        assertEquals(3, factory.sockets.size)

        factory.sockets.last().listener.onFailure("still down")
        scope.advanceTimeBy(60_000)
        scope.runCurrent()
        assertEquals(3, factory.sockets.size)
        assertEquals("gave up reconnecting", client.state.value.lastError)
    }

    @Test
    fun `a successful session resets the retry budget`() {
        connected().listener.onFailure("reset")
        scope.advanceTimeBy(101)
        scope.runCurrent()
        val second = factory.sockets.last()
        second.listener.onOpen()
        second.reply(second.sent.single(), WireStatus.OK)
        second.listener.onFailure("reset")
        scope.advanceTimeBy(101)
        scope.runCurrent()
        assertEquals(3, factory.sockets.size)
    }

    @Test
    fun `late callbacks from a replaced socket do not disturb the new session`() {
        val old = connected()
        old.listener.onFailure("reset")
        scope.advanceTimeBy(101)
        scope.runCurrent()
        val fresh = factory.sockets.last()
        fresh.listener.onOpen()
        fresh.reply(fresh.sent.single(), WireStatus.OK)
        assertEquals(ConnectionState.CONNECTED, client.state.value.connection)

        old.listener.onClosed()
        old.listener.onFailure("late failure")
        old.deliver(WireEnvelope(VoiceWire.SERVICE_VOICE, "console-test", WireOp.DATA, null, 99, VoiceFixtures.load().first { it.name == "event_state_changed" }.let { VoiceWire.decodeEnvelope(it.bytes).payload }))
        scope.advanceTimeBy(60_000)
        scope.runCurrent()

        assertEquals(ConnectionState.CONNECTED, client.state.value.connection)
        assertEquals("idle", client.state.value.machineState)
        assertEquals(2, factory.sockets.size)
    }

    @Test
    fun `disconnect closes the socket and does not reconnect`() {
        val socket = connected()
        client.disconnect()
        assertTrue(socket.closed)
        socket.listener.onClosed() // a late callback from the closed socket
        scope.advanceTimeBy(60_000)
        scope.runCurrent()
        assertEquals(1, factory.sockets.size)
        assertEquals(ConnectionState.DISCONNECTED, client.state.value.connection)
    }

    @Test
    fun `the key goes in a header and an empty key sends no header`() {
        assertEquals(mapOf("X-API-Key" to "abc"), VoiceConsoleViewModel.authHeaders("abc"))
        assertEquals(emptyMap<String, String>(), VoiceConsoleViewModel.authHeaders(""))
        assertEquals(emptyMap<String, String>(), VoiceConsoleViewModel.authHeaders("  "))
    }

    @Test
    fun `the console url is the websocket base plus the voice path`() {
        assertEquals("ws://10.0.2.2:8000/ws/voice", VoiceConsoleViewModel.consoleUrl("ws://10.0.2.2:8000"))
        assertEquals("wss://ws.mia-app.com/ws/voice", VoiceConsoleViewModel.consoleUrl("wss://ws.mia-app.com/"))
    }
}
