package cz.mia.app.core.rules

import cz.mia.app.core.background.AlertSeverity

/**
 * A car condition worth a spoken warning, with its limits.
 *
 * A reading past [fireAt] that lasts [dwellMs] raises the warning once; it clears only when the value is back past
 * [clearAt], so a value hovering at the limit does not repeat it. The limits come from values already in the repo:
 * coolant 105 °C and fuel 20 % (the old RulesEngine, `schemas/json/config.schema.json` `temp_high` and `fuel_low`),
 * battery 11.5 / 14.8 V (`infra/monitoring/rules/automotive-alerts.yml`, BatteryVoltageAbnormal) and 6000 rpm
 * (`config.schema.json` `rpm_max`). None has been checked on the A4 8H yet (REQ-AND-019 not_proven).
 */
enum class CarCondition(
	val code: String,
	val severity: AlertSeverity,
	val above: Boolean,
	val fireAt: Double,
	val clearAt: Double,
	val dwellMs: Long,
) {
	ENGINE_OVERHEAT("ENGINE_OVERHEAT", AlertSeverity.CRITICAL, above = true, fireAt = 105.0, clearAt = 100.0, dwellMs = 10_000),
	BATTERY_LOW("BATTERY_LOW", AlertSeverity.WARNING, above = false, fireAt = 11.5, clearAt = 11.8, dwellMs = 60_000),
	BATTERY_HIGH("BATTERY_HIGH", AlertSeverity.WARNING, above = true, fireAt = 14.8, clearAt = 14.5, dwellMs = 60_000),
	RPM_HIGH("RPM_HIGH", AlertSeverity.WARNING, above = true, fireAt = 6000.0, clearAt = 5700.0, dwellMs = 3_000),
	FUEL_LOW("FUEL_LOW", AlertSeverity.WARNING, above = false, fireAt = 20.0, clearAt = 25.0, dwellMs = 30_000);

	/** Where [value] stands against this condition's limits. */
	fun level(value: Double): ReadingLevel {
		val past = if (above) value > fireAt else value < fireAt
		val back = if (above) value <= clearAt else value >= clearAt
		return when {
			past -> ReadingLevel.TRIGGERED
			back -> ReadingLevel.CLEAR
			else -> ReadingLevel.BAND
		}
	}
}

enum class ReadingLevel {
	/** Past the limit. */
	TRIGGERED,

	/** Between the limit and the clear value: keeps whatever state the condition is in. */
	BAND,

	/** Back past the clear value. */
	CLEAR,

	/** No usable value: no data, a stale or low-confidence envelope, or ignition off. */
	UNKNOWN,
}

/** One condition's reading at one moment. [value] is null when [level] is [ReadingLevel.UNKNOWN]. */
data class ConditionReading(
	val condition: CarCondition,
	val level: ReadingLevel,
	val value: Double?,
) {
	companion object {
		fun of(condition: CarCondition, value: Double?): ConditionReading =
			if (value == null) unknown(condition) else ConditionReading(condition, condition.level(value), value)

		fun unknown(condition: CarCondition) = ConditionReading(condition, ReadingLevel.UNKNOWN, null)
	}
}
