package cz.mia.app.core.audio

// @req REQ-AND-028

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AudioSettingsCodecTest {
    private val pi = """
        {"mic_transport":"wifi","reply_output":"pi_speaker",
         "effective":{"mic_transport":"wifi","reply_output":"pi_speaker"},
         "capabilities":{"bt_audio_available":false,
           "mic_transport":{"wifi":true,"bluetooth":false},
           "reply_output":{"pi_speaker":true,"bluetooth_phone":false,"phone_speaker":false}}}
    """.trimIndent()

    @Test
    fun `it reads the Pi's report, including what the Pi cannot do`() {
        val report = AudioSettingsCodec.parse(pi)!!
        assertEquals(MicTransport.WIFI, report.micTransport)
        assertEquals(ReplyOutput.PI_SPEAKER, report.effectiveReply)
        assertTrue(report.available(MicTransport.WIFI))
        assertFalse(report.available(MicTransport.BLUETOOTH))
        assertTrue(report.available(ReplyOutput.PI_SPEAKER))
        assertFalse(report.available(ReplyOutput.BLUETOOTH_PHONE))
        assertFalse(report.available(ReplyOutput.PHONE_SPEAKER))
        assertFalse(report.btAudioAvailable)
    }

    @Test
    fun `a report that is not understood is null, never a guess`() {
        assertNull(AudioSettingsCodec.parse("not json"))
        assertNull(AudioSettingsCodec.parse("""{"mic_transport":"wifi"}"""))
        val bad = pi.replace("\"reply_output\":\"pi_speaker\",", "\"reply_output\":\"loudspeaker\",")
        assertNull(AudioSettingsCodec.parse(bad))
    }

    @Test
    fun `an update names only the field being changed`() {
        assertEquals("""{"mic_transport":"bluetooth"}""", AudioSettingsCodec.updateBody(MicTransport.BLUETOOTH, null))
        assertEquals("""{"reply_output":"phone_speaker"}""", AudioSettingsCodec.updateBody(null, ReplyOutput.PHONE_SPEAKER))
    }
}
