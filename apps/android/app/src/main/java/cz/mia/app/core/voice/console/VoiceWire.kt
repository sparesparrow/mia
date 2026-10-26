package cz.mia.app.core.voice.console

import MiaVoice.Arg
import MiaVoice.ArgKind
import MiaVoice.Cancel
import MiaVoice.Confirm
import MiaVoice.CueName
import MiaVoice.Deny
import MiaVoice.EndDictation
import MiaVoice.Envelope
import MiaVoice.FeedbackCue
import MiaVoice.GoNow
import MiaVoice.Led
import MiaVoice.Op
import MiaVoice.ServiceType
import MiaVoice.SetLanguage
import MiaVoice.SetVerbosity
import MiaVoice.Settings
import MiaVoice.Source
import MiaVoice.Spoken
import MiaVoice.State
import MiaVoice.StateChanged
import MiaVoice.Status
import MiaVoice.SwitchPersona
import MiaVoice.Tone
import MiaVoice.Transcript
import MiaVoice.Verbosity
import MiaVoice.VoiceBody
import MiaVoice.VoiceMessage
import MiaVoice.Wake
import com.google.flatbuffers.FlatBufferBuilder
import java.nio.ByteBuffer

/** The buffer is not a valid envelope or voice message. */
class VoiceWireException(message: String, cause: Throwable? = null) : Exception(message, cause)

enum class WireOp(val value: UByte) { DATA(Op.Data), OPEN(Op.Open), CLOSE(Op.Close) }

enum class WireStatus(val value: UByte) {
    OK(Status.Ok),
    UNKNOWN_SERVICE(Status.UnknownService),
    UNSUPPORTED_VERSION(Status.UnsupportedVersion),
    MALFORMED(Status.Malformed),
    NOT_PERMITTED(Status.NotPermitted),
    UNKNOWN_SESSION(Status.UnknownSession),
}

enum class VerbosityLevel(val value: UByte) {
    QUIET(Verbosity.Quiet),
    NORMAL(Verbosity.Normal),
    CHATTY(Verbosity.Chatty),
}

/** What the console may send: the button commands and the settings (spec/interfaces/voice.md). */
sealed class ConsoleCommand {
    object Wake : ConsoleCommand()
    object GoNow : ConsoleCommand()
    object Cancel : ConsoleCommand()
    object Confirm : ConsoleCommand()
    object Deny : ConsoleCommand()
    object EndDictation : ConsoleCommand()
    data class SetVerbosity(val level: VerbosityLevel) : ConsoleCommand()

    /** An empty name asks for the next persona. */
    data class SwitchPersona(val persona: String = "") : ConsoleCommand()

    /** The language MIA speaks, such as `cs` or `en`. */
    data class SetLanguage(val language: String) : ConsoleCommand()
}

/** What the machine tells the console. Names are the snake_case strings the Pi code uses (`yellow_countdown`). */
sealed class ConsoleEvent {
    data class StateChanged(val previous: String, val current: String) : ConsoleEvent()

    /** [state] is a resting state or a transient cue name (`wake_caught`). */
    data class Feedback(val state: String, val led: String, val tone: String) : ConsoleEvent()

    data class Spoken(
        val phrase: String,
        val params: Map<String, String>,
        val priority: Int,
        val utteranceId: Long,
        /** The words in the persona and language in use; empty from a Pi that does not fill them. */
        val text: String = "",
    ) : ConsoleEvent()

    data class Transcript(val text: String, val utteranceId: Long) : ConsoleEvent()

    /** The settings the machine uses now, and the choices this Pi offers: after the session opens and after every change (ADR-0019). */
    data class Settings(
        val verbosity: VerbosityLevel,
        val persona: String = "",
        val personas: List<String> = emptyList(),
        val language: String = "",
        val languages: List<String> = emptyList(),
    ) : ConsoleEvent()
}

data class WireEnvelope(
    val service: Int,
    val sessionId: String,
    val op: WireOp,
    val status: WireStatus?,
    val seq: Long,
    val payload: ByteArray,
    val version: Int = VoiceWire.VERSION,
) {
    override fun equals(other: Any?): Boolean =
        other is WireEnvelope &&
            service == other.service && sessionId == other.sessionId && op == other.op &&
            status == other.status && seq == other.seq && version == other.version &&
            payload.contentEquals(other.payload)

    override fun hashCode(): Int = 31 * (31 * sessionId.hashCode() + seq.hashCode()) + payload.contentHashCode()
}

/**
 * The FlatBuffers envelope of `schemas/voice.fbs` (ADR-0013), on top of the generated `MiaVoice` bindings.
 * The Pi side is `services/voice_fsm/wire/codec.py`; both read the same fixtures in `tests/fixtures/voice`.
 */
object VoiceWire {
    const val VERSION = 1
    val SERVICE_VOICE: Int = ServiceType.Voice.toInt()

    fun encodeEnvelope(envelope: WireEnvelope): ByteArray {
        val b = FlatBufferBuilder(64 + envelope.payload.size)
        val session = if (envelope.sessionId.isEmpty()) 0 else b.createString(envelope.sessionId)
        val payload = if (envelope.payload.isEmpty()) 0 else b.createByteVector(envelope.payload)
        Envelope.startEnvelope(b)
        Envelope.addVersion(b, envelope.version.toUByte())
        Envelope.addService(b, envelope.service.toUByte())
        if (session != 0) Envelope.addSessionId(b, session)
        Envelope.addOp(b, envelope.op.value)
        Envelope.addStatus(b, (envelope.status ?: WireStatus.OK).value)
        Envelope.addSeq(b, envelope.seq.toUInt())
        if (payload != 0) Envelope.addPayload(b, payload)
        Envelope.finishEnvelopeBuffer(b, Envelope.endEnvelope(b))
        return b.sizedByteArray()
    }

    fun decodeEnvelope(data: ByteArray): WireEnvelope {
        try {
            val bb = ByteBuffer.wrap(data)
            if (data.size < 8 || !Envelope.EnvelopeBufferHasIdentifier(bb)) {
                throw VoiceWireException("not a MIAV envelope")
            }
            val e = Envelope.getRootAsEnvelope(bb)
            checkCount("payload", e.payloadLength, data.size)
            val payload = ByteArray(e.payloadLength) { i -> e.payload(i).toByte() }
            return WireEnvelope(
                service = e.service.toInt(),
                sessionId = e.sessionId ?: "",
                op = WireOp.values().firstOrNull { it.value == e.op }
                    ?: throw VoiceWireException("unknown op ${e.op}"),
                status = WireStatus.values().firstOrNull { it.value == e.status },
                seq = e.seq.toLong(),
                payload = payload,
                version = e.version.toInt(),
            )
        } catch (ex: VoiceWireException) {
            throw ex
        } catch (ex: RuntimeException) {
            throw VoiceWireException("malformed envelope: ${ex.message}", ex)
        }
    }

    fun encodeCommand(command: ConsoleCommand): ByteArray {
        val b = FlatBufferBuilder(64)
        val console = Source.Console
        val (type, body) = when (command) {
            is ConsoleCommand.Wake -> VoiceBody.Wake to Wake.createWake(b, console)
            is ConsoleCommand.GoNow -> VoiceBody.GoNow to GoNow.createGoNow(b, console)
            is ConsoleCommand.Cancel -> VoiceBody.Cancel to Cancel.createCancel(b, console)
            is ConsoleCommand.Confirm -> VoiceBody.Confirm to Confirm.createConfirm(b, console)
            is ConsoleCommand.Deny -> VoiceBody.Deny to Deny.createDeny(b, console)
            is ConsoleCommand.EndDictation -> VoiceBody.EndDictation to EndDictation.createEndDictation(b, console)
            is ConsoleCommand.SetVerbosity -> {
                // Field order matches services/voice_fsm/wire/codec.py so the bytes are identical.
                SetVerbosity.startSetVerbosity(b)
                SetVerbosity.addLevel(b, command.level.value)
                SetVerbosity.addSource(b, console)
                VoiceBody.SetVerbosity to SetVerbosity.endSetVerbosity(b)
            }
            is ConsoleCommand.SwitchPersona -> {
                val persona = if (command.persona.isEmpty()) 0 else b.createString(command.persona)
                SwitchPersona.startSwitchPersona(b)
                if (persona != 0) SwitchPersona.addPersona(b, persona)
                SwitchPersona.addSource(b, console)
                VoiceBody.SwitchPersona to SwitchPersona.endSwitchPersona(b)
            }
            is ConsoleCommand.SetLanguage -> {
                val language = if (command.language.isEmpty()) 0 else b.createString(command.language)
                SetLanguage.startSetLanguage(b)
                if (language != 0) SetLanguage.addLanguage(b, language)
                SetLanguage.addSource(b, console)
                VoiceBody.SetLanguage to SetLanguage.endSetLanguage(b)
            }
        }
        VoiceMessage.startVoiceMessage(b)
        VoiceMessage.addBodyType(b, type)
        VoiceMessage.addBody(b, body)
        b.finish(VoiceMessage.endVoiceMessage(b))
        return b.sizedByteArray()
    }

    fun decodeEvent(payload: ByteArray): ConsoleEvent {
        try {
            val message = VoiceMessage.getRootAsVoiceMessage(ByteBuffer.wrap(payload))
            return when (message.bodyType) {
                VoiceBody.StateChanged -> {
                    val t = StateChanged()
                    message.body(t) ?: throw VoiceWireException("voice message has no body")
                    ConsoleEvent.StateChanged(
                        snake(State.name(t.previous.toInt())),
                        snake(State.name(t.current.toInt())),
                    )
                }
                VoiceBody.FeedbackCue -> {
                    val t = FeedbackCue()
                    message.body(t) ?: throw VoiceWireException("voice message has no body")
                    val key = if (t.cue != CueName.NoCue) CueName.name(t.cue.toInt()) else State.name(t.state.toInt())
                    ConsoleEvent.Feedback(
                        snake(key),
                        snake(Led.name(t.led.toInt())),
                        if (t.tone == Tone.NoTone) "none" else snake(Tone.name(t.tone.toInt())),
                    )
                }
                VoiceBody.Spoken -> {
                    val t = Spoken()
                    message.body(t) ?: throw VoiceWireException("voice message has no body")
                    ConsoleEvent.Spoken(t.phrase ?: "", readArgs(t, payload.size), t.priority.toInt(), t.utteranceId.toLong(), t.text ?: "")
                }
                VoiceBody.Transcript -> {
                    val t = Transcript()
                    message.body(t) ?: throw VoiceWireException("voice message has no body")
                    ConsoleEvent.Transcript(t.text ?: "", t.utteranceId.toLong())
                }
                VoiceBody.Settings -> {
                    val t = Settings()
                    message.body(t) ?: throw VoiceWireException("voice message has no body")
                    checkCount("personas", t.personasLength, payload.size)
                    checkCount("languages", t.languagesLength, payload.size)
                    ConsoleEvent.Settings(
                        verbosity = VerbosityLevel.values().firstOrNull { it.value == t.verbosity }
                            ?: throw VoiceWireException("unknown verbosity ${t.verbosity}"),
                        persona = t.persona ?: "",
                        personas = (0 until t.personasLength).map { t.personas(it) ?: "" },
                        language = t.language ?: "",
                        languages = (0 until t.languagesLength).map { t.languages(it) ?: "" },
                    )
                }
                else -> throw VoiceWireException("voice message type ${message.bodyType} is not an event")
            }
        } catch (ex: VoiceWireException) {
            throw ex
        } catch (ex: RuntimeException) {
            throw VoiceWireException("malformed voice message: ${ex.message}", ex)
        }
    }

    /** Parameter values as display text; a list is joined with commas. */
    private fun readArgs(spoken: Spoken, bufferSize: Int): Map<String, String> {
        val out = linkedMapOf<String, String>()
        checkCount("params", spoken.paramsLength, bufferSize)
        for (i in 0 until spoken.paramsLength) {
            val arg: Arg = spoken.params(i) ?: continue
            val key = arg.key ?: ""
            out[key] = when (arg.kind) {
                ArgKind.Text -> arg.text ?: ""
                ArgKind.Int -> arg.intValue.toString()
                ArgKind.Real -> arg.realValue.toString()
                ArgKind.Flag -> (arg.intValue != 0L).toString()
                ArgKind.TextList -> {
                    checkCount("texts", arg.textsLength, bufferSize)
                    (0 until arg.textsLength).joinToString(", ") { arg.texts(it) ?: "" }
                }
                else -> throw VoiceWireException("argument $key has unknown kind ${arg.kind}")
            }
        }
        return out
    }

    /** A vector cannot hold more elements than the buffer has bytes; a damaged length must not drive an allocation. */
    private fun checkCount(what: String, count: Int, bufferSize: Int) {
        if (count < 0 || count > bufferSize) throw VoiceWireException("$what length $count does not fit a $bufferSize byte buffer")
    }

    /** `YellowCountdown` to `yellow_countdown`. */
    internal fun snake(name: String): String =
        name.replace(Regex("(?<!^)([A-Z])"), "_$1").lowercase()
}
