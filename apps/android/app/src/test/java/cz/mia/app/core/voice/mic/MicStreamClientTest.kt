package cz.mia.app.core.voice.mic

// @req REQ-AND-027

import cz.mia.app.core.voice.console.VoiceSocket
import cz.mia.app.core.voice.console.VoiceSocketFactory
import cz.mia.app.core.voice.console.VoiceSocketListener
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

private class FakeMicSocket(val url: String, val headers: Map<String, String>, val listener: VoiceSocketListener) : VoiceSocket {
    val texts = mutableListOf<String>()
    val frames = mutableListOf<ByteArray>()
    var queued = 0L
    var closed = false

    override fun send(data: ByteArray): Boolean {
        frames += data
        return true
    }

    override fun sendText(text: String): Boolean {
        texts += text
        return true
    }

    override fun queuedBytes(): Long = queued

    override fun close() {
        closed = true
    }
}

private class FakeMicFactory : VoiceSocketFactory {
    val sockets = mutableListOf<FakeMicSocket>()

    override fun open(url: String, headers: Map<String, String>, listener: VoiceSocketListener): VoiceSocket =
        FakeMicSocket(url, headers, listener).also { sockets += it }
}

@OptIn(ExperimentalCoroutinesApi::class)
class MicStreamClientTest {
    private val scope = TestScope(StandardTestDispatcher())
    private val factory = FakeMicFactory()
    private val client = MicStreamClient("ws://pi:8000/ws/audio", mapOf("X-API-Key" to "k"), factory, scope)
    private val frame = ByteArray(MicProtocol.FRAME_BYTES)

    private fun ready(): FakeMicSocket {
        val socket = factory.sockets.last()
        socket.listener.onOpen()
        socket.listener.onText("""{"ok":true}""")
        return socket
    }

    @Test
    fun `it sends the header on open and is ready only after the ok`() {
        client.start()
        val socket = factory.sockets.single()
        assertEquals("ws://pi:8000/ws/audio", socket.url)
        assertEquals(mapOf("X-API-Key" to "k"), socket.headers)
        assertEquals(MicLink.CONNECTING, client.link.value)
        socket.listener.onOpen()
        assertEquals(listOf(MicProtocol.HEADER), socket.texts)
        assertEquals(MicLink.CONNECTING, client.link.value)
        socket.listener.onText("""{"ok":true}""")
        assertEquals(MicLink.READY, client.link.value)
    }

    @Test
    fun `it sends the header when open fires synchronously before the factory returns`() {
        lateinit var socket: FakeMicSocket
        val synchronousFactory = object : VoiceSocketFactory {
            override fun open(url: String, headers: Map<String, String>, listener: VoiceSocketListener): VoiceSocket =
                FakeMicSocket(url, headers, listener).also {
                    socket = it
                    listener.onOpen()
                }
        }
        val synchronousClient = MicStreamClient("ws://pi:8000/ws/audio", emptyMap(), synchronousFactory, scope)

        synchronousClient.start()

        assertEquals(listOf(MicProtocol.HEADER), socket.texts)
        socket.listener.onOpen()
        assertEquals(listOf(MicProtocol.HEADER), socket.texts)
    }

    @Test
    fun `frames are dropped until ready and sent after`() {
        client.start()
        assertFalse(client.sendFrame(frame))
        val socket = ready()
        assertTrue(client.sendFrame(frame))
        assertEquals(1, socket.frames.size)
        assertEquals(1L, client.droppedFrames)
    }

    @Test
    fun `a frame is dropped when more than six are queued`() {
        client.start()
        val socket = ready()
        socket.queued = 7L * MicProtocol.FRAME_BYTES
        assertFalse(client.sendFrame(frame))
        assertTrue(socket.frames.isEmpty())
        socket.queued = 0
        assertTrue(client.sendFrame(frame))
    }

    @Test
    fun `it reconnects after 1, 2 and 4 seconds and starts over after an ok`() {
        client.start()
        factory.sockets.last().listener.onFailure("down")
        scope.advanceTimeBy(999); scope.runCurrent()
        assertEquals(1, factory.sockets.size)
        scope.advanceTimeBy(2); scope.runCurrent()
        assertEquals(2, factory.sockets.size)

        factory.sockets.last().listener.onClosed()
        scope.advanceTimeBy(1999); scope.runCurrent()
        assertEquals(2, factory.sockets.size)
        scope.advanceTimeBy(2); scope.runCurrent()
        assertEquals(3, factory.sockets.size)

        factory.sockets.last().listener.onFailure("down")
        scope.advanceTimeBy(3999); scope.runCurrent()
        assertEquals(3, factory.sockets.size)
        scope.advanceTimeBy(2); scope.runCurrent()
        assertEquals(4, factory.sockets.size)

        ready()
        factory.sockets.last().listener.onFailure("down")
        scope.advanceTimeBy(1001); scope.runCurrent()
        assertEquals(5, factory.sockets.size)
    }

    @Test
    fun `stop closes the socket and nothing reconnects`() {
        client.start()
        val socket = ready()
        client.stop()
        assertTrue(socket.closed)
        assertEquals(MicLink.OFF, client.link.value)
        socket.listener.onFailure("late")
        scope.advanceTimeBy(10_000); scope.runCurrent()
        assertEquals(1, factory.sockets.size)
        assertFalse(client.sendFrame(frame))
    }
}
