package cz.mia.app.core.voice.console

import cz.mia.app.core.networking.Backoff
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** One open WebSocket. Frames are binary envelopes. */
interface VoiceSocket {
    fun send(data: ByteArray): Boolean
    fun close()
}

interface VoiceSocketListener {
    fun onOpen()
    fun onMessage(data: ByteArray)
    fun onClosed()
    fun onFailure(message: String)
}

fun interface VoiceSocketFactory {
    fun open(url: String, listener: VoiceSocketListener): VoiceSocket
}

/**
 * The console's end of `/ws/voice` (ADR-0013): opens a session, sends the button commands, folds the
 * machine's events into a [VoiceConsoleState] and reconnects with a growing delay.
 *
 * It only knows the commands in [ConsoleCommand], which are the ones the Pi accepts from a console. It never
 * claims a command source; the Pi stamps `console` on whatever arrives.
 */
class VoiceConsoleClient(
    private val url: String,
    private val factory: VoiceSocketFactory,
    private val scope: CoroutineScope,
    private val sessionId: String = "console-" + java.util.UUID.randomUUID().toString().take(8),
    private val now: () -> Long = System::currentTimeMillis,
    private val reconnectDelaysMs: List<Long> = Backoff.exponential(baseMs = 1000, maxMs = 15000, attempts = 6),
) {
    private val lock = Any()
    private val _state = MutableStateFlow(VoiceConsoleState())
    val state: StateFlow<VoiceConsoleState> = _state.asStateFlow()

    // Guarded by lock.
    private var socket: VoiceSocket? = null
    private var transportOpen = false
    private var generation = 0
    private var wanted = false
    private var seq = 0L
    private var openSeq = -1L
    private var attempt = 0
    private val sent = mutableMapOf<Long, ConsoleCommand>()

    fun connect() {
        synchronized(lock) {
            wanted = true
            if (socket != null) return
            attempt = 0
        }
        open()
    }

    fun disconnect() {
        val toClose: VoiceSocket?
        synchronized(lock) {
            wanted = false
            generation++
            toClose = socket
            socket = null
            transportOpen = false
            sent.clear()
        }
        toClose?.close()
        _state.update { it.copy(connection = ConnectionState.DISCONNECTED) }
    }

    /** Send a button press or the verbosity setting. False if the session is not open. */
    fun send(command: ConsoleCommand): Boolean {
        val target: VoiceSocket
        val number: Long
        synchronized(lock) {
            val open = socket
            if (open == null || _state.value.connection != ConnectionState.CONNECTED) {
                _state.update { it.logged(LogLine(LogKind.ERROR, "not connected: ${name(command)} not sent", now())) }
                return false
            }
            target = open
            number = nextSeq()
            sent[number] = command
        }
        val frame = VoiceWire.encodeEnvelope(
            WireEnvelope(VoiceWire.SERVICE_VOICE, sessionId, WireOp.DATA, null, number, VoiceWire.encodeCommand(command)),
        )
        val accepted = target.send(frame)
        if (!accepted) synchronized(lock) { sent.remove(number) }
        val text = (if (accepted) "sent " else "send failed: ") + name(command)
        _state.update { it.logged(LogLine(if (accepted) LogKind.SENT else LogKind.ERROR, text, now())) }
        return accepted
    }

    private fun open() {
        val mine: Int
        synchronized(lock) {
            mine = ++generation
            transportOpen = false
        }
        _state.update { it.copy(connection = ConnectionState.CONNECTING, lastError = null) }
        // Callbacks from a socket that has been replaced or closed on purpose are ignored.
        val listener = object : VoiceSocketListener {
            override fun onOpen() {
                val ready = synchronized(lock) {
                    if (generation != mine) return
                    transportOpen = true
                    socket != null
                }
                if (ready) sendOpen()
            }

            override fun onMessage(data: ByteArray) {
                if (synchronized(lock) { generation == mine }) handle(data)
            }

            override fun onClosed() {
                if (synchronized(lock) { generation == mine }) lost(null)
            }

            override fun onFailure(message: String) {
                if (synchronized(lock) { generation == mine }) lost(message)
            }
        }
        val created = factory.open(url, listener)
        val ready = synchronized(lock) {
            if (generation != mine) {
                null
            } else {
                socket = created
                transportOpen
            }
        }
        // The transport may have opened before `factory.open` returned.
        if (ready == null) created.close() else if (ready) sendOpen()
    }

    private fun sendOpen() {
        val target: VoiceSocket?
        val number: Long
        synchronized(lock) {
            target = socket
            number = nextSeq()
            openSeq = number
        }
        val frame = VoiceWire.encodeEnvelope(
            WireEnvelope(VoiceWire.SERVICE_VOICE, sessionId, WireOp.OPEN, null, number, ByteArray(0)),
        )
        target?.send(frame)
    }

    private fun handle(data: ByteArray) {
        val envelope = try {
            VoiceWire.decodeEnvelope(data)
        } catch (e: VoiceWireException) {
            _state.update { it.logged(LogLine(LogKind.ERROR, "bad frame: ${e.message}", now())) }
            return
        }
        if (envelope.payload.isNotEmpty()) {
            try {
                val event = VoiceWire.decodeEvent(envelope.payload)
                _state.update { it.reduce(event, now()) }
            } catch (e: VoiceWireException) {
                _state.update { it.logged(LogLine(LogKind.ERROR, "bad event: ${e.message}", now())) }
            }
            return
        }
        reply(envelope)
    }

    private fun reply(envelope: WireEnvelope) {
        val status = envelope.status ?: WireStatus.OK
        val opened: Boolean
        val command: ConsoleCommand?
        synchronized(lock) {
            opened = envelope.op == WireOp.OPEN && envelope.seq == openSeq
            command = sent.remove(envelope.seq)
            if (opened && status == WireStatus.OK) attempt = 0
        }
        if (opened) {
            if (status == WireStatus.OK) {
                _state.update {
                    it.copy(connection = ConnectionState.CONNECTED)
                        .logged(LogLine(LogKind.REPLY, "session ${envelope.sessionId} open", now()))
                }
            } else {
                _state.update {
                    it.copy(lastError = "session refused: $status")
                        .logged(LogLine(LogKind.ERROR, "session refused: $status", now()))
                }
                synchronized(lock) { socket }?.close()
            }
            return
        }
        val what = command?.let { name(it) } ?: "request"
        if (status != WireStatus.OK) {
            _state.update {
                it.copy(lastError = "$what: $status").logged(LogLine(LogKind.ERROR, "refused: $what ($status)", now()))
            }
        } else if (command != null) {
            _state.update {
                val level = (command as? ConsoleCommand.SetVerbosity)?.level ?: it.verbosity
                it.copy(verbosity = level).logged(LogLine(LogKind.REPLY, "ok: $what", now()))
            }
        }
    }

    private fun lost(message: String?) {
        val retry: Boolean
        val delayMs: Long
        synchronized(lock) {
            socket = null
            transportOpen = false
            sent.clear()
            retry = wanted && attempt < reconnectDelaysMs.size
            delayMs = if (retry) reconnectDelaysMs[attempt] else 0L
            if (retry) attempt++
        }
        _state.update {
            it.copy(connection = ConnectionState.DISCONNECTED, lastError = message ?: it.lastError)
                .logged(LogLine(LogKind.ERROR, if (message != null) "connection lost: $message" else "connection closed", now()))
        }
        if (retry) {
            scope.launch {
                delay(delayMs)
                val again = synchronized(lock) { wanted && socket == null }
                if (again) open()
            }
        } else if (synchronized(lock) { wanted }) {
            _state.update { it.copy(lastError = "gave up reconnecting") }
        }
    }

    private fun nextSeq(): Long {
        seq = (seq + 1) and 0xFFFFFFFFL
        return seq
    }

    private fun name(command: ConsoleCommand): String = when (command) {
        is ConsoleCommand.Wake -> "wake"
        is ConsoleCommand.GoNow -> "go_now"
        is ConsoleCommand.Cancel -> "cancel"
        is ConsoleCommand.Confirm -> "confirm"
        is ConsoleCommand.Deny -> "deny"
        is ConsoleCommand.EndDictation -> "end_dictation"
        is ConsoleCommand.SetVerbosity -> "verbosity ${command.level.name.lowercase()}"
    }
}
