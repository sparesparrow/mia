package cz.mia.app.core.background

data class HealthPing(
	val ts: Long = System.currentTimeMillis(),
	val appVersion: String = cz.mia.app.BuildConfig.VERSION_NAME,
	val status: String = "ok"
)
