package cz.mia.app.core.voice.mic

import cz.mia.app.core.networking.Backoff
import cz.mia.app.core.voice.console.ConnectionState

/** The phone microphone stream's wire facts (ADR-0021, REQ-AND-027). */
object MicProtocol {
    const val SAMPLE_RATE = 16000
    const val FRAME_MS = 30

    /** 480 samples of PCM16 mono: 30 ms. */
    const val FRAME_BYTES = SAMPLE_RATE * FRAME_MS / 1000 * 2

    /** More queued frames than this and the next frame is dropped: capture never waits for the network. */
    const val MAX_QUEUED_FRAMES = 6

    /** The first frame of every connection; the Pi answers `{"ok":true}` or closes with 1003. */
    const val HEADER = """{"v":1,"fmt":"s16le","rate":16000,"ch":1,"frame_ms":30}"""

    val RECONNECT_DELAYS_MS: List<Long> = Backoff.linearDelays(1000, 2000, 4000)

    fun reconnectDelayMs(attempt: Int): Long =
        RECONNECT_DELAYS_MS[attempt.coerceIn(0, RECONNECT_DELAYS_MS.lastIndex)]

    fun shouldDrop(queuedBytes: Long): Boolean = queuedBytes > MAX_QUEUED_FRAMES.toLong() * FRAME_BYTES

    fun isOk(text: String): Boolean = Regex("\"ok\"\\s*:\\s*true").containsMatchIn(text)
}

/** Cuts whatever size `AudioRecord.read` returns into whole 960-byte frames; the rest waits for the next read. */
class MicFramer(private val frameBytes: Int = MicProtocol.FRAME_BYTES) {
    private var pending = ByteArray(0)

    fun add(chunk: ByteArray, length: Int = chunk.size): List<ByteArray> {
        if (length <= 0) return emptyList()
        val data = pending + chunk.copyOf(length)
        val frames = ArrayList<ByteArray>(data.size / frameBytes)
        var offset = 0
        while (data.size - offset >= frameBytes) {
            frames += data.copyOfRange(offset, offset + frameBytes)
            offset += frameBytes
        }
        pending = data.copyOfRange(offset, data.size)
        return frames
    }

    /** Forget a half frame, for example when streaming pauses, so old audio never leads the next utterance. */
    fun reset() {
        pending = ByteArray(0)
    }
}

/**
 * Push-to-talk (ADR-0021): audio goes to the Pi only from the console's Wake until the machine leaves
 * `listening`, as the Pi's machine reports it in `StateChanged`. Anything else, including a lost console
 * connection, means silence leaves the phone.
 */
object PushToTalk {
    private val streamingStates = setOf("listening")

    fun streaming(machineState: String, connection: ConnectionState): Boolean =
        connection == ConnectionState.CONNECTED && machineState in streamingStates
}
