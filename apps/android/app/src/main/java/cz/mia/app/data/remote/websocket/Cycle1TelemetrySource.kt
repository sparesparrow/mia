package cz.mia.app.data.remote.websocket

import cz.mia.app.core.networking.PiConnection
import cz.mia.app.core.networking.PiConnectionProvider
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

/** Opens a telemetry connection to a Pi. */
fun interface TelemetryStreamFactory {
    fun open(target: PiConnection): TelemetryStream
}

/**
 * One Cycle 1 telemetry connection to the Pi, shared by the dashboard and the driving service (REQ-AND-012,
 * REQ-AND-019).
 *
 * The socket is open while at least one [Lease] is held, and follows the Pi address and key in Settings: a change
 * closes the old connection and opens one to the new target. The Pi resends its newest envelope ten times a second
 * whether or not it changed, and has no real-time clock, so freshness is judged by when the envelope's timestamp
 * last changed on this phone: after [staleAfterMs] without a change, [isStale] is true.
 */
@Singleton
class Cycle1TelemetrySource(
    private val connections: StateFlow<PiConnection>,
    private val factory: TelemetryStreamFactory,
    private val scope: CoroutineScope,
    private val now: () -> Long = System::currentTimeMillis,
    private val staleAfterMs: Long = STALE_AFTER_MS,
) {
    @Inject
    constructor(provider: PiConnectionProvider, factory: TelemetryStreamFactory) :
        this(provider.connections, factory, CoroutineScope(SupervisorJob() + Dispatchers.IO))

    /** Held by whoever needs telemetry; [release] it when done. */
    inner class Lease internal constructor() {
        private var released = false

        fun release() {
            synchronized(this@Cycle1TelemetrySource) {
                if (released) return
                released = true
                holders--
                if (holders == 0) stop()
            }
        }
    }

    private val _envelope = MutableStateFlow<Cycle1TelemetryEnvelope?>(null)
    val envelope: StateFlow<Cycle1TelemetryEnvelope?> = _envelope.asStateFlow()

    private val _connection = MutableStateFlow<WebSocketState>(WebSocketState.Disconnected)
    val connection: StateFlow<WebSocketState> = _connection.asStateFlow()

    private var holders = 0
    private var job: Job? = null

    @Volatile
    private var lastTimestamp: String? = null

    @Volatile
    private var lastChangeAt = 0L

    fun acquire(): Lease = synchronized(this) {
        holders++
        if (holders == 1) start()
        Lease()
    }

    /** True when there is no envelope, or its timestamp has not changed for [staleAfterMs]. */
    fun isStale(): Boolean = _envelope.value == null || now() - lastChangeAt > staleAfterMs

    private fun start() {
        job = scope.launch {
            connections.collectLatest { target ->
                val stream = factory.open(target)
                try {
                    val state = launch { stream.stateFlow.collect { _connection.value = it } }
                    val messages = launch {
                        stream.telemetryFlow.collect { message -> message.vehicleTelemetry?.let(::accept) }
                    }
                    stream.connect()
                    state.join()
                    messages.join()
                } finally {
                    stream.cleanup()
                }
            }
        }
    }

    private fun stop() {
        job?.cancel()
        job = null
        _connection.value = WebSocketState.Disconnected
    }

    private fun accept(envelope: Cycle1TelemetryEnvelope) {
        if (envelope.timestamp != lastTimestamp) {
            lastTimestamp = envelope.timestamp
            lastChangeAt = now()
        }
        _envelope.value = envelope
    }

    companion object {
        const val STALE_AFTER_MS = 10_000L
    }
}
