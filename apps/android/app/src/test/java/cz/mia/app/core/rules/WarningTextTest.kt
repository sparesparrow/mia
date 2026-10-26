package cz.mia.app.core.rules

// @req REQ-AND-019

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WarningTextTest {
	private val samples = mapOf(
		CarCondition.ENGINE_OVERHEAT to 112.0,
		CarCondition.BATTERY_LOW to 11.4,
		CarCondition.BATTERY_HIGH to 15.1,
		CarCondition.RPM_HIGH to 6200.0,
		CarCondition.FUEL_LOW to 12.0,
	)

	private val units = mapOf(
		"cs" to mapOf(
			CarCondition.ENGINE_OVERHEAT to Pair("°C", "stupňů"),
			CarCondition.BATTERY_LOW to Pair("V", "voltu"),
			CarCondition.BATTERY_HIGH to Pair("V", "voltu"),
			CarCondition.RPM_HIGH to Pair("/min", "za minutu"),
			CarCondition.FUEL_LOW to Pair("%", "procent"),
		),
		"en" to mapOf(
			CarCondition.ENGINE_OVERHEAT to Pair("°C", "degrees"),
			CarCondition.BATTERY_LOW to Pair("V", "volts"),
			CarCondition.BATTERY_HIGH to Pair("V", "volts"),
			CarCondition.RPM_HIGH to Pair("rpm", "RPM"),
			CarCondition.FUEL_LOW to Pair("%", "percent"),
		),
	)

	private fun sentences(text: String) = text.split(Regex("(?<=\\.) ")).filter { it.isNotBlank() }

	@Test
	fun `every warning gives value and unit in its first sentence and a recommendation after it`() {
		for (language in listOf("cs", "en")) {
			for ((condition, value) in samples) {
				val message = WarningText.render(condition, value, language)
				val (displayUnit, spokenUnit) = units.getValue(language).getValue(condition)
				val number = if (condition == CarCondition.BATTERY_LOW || condition == CarCondition.BATTERY_HIGH) {
					if (language == "cs") value.toString().replace('.', ',') else value.toString()
				} else {
					value.toInt().toString()
				}
				for ((text, unit) in listOf(message.display to displayUnit, message.spoken to spokenUnit)) {
					val parts = sentences(text)
					assertTrue("$language $condition: $text", parts.size >= 2)
					assertTrue("$language $condition value: $text", parts[0].contains(number))
					assertTrue("$language $condition unit: $text", parts[0].contains(unit))
				}
			}
		}
	}

	@Test
	fun `Czech volts use a decimal comma`() {
		assertEquals("Napětí baterie 11,4 voltu. Nechte zkontrolovat baterii a dobíjení.",
			WarningText.render(CarCondition.BATTERY_LOW, 11.4, "cs").spoken)
	}

	@Test
	fun `any language other than Czech gets English`() {
		assertEquals(WarningText.render(CarCondition.FUEL_LOW, 12.0, "en"), WarningText.render(CarCondition.FUEL_LOW, 12.0, "de"))
	}
}
