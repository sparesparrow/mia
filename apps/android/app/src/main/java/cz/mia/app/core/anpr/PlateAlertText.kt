package cz.mia.app.core.anpr

/**
 * The words for a [PlateAlert], in Czech or English, shown and spoken alike. The text names the user's label but
 * never the plate, and stays on the phone: plate alerts are not published over MQTT.
 *
 * The camera faces the road ahead, so a repeated plate is a car seen again, not necessarily one behind.
 */
object PlateAlertText {
	fun render(alert: PlateAlert, language: String): String = if (language == "cs") czech(alert) else english(alert)

	/** One notification per plate, so a second alert for the same car replaces the first. */
	fun notificationId(alert: PlateAlert): Int = 3000 + (alert.plateHash.hashCode() and 0x3FF)

	private fun czech(alert: PlateAlert): String = when (alert) {
		is PlateAlert.Listed ->
			if (alert.label.isBlank()) "Auto z černé knihy." else "Auto z černé knihy: ${alert.label.trim()}."
		is PlateAlert.Repeated -> "Stejné auto vidím už ${alert.episodes}krát za ${czechSpan(alert.spanMs)}."
	}

	private fun english(alert: PlateAlert): String = when (alert) {
		is PlateAlert.Listed ->
			if (alert.label.isBlank()) "Black-book car." else "Black-book car: ${alert.label.trim()}."
		is PlateAlert.Repeated -> "Same car seen ${alert.episodes} times in ${englishSpan(alert.spanMs)}."
	}

	private fun czechSpan(ms: Long): String {
		val minutes = ms / 60_000
		if (minutes < 120) return "$minutes minut"
		val hours = minutes / 60
		return if (hours in 2..4) "$hours hodiny" else "$hours hodin"
	}

	private fun englishSpan(ms: Long): String {
		val minutes = ms / 60_000
		return if (minutes < 120) "$minutes minutes" else "${minutes / 60} hours"
	}
}
