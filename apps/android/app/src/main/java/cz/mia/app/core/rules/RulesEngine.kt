package cz.mia.app.core.rules

import cz.mia.app.core.background.OBDData
import cz.mia.app.core.background.VehicleAlert
import cz.mia.app.core.background.AlertSeverity
import javax.inject.Inject
import javax.inject.Singleton

interface RulesEngine {
	fun evaluate(obdData: OBDData): List<VehicleAlert>
}

@Singleton
class RulesEngineImpl @Inject constructor() : RulesEngine {
	private val fuelWarnThreshold: Int = 20
	private val tempAlertThreshold: Int = 105

	override fun evaluate(obdData: OBDData): List<VehicleAlert> {
		val alerts = mutableListOf<VehicleAlert>()

		if (obdData.fuelLevel < fuelWarnThreshold) {
			alerts.add(
				VehicleAlert(
					severity = AlertSeverity.WARNING,
					code = "FUEL_LOW",
					message = "Palivo dochází. Nejbližší čerpačka v dosahu."
				)
			)
		}

		if (obdData.coolantTemp > tempAlertThreshold) {
			alerts.add(
				VehicleAlert(
					severity = AlertSeverity.CRITICAL,
					code = "ENGINE_OVERHEAT",
					message = "POZOR! Motor přehřívá. Zastavte bezpečně."
				)
			)
		}

		return alerts
	}
}
