package cz.mia.app.core.update

import com.google.gson.JsonParser

/** The Pi's answer: the last JSON line mia-apply-update prints. */
data class UpdateResult(val ok: Boolean, val step: String, val version: String?, val error: String?) {
	companion object {
		fun parse(stdout: String, exitStatus: Int?): UpdateResult {
			val line = stdout.lineSequence().map { it.trim() }.lastOrNull { it.startsWith("{") }
				?: return UpdateResult(false, "no_result", null, "The Pi sent no result (exit status ${exitStatus ?: "unknown"})")
			return try {
				val json = JsonParser.parseString(line).asJsonObject
				UpdateResult(
					ok = json.get("ok").asBoolean && (exitStatus == null || exitStatus == 0),
					step = json.get("step").asString,
					version = json.get("version")?.takeUnless { it.isJsonNull }?.asString,
					error = json.get("error")?.takeUnless { it.isJsonNull }?.asString,
				)
			} catch (e: RuntimeException) {
				UpdateResult(false, "bad_result", null, "The Pi's result could not be read")
			}
		}
	}
}
