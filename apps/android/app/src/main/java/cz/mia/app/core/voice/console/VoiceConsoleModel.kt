package cz.mia.app.core.voice.console

enum class ConnectionState { DISCONNECTED, CONNECTING, CONNECTED }

enum class LedPattern { OFF, SOLID, BLINK, PULSE, BRIEF }

/** How to draw an LED colour name from the machine. Colour alone is not enough: the pattern differs too. */
data class LedLook(val argb: Long, val pattern: LedPattern)

object LedLooks {
    private val looks = mapOf(
        "off" to LedLook(0xFF2B2B2B, LedPattern.OFF),
        "blue" to LedLook(0xFF2196F3, LedPattern.SOLID),
        "green" to LedLook(0xFF4CAF50, LedPattern.SOLID),
        "yellow_countdown" to LedLook(0xFFFFC107, LedPattern.BLINK),
        "yellow_solid" to LedLook(0xFFFFC107, LedPattern.SOLID),
        "purple" to LedLook(0xFF9C27B0, LedPattern.SOLID),
        "red" to LedLook(0xFFF44336, LedPattern.SOLID),
        "orange_flash" to LedLook(0xFFFF9800, LedPattern.BLINK),
        "white_brief" to LedLook(0xFFFFFFFF, LedPattern.BRIEF),
        "blue_pulse" to LedLook(0xFF2196F3, LedPattern.PULSE),
    )

    /** An unknown name shows as a grey solid so a new colour on the Pi is visible rather than silently off. */
    private val unknown = LedLook(0xFF9E9E9E, LedPattern.SOLID)

    val known: Set<String> get() = looks.keys

    fun of(name: String): LedLook = looks[name] ?: unknown
}

enum class LogKind { STATE, FEEDBACK, SPOKEN, TRANSCRIPT, SENT, REPLY, ERROR }

data class LogLine(val kind: LogKind, val text: String, val atMs: Long)

data class VoiceConsoleState(
    val connection: ConnectionState = ConnectionState.DISCONNECTED,
    /** The machine's resting state: idle, listening, executing, window, confirming, speaking, dictating, warning. */
    val machineState: String = "idle",
    val led: String = "off",
    val tone: String = "none",
    /** The transient cue behind the current LED (`wake_caught`), null for a resting state. */
    val cue: String? = null,
    val transcript: String = "",
    /** The phrases MIA said, newest last. */
    val spoken: List<LogLine> = emptyList(),
    /** Everything that happened, newest last: the event queue shown on the screen. */
    val log: List<LogLine> = emptyList(),
    /** The verbosity the machine reported; null until it does, and again once the connection is gone. */
    val verbosity: VerbosityLevel? = null,
    val lastError: String? = null,
) {
    val ledLook: LedLook get() = LedLooks.of(led)

    /** Fold one event from the machine into the state. */
    fun reduce(event: ConsoleEvent, nowMs: Long): VoiceConsoleState = when (event) {
        is ConsoleEvent.StateChanged ->
            copy(machineState = event.current).logged(
                LogLine(LogKind.STATE, "${event.previous} -> ${event.current}", nowMs),
            )
        is ConsoleEvent.Feedback -> {
            val transient = event.state in TRANSIENT_CUES
            copy(
                led = event.led,
                tone = event.tone,
                cue = if (transient) event.state else null,
                machineState = if (transient) machineState else event.state,
            ).logged(LogLine(LogKind.FEEDBACK, "${event.state}: led ${event.led}, tone ${event.tone}", nowMs))
        }
        is ConsoleEvent.Spoken -> {
            val line = LogLine(LogKind.SPOKEN, describe(event), nowMs)
            copy(spoken = (spoken + line).takeLast(MAX_SPOKEN)).logged(line)
        }
        is ConsoleEvent.Transcript ->
            copy(transcript = event.text).logged(LogLine(LogKind.TRANSCRIPT, event.text, nowMs))
        is ConsoleEvent.Settings ->
            copy(verbosity = event.verbosity).logged(
                LogLine(LogKind.STATE, "verbosity ${event.verbosity.name.lowercase()}", nowMs),
            )
    }

    fun logged(line: LogLine): VoiceConsoleState = copy(log = (log + line).takeLast(MAX_LOG))

    companion object {
        const val MAX_LOG = 100
        const val MAX_SPOKEN = 30
        val TRANSIENT_CUES = setOf("wake_caught", "analysing", "cancelled")

        /** A warning is spoken with priority 1 and must stand out in the list. */
        private fun describe(event: ConsoleEvent.Spoken): String {
            val params = if (event.params.isEmpty()) "" else event.params.entries.joinToString(", ", " (", ")") { "${it.key}=${it.value}" }
            val mark = if (event.priority > 0) "! " else ""
            return "$mark${event.phrase}$params"
        }
    }
}
