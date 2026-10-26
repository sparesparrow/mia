package cz.mia.app.core.rules

// @req REQ-AND-010 REQ-AND-019

import com.google.gson.JsonElement
import com.google.gson.JsonPrimitive
import cz.mia.app.core.background.OBDData
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.dto.Cycle1TelemetrySignal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

internal fun envelope(
	coolant: Double = 90.0,
	voltage: Double = 13.8,
	rpm: Double = 1750.0,
	ignition: Boolean = true,
	confidence: Double = 0.9,
	coolantConfidence: Double = confidence,
	timestamp: String = "2026-10-25T10:00:00Z",
): Cycle1TelemetryEnvelope {
	fun signal(value: JsonElement, unit: String, conf: Double = confidence) =
		Cycle1TelemetrySignal(value, unit, "esp32", conf)
	return Cycle1TelemetryEnvelope(
		schemaVersion = 1,
		messageType = "vehicle.telemetry",
		deviceId = "esp32-test",
		timestamp = timestamp,
		source = "esp32",
		confidence = confidence,
		signals = mapOf(
			"ignition" to signal(JsonPrimitive(ignition), "bool"),
			"battery_voltage" to signal(JsonPrimitive(voltage), "V"),
			"engine_rpm" to signal(JsonPrimitive(rpm), "rpm"),
			"coolant_temp_c" to signal(JsonPrimitive(coolant), "C", coolantConfidence),
		),
	)
}

private fun List<ConditionReading>.level(condition: CarCondition) = single { it.condition == condition }.level

class CarRulesTest {
	@Test
	fun `coolant above 105 C triggers, between 100 and 105 holds, at or below 100 clears`() {
		assertEquals(ReadingLevel.TRIGGERED, CarRules.fromCycle1(envelope(coolant = 110.0), stale = false).level(CarCondition.ENGINE_OVERHEAT))
		assertEquals(ReadingLevel.BAND, CarRules.fromCycle1(envelope(coolant = 102.0), stale = false).level(CarCondition.ENGINE_OVERHEAT))
		assertEquals(ReadingLevel.CLEAR, CarRules.fromCycle1(envelope(coolant = 100.0), stale = false).level(CarCondition.ENGINE_OVERHEAT))
	}

	@Test
	fun `battery below 11_5 V is low and above 14_8 V is high`() {
		val low = CarRules.fromCycle1(envelope(voltage = 11.2), stale = false)
		assertEquals(ReadingLevel.TRIGGERED, low.level(CarCondition.BATTERY_LOW))
		assertEquals(ReadingLevel.CLEAR, low.level(CarCondition.BATTERY_HIGH))
		val high = CarRules.fromCycle1(envelope(voltage = 15.0), stale = false)
		assertEquals(ReadingLevel.TRIGGERED, high.level(CarCondition.BATTERY_HIGH))
		assertEquals(ReadingLevel.CLEAR, high.level(CarCondition.BATTERY_LOW))
	}

	@Test
	fun `rpm above 6000 triggers`() {
		assertEquals(ReadingLevel.TRIGGERED, CarRules.fromCycle1(envelope(rpm = 6500.0), stale = false).level(CarCondition.RPM_HIGH))
		assertEquals(ReadingLevel.CLEAR, CarRules.fromCycle1(envelope(rpm = 3000.0), stale = false).level(CarCondition.RPM_HIGH))
	}

	@Test
	fun `the replay vector gives no warning`() {
		val readings = CarRules.fromCycle1(envelope(coolant = 86.0, voltage = 13.8, rpm = 1750.0, confidence = 1.0), stale = false)
		assertTrue(readings.none { it.level == ReadingLevel.TRIGGERED })
	}

	@Test
	fun `a missing, stale or ignition-off envelope is unknown`() {
		for (readings in listOf(
			CarRules.fromCycle1(null, stale = false),
			CarRules.fromCycle1(envelope(coolant = 120.0), stale = true),
			CarRules.fromCycle1(envelope(coolant = 120.0, ignition = false), stale = false),
		)) {
			assertEquals(4, readings.size)
			assertTrue(readings.all { it.level == ReadingLevel.UNKNOWN && it.value == null })
		}
	}

	@Test
	fun `a value below the confidence floor is unknown, the simulation's 0_5 included`() {
		val simulated = CarRules.fromCycle1(envelope(coolant = 120.0, confidence = 0.5), stale = false)
		assertTrue(simulated.all { it.level == ReadingLevel.UNKNOWN })

		val oneSignal = CarRules.fromCycle1(envelope(coolant = 120.0, voltage = 11.0, coolantConfidence = 0.5), stale = false)
		assertEquals(ReadingLevel.UNKNOWN, oneSignal.level(CarCondition.ENGINE_OVERHEAT))
		assertEquals(ReadingLevel.TRIGGERED, oneSignal.level(CarCondition.BATTERY_LOW))
	}

	@Test
	fun `BLE OBD readings cover fuel, coolant and rpm, and a fuel level of 0 is not reported`() {
		val obd = OBDData(fuelLevel = 10, engineRpm = 6200, vehicleSpeed = 80, coolantTemp = 110, engineLoad = 40, dtcCodes = emptyList())
		val readings = CarRules.fromObd(obd)
		assertEquals(ReadingLevel.TRIGGERED, readings.level(CarCondition.FUEL_LOW))
		assertEquals(ReadingLevel.TRIGGERED, readings.level(CarCondition.ENGINE_OVERHEAT))
		assertEquals(ReadingLevel.TRIGGERED, readings.level(CarCondition.RPM_HIGH))

		val unanswered = CarRules.fromObd(obd.copy(fuelLevel = 0))
		assertEquals(ReadingLevel.UNKNOWN, unanswered.level(CarCondition.FUEL_LOW))
	}
}
