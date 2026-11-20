package cz.mia.app.core.voice.mic

// @req REQ-AND-027

import cz.mia.app.core.voice.console.ConnectionState
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MicFramingTest {
    @Test
    fun `a frame is 960 bytes, 30 ms of 16 kHz mono PCM16`() {
        assertEquals(960, MicProtocol.FRAME_BYTES)
    }

    @Test
    fun `the framer cuts any read size into whole frames and keeps the rest`() {
        val framer = MicFramer()
        assertTrue(framer.add(ByteArray(500) { 1 }).isEmpty())
        val frames = framer.add(ByteArray(1500) { 2 })
        assertEquals(2, frames.size)
        assertTrue(frames.all { it.size == 960 })
        // 500 + 1500 = 2000 bytes: two frames out, 80 bytes wait; the first frame starts with the first read.
        assertEquals(1.toByte(), frames[0][0])
        assertEquals(2.toByte(), frames[0][500])
        assertEquals(1, framer.add(ByteArray(880)).size)
    }

    @Test
    fun `the framer honours the length of a read, not the size of the buffer`() {
        val framer = MicFramer()
        assertEquals(1, framer.add(ByteArray(2000), 960).size)
    }

    @Test
    fun `reset forgets a half frame`() {
        val framer = MicFramer()
        framer.add(ByteArray(400))
        framer.reset()
        assertTrue(framer.add(ByteArray(600)).isEmpty())
    }

    @Test
    fun `frames are dropped when more than six are queued`() {
        assertFalse(MicProtocol.shouldDrop(6L * 960))
        assertTrue(MicProtocol.shouldDrop(6L * 960 + 1))
        assertFalse(MicProtocol.shouldDrop(0))
    }

    @Test
    fun `reconnect waits 1, 2 and then 4 seconds`() {
        assertEquals(listOf(1000L, 2000L, 4000L, 4000L, 4000L), (0..4).map { MicProtocol.reconnectDelayMs(it) })
    }

    @Test
    fun `only the Pi's ok answer opens the stream`() {
        assertTrue(MicProtocol.isOk("""{"ok":true}"""))
        assertTrue(MicProtocol.isOk("""{ "ok" : true }"""))
        assertFalse(MicProtocol.isOk("""{"mic":"open","reason":"speaking"}"""))
        assertFalse(MicProtocol.isOk("""{"ok":false}"""))
    }

    @Test
    fun `the header names the one format the Pi accepts`() {
        assertEquals("""{"v":1,"fmt":"s16le","rate":16000,"ch":1,"frame_ms":30}""", MicProtocol.HEADER)
    }

    @Test
    fun `audio streams only while the Pi machine is listening and the console is connected`() {
        assertTrue(PushToTalk.streaming("listening", ConnectionState.CONNECTED))
        for (state in listOf("idle", "executing", "window", "confirming", "speaking", "dictating", "warning")) {
            assertFalse(state, PushToTalk.streaming(state, ConnectionState.CONNECTED))
        }
        assertFalse(PushToTalk.streaming("listening", ConnectionState.DISCONNECTED))
        assertFalse(PushToTalk.streaming("listening", ConnectionState.CONNECTING))
    }

    @Test
    fun `framer output is the input bytes in order`() {
        val framer = MicFramer()
        val input = ByteArray(1920) { (it % 251).toByte() }
        val out = framer.add(input.copyOfRange(0, 700)) + framer.add(input.copyOfRange(700, 1920))
        assertArrayEquals(input, out.fold(ByteArray(0)) { acc, f -> acc + f })
    }
}
