package cz.mia.app.core.audio

import com.google.gson.JsonObject
import com.google.gson.JsonParser

/** Where MIA's microphone comes from. The Pi decides which of these it can serve (ADR-0019, ADR-0021). */
enum class MicTransport(val wire: String, val label: String) {
    WIFI("wifi", "Wi-Fi"),
    BLUETOOTH("bluetooth", "Bluetooth"),
}

/** Where MIA's replies are heard. */
enum class ReplyOutput(val wire: String, val label: String) {
    PI_SPEAKER("pi_speaker", "Pi speaker"),
    BLUETOOTH_PHONE("bluetooth_phone", "Bluetooth to phone"),
    PHONE_SPEAKER("phone_speaker", "Phone speaker"),
}

/**
 * What the Pi reports for `GET /audio/settings`: the stored choice, what it really uses ([effectiveMic],
 * [effectiveReply]) and what it can do. The phone shows this and never what it last asked for.
 */
data class AudioSettingsReport(
    val micTransport: MicTransport,
    val replyOutput: ReplyOutput,
    val effectiveMic: MicTransport,
    val effectiveReply: ReplyOutput,
    val micAvailable: Map<MicTransport, Boolean>,
    val replyAvailable: Map<ReplyOutput, Boolean>,
    val btAudioAvailable: Boolean,
) {
    fun available(option: MicTransport): Boolean = micAvailable[option] ?: false
    fun available(option: ReplyOutput): Boolean = replyAvailable[option] ?: false
}

object AudioSettingsCodec {
    /** The report in [json], or null when it is not one this app understands. */
    fun parse(json: String): AudioSettingsReport? = try {
        val root = JsonParser.parseString(json).asJsonObject
        val caps = root.getAsJsonObject("capabilities")
        val micCaps = caps.getAsJsonObject("mic_transport")
        val replyCaps = caps.getAsJsonObject("reply_output")
        val effective = root.getAsJsonObject("effective")
        AudioSettingsReport(
            micTransport = mic(root, "mic_transport"),
            replyOutput = reply(root, "reply_output"),
            effectiveMic = mic(effective, "mic_transport"),
            effectiveReply = reply(effective, "reply_output"),
            micAvailable = MicTransport.values().associateWith { flag(micCaps, it.wire) },
            replyAvailable = ReplyOutput.values().associateWith { flag(replyCaps, it.wire) },
            btAudioAvailable = flag(caps, "bt_audio_available"),
        )
    } catch (e: Exception) {
        null
    }

    /** The body of `PUT /audio/settings`; a null field is left as it is. */
    fun updateBody(mic: MicTransport?, reply: ReplyOutput?): String {
        val body = JsonObject()
        if (mic != null) body.addProperty("mic_transport", mic.wire)
        if (reply != null) body.addProperty("reply_output", reply.wire)
        return body.toString()
    }

    private fun mic(obj: JsonObject, key: String): MicTransport =
        MicTransport.values().first { it.wire == obj.get(key).asString }

    private fun reply(obj: JsonObject, key: String): ReplyOutput =
        ReplyOutput.values().first { it.wire == obj.get(key).asString }

    private fun flag(obj: JsonObject, key: String): Boolean = obj.get(key)?.asBoolean ?: false
}

sealed class AudioSettingsResult {
    data class Ok(val report: AudioSettingsReport) : AudioSettingsResult()

    /** The Pi refused with 409: it cannot do that (Bluetooth audio, phone speaker). Nothing was stored. */
    object Unavailable : AudioSettingsResult()

    data class Failed(val message: String) : AudioSettingsResult()
}
