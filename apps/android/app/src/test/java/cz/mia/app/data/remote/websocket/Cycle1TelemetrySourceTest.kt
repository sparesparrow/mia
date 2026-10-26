package cz.mia.app.data.remote.websocket

// @req REQ-AND-012 REQ-AND-019

import com.google.gson.JsonPrimitive
import cz.mia.app.core.networking.PiConnection
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.dto.Cycle1TelemetrySignal
import cz.mia.app.data.remote.dto.WebSocketMessage
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.runCurrent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private class FakeStream(val target: PiConnection) : TelemetryStream {
    override val telemetryFlow = MutableSharedFlow<WebSocketMessage>(extraBufferCapacity = 16)
    override val stateFlow = MutableSharedFlow<WebSocketState>(replay = 1, extraBufferCapacity = 8)
    var connected = false
    var cleanedUp = false

    override fun connect() {
        connected = true
    }

    override fun cleanup() {
        cleanedUp = true
    }
}

private fun envelopeAt(timestamp: String) = Cycle1TelemetryEnvelope(
    schemaVersion = 1,
    messageType = "vehicle.telemetry",
    deviceId = "esp32-test",
    timestamp = timestamp,
    source = "replay",
    confidence = 1.0,
    signals = mapOf("coolant_temp_c" to Cycle1TelemetrySignal(JsonPrimitive(86.0), "C", "replay", 1.0)),
)

@OptIn(ExperimentalCoroutinesApi::class)
class Cycle1TelemetrySourceTest {
    private val scope = TestScope(StandardTestDispatcher())
    private val first = PiConnection("http://10.0.0.2:8000", "ws://10.0.0.2:8000", "key-1")
    private val second = PiConnection("http://10.0.0.3:8000", "ws://10.0.0.3:8000", "key-2")
    private val connections = MutableStateFlow(first)
    private val streams = mutableListOf<FakeStream>()
    private var time = 0L
    private val source = Cycle1TelemetrySource(
        connections = connections,
        factory = TelemetryStreamFactory { target -> FakeStream(target).also { streams += it } },
        scope = scope,
        now = { time },
        staleAfterMs = 10_000,
    )

    @Test
    fun `nothing connects until someone acquires, and two holders share one connection`() {
        scope.runCurrent()
        assertTrue(streams.isEmpty())

        val dashboard = source.acquire()
        val service = source.acquire()
        scope.runCurrent()
        assertEquals(1, streams.size)
        assertTrue(streams.single().connected)

        dashboard.release()
        scope.runCurrent()
        assertFalse(streams.single().cleanedUp)

        service.release()
        scope.runCurrent()
        assertTrue(streams.single().cleanedUp)
        assertEquals(WebSocketState.Disconnected, source.connection.value)
    }

    @Test
    fun `releasing a lease twice counts once`() {
        val a = source.acquire()
        val b = source.acquire()
        scope.runCurrent()
        a.release()
        a.release()
        scope.runCurrent()
        assertFalse(streams.single().cleanedUp)
        b.release()
        scope.runCurrent()
        assertTrue(streams.single().cleanedUp)
    }

    @Test
    fun `a new Pi address or key closes the old connection and opens one to the new target`() {
        source.acquire()
        scope.runCurrent()
        connections.value = second
        scope.runCurrent()

        assertEquals(2, streams.size)
        assertTrue(streams[0].cleanedUp)
        assertEquals(second, streams[1].target)
        assertTrue(streams[1].connected)
    }

    @Test
    fun `envelopes and connection state are passed on`() {
        source.acquire()
        scope.runCurrent()
        val stream = streams.single()
        stream.stateFlow.tryEmit(WebSocketState.Connected)
        stream.telemetryFlow.tryEmit(WebSocketMessage(timestamp = "t", vehicleTelemetry = envelopeAt("2026-10-25T10:00:00Z")))
        stream.telemetryFlow.tryEmit(WebSocketMessage(timestamp = "t"))
        scope.runCurrent()

        assertEquals(WebSocketState.Connected, source.connection.value)
        assertEquals("2026-10-25T10:00:00Z", source.envelope.value?.timestamp)
    }

    @Test
    fun `an envelope whose timestamp stops changing goes stale even while it is resent`() {
        assertNull(source.envelope.value)
        assertTrue(source.isStale())

        source.acquire()
        scope.runCurrent()
        val stream = streams.single()
        stream.telemetryFlow.tryEmit(WebSocketMessage(timestamp = "t", vehicleTelemetry = envelopeAt("a")))
        scope.runCurrent()
        assertFalse(source.isStale())

        time = 8_000
        stream.telemetryFlow.tryEmit(WebSocketMessage(timestamp = "t", vehicleTelemetry = envelopeAt("a")))
        scope.runCurrent()
        time = 10_001
        assertTrue(source.isStale())

        stream.telemetryFlow.tryEmit(WebSocketMessage(timestamp = "t", vehicleTelemetry = envelopeAt("b")))
        scope.runCurrent()
        assertFalse(source.isStale())
    }
}
