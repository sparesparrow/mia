package cz.mia.app.core.voice

// @req REQ-AND-019

import cz.mia.app.core.background.AlertSeverity
import cz.mia.app.core.background.VehicleAlert
import cz.mia.app.core.rules.CarWarningCodes
import cz.mia.app.core.rules.CarWarningTexts
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SpokenCarWarningsTest {
	private val warnings = SpokenCarWarnings()

	@Test
	fun overheat_speaksOnceUntilRepeatInterval() {
		val first = warnings.cycle1(coolantC = 110.0, batteryV = 12.6, nowMs = 0L)
		assertEquals(listOf(CarWarningCodes.ENGINE_OVERHEAT), first.map { it.code })
		assertTrue(first.single().interrupt)
		assertEquals(CarWarningTexts.ENGINE_OVERHEAT, first.single().text)

		assertTrue(warnings.cycle1(110.0, 12.6, 1_000L).isEmpty())
		assertEquals(
			listOf(CarWarningCodes.ENGINE_OVERHEAT),
			warnings.cycle1(110.0, 12.6, 60_000L).map { it.code },
		)
	}

	@Test
	fun clearedOverheat_speaksAgainImmediately() {
		warnings.cycle1(110.0, 12.6, 0L)
		warnings.cycle1(90.0, 12.6, 1_000L)
		assertEquals(
			listOf(CarWarningCodes.ENGINE_OVERHEAT),
			warnings.cycle1(110.0, 12.6, 2_000L).map { it.code },
		)
	}

	@Test
	fun missingSignal_doesNotSpeakOrClear() {
		warnings.cycle1(110.0, 12.6, 0L)
		assertTrue(warnings.cycle1(coolantC = null, batteryV = null, nowMs = 1_000L).isEmpty())
		assertTrue(warnings.cycle1(110.0, 12.6, 2_000L).isEmpty())
	}

	@Test
	fuelWarning_isGatedUntilItClears() {
		val fuel = VehicleAlert(
			severity = AlertSeverity.WARNING,
			code = CarWarningCodes.FUEL_LOW,
			message = CarWarningTexts.FUEL_LOW,
			timestamp = 0L,
		)
		assertEquals(listOf(CarWarningCodes.FUEL_LOW), warnings.gate(listOf(fuel), 0L).map { it.code })
		assertTrue(warnings.gate(listOf(fuel), 1_000L).isEmpty())
		assertTrue(warnings.gate(emptyList(), 2_000L).isEmpty())
		assertEquals(listOf(CarWarningCodes.FUEL_LOW), warnings.gate(listOf(fuel), 3_000L).map { it.code })
	}

	@Test
	fun battery_usesExistingLowThreshold() {
		assertTrue(warnings.cycle1(coolantC = 90.0, batteryV = 11.5, nowMs = 0L).isEmpty())
		val low = warnings.cycle1(90.0, 11.49, 0L)
		assertEquals(listOf(CarWarningCodes.BATTERY_LOW), low.map { it.code })
		assertEquals(false, low.single().interrupt)
	}

	@Test
	fun coolantAtThreshold_doesNotSpeak() {
		assertTrue(warnings.cycle1(coolantC = 105.0, batteryV = 12.4, nowMs = 0L).isEmpty())
	}
}
