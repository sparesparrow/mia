package cz.mia.app.core.rules

import cz.mia.app.core.background.OBDData
import cz.mia.app.core.background.VehicleAlert
import javax.inject.Inject
import javax.inject.Singleton

interface RulesEngine {
	/** The alerts whose limits [obdData] is past right now, without dwell or repeat suppression. */
	fun evaluate(obdData: OBDData): List<VehicleAlert>
}

/** Point-in-time view of [CarRules]; the driving service warns through [CarWarningAnnouncer] instead. */
@Singleton
class RulesEngineImpl @Inject constructor() : RulesEngine {
	override fun evaluate(obdData: OBDData): List<VehicleAlert> =
		CarRules.fromObd(obdData)
			.filter { it.level == ReadingLevel.TRIGGERED }
			.map { reading ->
				val condition = reading.condition
				val text = WarningText.render(condition, reading.value ?: 0.0, language = "cs")
				VehicleAlert(severity = condition.severity, code = condition.code, message = text.display)
			}
}
