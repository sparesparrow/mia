package cz.mia.app.core.voice.mic

import cz.mia.app.core.voice.console.VoiceSocket
import cz.mia.app.core.voice.console.VoiceSocketFactory
import cz.mia.app.core.voice.console.VoiceSocketListener
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class MicLink { OFF, CONNECTING, READY }

/**
 * The phone's end of `/ws/audio` (ADR-0021): opens the socket, sends the format header, waits for `{"ok":true}`,
 * then sends 960-byte frames. A frame is dropped, never waited for, when the socket has more than
 * [MicProtocol.MAX_QUEUED_FRAMES] frames queued or is not ready. After a loss it reconnects after 1, 2 and then
 * 4 s until [stop].
 */
class MicStreamClient(
    private val url: String,
    private val headers: Map<String, String>,
    private val factory: VoiceSocketFactory,
    private val scope: CoroutineScope,
) {
    private val lock = Any()
    private val _link = MutableStateFlow(MicLink.OFF)
    val link: StateFlow<MicLink> = _link.asStateFlow()

    // Guarded by lock.
    private var socket: VoiceSocket? = null
    private var generation = 0
    private var openingGeneration: Int? = null
    private var wanted = false
    private var attempt = 0
    private var dropped = 0L
    private var sentFrames = 0L

    val droppedFrames: Long get() = synchronized(lock) { dropped }
    val sentFrameCount: Long get() = synchronized(lock) { sentFrames }

    fun start() {
        synchronized(lock) {
            wanted = true
            if (socket != null || openingGeneration != null) return
            attempt = 0
        }
        open()
    }

    fun stop() {
        val toClose: VoiceSocket?
        synchronized(lock) {
            wanted = false
            generation++
            openingGeneration = null
            toClose = socket
            socket = null
        }
        toClose?.close()
        _link.value = MicLink.OFF
    }

    /** True when the frame went to the socket; false when it was dropped. Safe to call from the capture thread. */
    fun sendFrame(frame: ByteArray): Boolean {
        val target: VoiceSocket
        synchronized(lock) {
            val open = socket
            if (open == null || _link.value != MicLink.READY) {
                dropped++
                return false
            }
            target = open
        }
        if (MicProtocol.shouldDrop(target.queuedBytes()) || !target.send(frame)) {
            synchronized(lock) { dropped++ }
            return false
        }
        synchronized(lock) { sentFrames++ }
        return true
    }

    private fun open() {
        val mine: Int
        synchronized(lock) {
            if (!wanted || socket != null || openingGeneration != null) return
            mine = ++generation
            openingGeneration = mine
        }
        _link.value = MicLink.CONNECTING
        var openArrivedBeforeSocket = false
        var headerSent = false
        val listener = object : VoiceSocketListener {
            override fun onOpen() {
                val target = synchronized(lock) {
                    if (generation != mine) return
                    val current = socket
                    if (current == null) {
                        openArrivedBeforeSocket = true
                        null
                    } else if (!headerSent) {
                        headerSent = true
                        current
                    } else {
                        null
                    }
                } ?: return
                target.sendText(MicProtocol.HEADER)
            }

            override fun onMessage(data: ByteArray) = Unit

            override fun onText(text: String) {
                if (!MicProtocol.isOk(text)) return
                synchronized(lock) {
                    if (generation != mine) return
                    attempt = 0
                }
                _link.value = MicLink.READY
            }

            override fun onClosed() = lost(mine)

            override fun onFailure(message: String) = lost(mine)
        }
        val created = try {
            factory.open(url, headers, listener)
        } catch (e: Exception) {
            lost(mine)
            return
        }
        var sendHeader = false
        val keep = synchronized(lock) {
            if (generation == mine && openingGeneration == mine) {
                socket = created
                openingGeneration = null
                if (openArrivedBeforeSocket && !headerSent) {
                    headerSent = true
                    sendHeader = true
                }
                true
            } else {
                false
            }
        }
        if (!keep) created.close() else if (sendHeader) created.sendText(MicProtocol.HEADER)
    }

    private fun lost(mine: Int) {
        val delayMs: Long
        synchronized(lock) {
            if (generation != mine) return
            socket = null
            openingGeneration = null
            generation++
            if (!wanted) return
            delayMs = MicProtocol.reconnectDelayMs(attempt)
            attempt++
        }
        _link.value = MicLink.CONNECTING
        val wait = synchronized(lock) { generation }
        scope.launch {
            delay(delayMs)
            val again = synchronized(lock) { wanted && generation == wait && socket == null }
            if (again) open()
        }
    }
}
