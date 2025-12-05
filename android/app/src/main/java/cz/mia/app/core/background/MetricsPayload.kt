package cz.mia.app.core.background

import android.os.Build

data class MetricsPayload(
	val ts: Long = System.currentTimeMillis(),
	val appVersion: String = cz.mia.app.BuildConfig.VERSION_NAME,
	val sdkInt: Int = Build.VERSION.SDK_INT,
	val manufacturer: String = Build.MANUFACTURER,
	val model: String = Build.MODEL
)
