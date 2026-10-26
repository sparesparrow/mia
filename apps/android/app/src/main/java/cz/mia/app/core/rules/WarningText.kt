package cz.mia.app.core.rules

import java.util.Locale

/** A warning as shown in the notification ([display]) and as spoken ([spoken]). */
data class WarningMessage(val display: String, val spoken: String)

/**
 * The wording of car warnings. Every warning names the reading with its value and unit in the first sentence and
 * gives a recommendation in the second, so the content comes first whatever voice reads it (ADR-0015).
 * Czech for a Czech voice, English otherwise.
 */
object WarningText {
	fun render(condition: CarCondition, value: Double, language: String): WarningMessage =
		if (language == "cs") czech(condition, value) else english(condition, value)

	private fun czech(condition: CarCondition, value: Double): WarningMessage {
		val whole = value.toInt()
		val volts = String.format(Locale("cs", "CZ"), "%.1f", value)
		return when (condition) {
			CarCondition.ENGINE_OVERHEAT -> WarningMessage(
				display = "Chladicí kapalina $whole °C. Zastavte, až to bude bezpečné, a vypněte motor.",
				spoken = "Teplota motoru $whole stupňů. Zastavte, až to bude bezpečné, a vypněte motor.",
			)
			CarCondition.BATTERY_LOW -> WarningMessage(
				display = "Baterie $volts V. Nechte zkontrolovat baterii a dobíjení.",
				spoken = "Napětí baterie $volts voltu. Nechte zkontrolovat baterii a dobíjení.",
			)
			CarCondition.BATTERY_HIGH -> WarningMessage(
				display = "Baterie $volts V, nad normou. Nechte zkontrolovat regulátor dobíjení.",
				spoken = "Napětí baterie $volts voltu, nad normou. Nechte zkontrolovat regulátor dobíjení.",
			)
			CarCondition.RPM_HIGH -> WarningMessage(
				display = "Otáčky $whole/min. Uberte plyn.",
				spoken = "Otáčky $whole za minutu. Uberte plyn.",
			)
			CarCondition.FUEL_LOW -> WarningMessage(
				display = "Palivo $whole %. Natankujte při nejbližší příležitosti.",
				spoken = "Palivo $whole procent. Natankujte při nejbližší příležitosti.",
			)
		}
	}

	private fun english(condition: CarCondition, value: Double): WarningMessage {
		val whole = value.toInt()
		val volts = String.format(Locale.US, "%.1f", value)
		return when (condition) {
			CarCondition.ENGINE_OVERHEAT -> WarningMessage(
				display = "Coolant $whole °C. Stop when it is safe and switch the engine off.",
				spoken = "Coolant at $whole degrees. Stop when it is safe and switch the engine off.",
			)
			CarCondition.BATTERY_LOW -> WarningMessage(
				display = "Battery $volts V. Have the battery and charging checked.",
				spoken = "Battery at $volts volts. Have the battery and charging checked.",
			)
			CarCondition.BATTERY_HIGH -> WarningMessage(
				display = "Battery $volts V, above normal. Have the charging regulator checked.",
				spoken = "Battery at $volts volts, above normal. Have the charging regulator checked.",
			)
			CarCondition.RPM_HIGH -> WarningMessage(
				display = "Engine speed $whole rpm. Ease off the throttle.",
				spoken = "Engine speed $whole RPM. Ease off the throttle.",
			)
			CarCondition.FUEL_LOW -> WarningMessage(
				display = "Fuel $whole %. Refuel at the next opportunity.",
				spoken = "Fuel at $whole percent. Refuel at the next opportunity.",
			)
		}
	}
}
