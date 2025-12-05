package cz.mia.app.core.background

object MQTTTopics {
	fun telemetry(vin: String): String = "vehicle/telemetry/$vin/obd"
	fun alerts(vin: String): String = "vehicle/alerts/$vin"
	fun anpr(vin: String): String = "vehicle/events/$vin/anpr"
	fun health(vin: String): String = "device/health/$vin"
	fun metrics(vin: String): String = "device/metrics/$vin"
}
