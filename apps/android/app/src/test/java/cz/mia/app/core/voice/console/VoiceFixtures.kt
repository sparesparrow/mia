package cz.mia.app.core.voice.console

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.io.File

/** One case of `tests/fixtures/voice/envelopes.json`, written by the Pi's codec (tools/schemas/gen_voice_fixtures.py). */
class VoiceFixture(private val json: JsonObject) {
    val name: String get() = json["name"].asString
    val type: String get() = json["type"].asString
    val session: String get() = json["session"].asString
    val seq: Long get() = json["seq"].asLong
    val bytes: ByteArray get() = json["hex"].asString.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    val command: String get() = json["command"].asString
    val status: String get() = json["status"].asString
    val event: JsonObject get() = json["event"].asJsonObject
}

object VoiceFixtures {
    /** Tests run in `apps/android/app`; the fixture is found by walking up to the repository root. */
    fun load(): List<VoiceFixture> {
        var dir: File? = File(System.getProperty("user.dir")).absoluteFile
        while (dir != null) {
            val file = File(dir, "tests/fixtures/voice/envelopes.json")
            if (file.isFile) {
                val cases = JsonParser.parseString(file.readText()).asJsonObject["cases"].asJsonArray
                return cases.map { VoiceFixture(it.asJsonObject) }
            }
            dir = dir.parentFile
        }
        error("tests/fixtures/voice/envelopes.json not found above ${System.getProperty("user.dir")}")
    }
}
