package cz.mia.app.core.rules

import cz.mia.app.core.background.AlertSeverity
import cz.mia.app.core.background.OBDData
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RulesEngineTest {
	private val engine = RulesEngineImpl()

	@Test
	fun fuelLow_emitsWarning() {
		val data = OBDData(
			fuelLevel = 10,
			engineRpm = 1500,
			vehicleSpeed = 50,
			coolantTemp = 90,
			engineLoad = 30,
			dtcCodes = emptyList()
		)
		val alerts = engine.evaluate(data)
		assertTrue(alerts.any { it.code == "FUEL_LOW" && it.severity == AlertSeverity.WARNING })
	}

	@Test
	fun engineOverheat_emitsCritical() {
		val data = OBDData(
			fuelLevel = 50,
			engineRpm = 2000,
			vehicleSpeed = 60,
			coolantTemp = 110,
			engineLoad = 40,
			dtcCodes = emptyList()
		)
		val alerts = engine.evaluate(data)
		assertTrue(alerts.any { it.code == "ENGINE_OVERHEAT" && it.severity == AlertSeverity.CRITICAL })
	}

	@Test
	fun nominal_noAlerts() {
		val data = OBDData(
			fuelLevel = 60,
			engineRpm = 1800,
			vehicleSpeed = 70,
			coolantTemp = 90,
			engineLoad = 30,
			dtcCodes = emptyList()
		)
		val alerts = engine.evaluate(data)
		assertEquals(0, alerts.size)
	}
}
