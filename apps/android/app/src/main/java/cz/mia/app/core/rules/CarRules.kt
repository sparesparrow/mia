package cz.mia.app.core.rules

import cz.mia.app.core.background.OBDData
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.dto.Cycle1TelemetrySignals

/**
 * Turns telemetry into [ConditionReading]s. Pure, so the limits are tested without a phone, a Pi or a car.
 */
object CarRules {
	/** Below this, a Cycle 1 value is not trusted for a warning. The Pi's simulation reports 0.5, real sources 0.9. */
	const val MIN_CONFIDENCE = 0.8

	private val CYCLE1_CONDITIONS = listOf(
		CarCondition.ENGINE_OVERHEAT,
		CarCondition.BATTERY_LOW,
		CarCondition.BATTERY_HIGH,
		CarCondition.RPM_HIGH,
	)

	/**
	 * Readings from the Pi's Cycle 1 envelope. Everything is unknown when there is no envelope, when it is stale,
	 * when the ignition is not reported on, or when a value's confidence (the lower of the envelope's and the
	 * signal's) is below [minConfidence].
	 */
	fun fromCycle1(
		envelope: Cycle1TelemetryEnvelope?,
		stale: Boolean,
		minConfidence: Double = MIN_CONFIDENCE,
	): List<ConditionReading> {
		if (envelope == null || stale || envelope.boolean(Cycle1TelemetrySignals.IGNITION) != true) {
			return CYCLE1_CONDITIONS.map { ConditionReading.unknown(it) }
		}
		fun trusted(name: String): Double? {
			val signal = envelope.signals[name] ?: return null
			if (minOf(envelope.confidence, signal.confidence) < minConfidence) return null
			return envelope.number(name)
		}
		val coolant = trusted(Cycle1TelemetrySignals.COOLANT_TEMP_C)
		val voltage = trusted(Cycle1TelemetrySignals.BATTERY_VOLTAGE)
		val rpm = trusted(Cycle1TelemetrySignals.ENGINE_RPM)
		return listOf(
			ConditionReading.of(CarCondition.ENGINE_OVERHEAT, coolant),
			ConditionReading.of(CarCondition.BATTERY_LOW, voltage),
			ConditionReading.of(CarCondition.BATTERY_HIGH, voltage),
			ConditionReading.of(CarCondition.RPM_HIGH, rpm),
		)
	}

	/**
	 * Readings from the phone's own BLE OBD adapter. A fuel level of 0 is treated as not reported: the manager
	 * starts at 0 and stays there when the adapter does not answer the fuel PID.
	 */
	fun fromObd(data: OBDData): List<ConditionReading> = listOf(
		ConditionReading.of(CarCondition.FUEL_LOW, data.fuelLevel.takeIf { it > 0 }?.toDouble()),
		ConditionReading.of(CarCondition.ENGINE_OVERHEAT, data.coolantTemp.toDouble()),
		ConditionReading.of(CarCondition.RPM_HIGH, data.engineRpm.toDouble()),
	)
}
