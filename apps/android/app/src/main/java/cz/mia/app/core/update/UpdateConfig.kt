package cz.mia.app.core.update

/**
 * The settings the user edits on the Software update screen. Mirrors schemas/json/mia-user-config.schema.json;
 * the Pi validates the same document again. [toYaml] writes the strict subset bin/mia-apply-update parses:
 * `key: value` lines, one level of sections, strings always in double quotes with JSON escapes.
 */
data class UpdateConfig(
	val deviceName: String? = null,
	val logLevel: String? = null,
	val logRetentionDays: Int? = null,
	val telemetryIntervalMs: Int? = null,
	val telemetryEnabled: Boolean? = null,
) {
	/** What is wrong with this config, in the schema's terms; empty when it is valid. */
	fun problems(): List<String> = buildList {
		deviceName?.let {
			if (it.length !in 1..32 || !NAME.matches(it)) add("Device name: 1-32 letters, digits, space . _ -, starting with a letter or digit")
		}
		logLevel?.let { if (it !in LEVELS) add("Log level must be one of $LEVELS") }
		logRetentionDays?.let { if (it !in 1..90) add("Log retention must be 1-90 days") }
		telemetryIntervalMs?.let { if (it !in 100..60000) add("Telemetry interval must be 100-60000 ms") }
	}

	fun toYaml(): String {
		val problems = problems()
		require(problems.isEmpty()) { problems.joinToString("; ") }
		val out = StringBuilder("version: 1\n")
		deviceName?.let { out.append("device_name: ").append(quote(it)).append('\n') }
		if (logLevel != null || logRetentionDays != null) {
			out.append("logging:\n")
			logLevel?.let { out.append("  level: ").append(quote(it)).append('\n') }
			logRetentionDays?.let { out.append("  retention_days: ").append(it).append('\n') }
		}
		if (telemetryIntervalMs != null || telemetryEnabled != null) {
			out.append("telemetry:\n")
			telemetryIntervalMs?.let { out.append("  interval_ms: ").append(it).append('\n') }
			telemetryEnabled?.let { out.append("  enabled: ").append(it).append('\n') }
		}
		return out.toString()
	}

	companion object {
		val LEVELS = listOf("error", "warning", "info", "debug")
		private val NAME = Regex("^[A-Za-z0-9][A-Za-z0-9 ._-]*$")

		/** A JSON string literal: the one quoting the Pi's parser accepts. */
		fun quote(value: String): String {
			val out = StringBuilder("\"")
			for (c in value) {
				when {
					c == '"' -> out.append("\\\"")
					c == '\\' -> out.append("\\\\")
					c == '\n' -> out.append("\\n")
					c == '\r' -> out.append("\\r")
					c == '\t' -> out.append("\\t")
					c < ' ' -> out.append("\\u%04x".format(c.code))
					else -> out.append(c)
				}
			}
			return out.append('"').toString()
		}
	}
}
