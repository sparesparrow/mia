package cz.mia.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import android.util.Log
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import cz.mia.app.core.background.RetentionWorker
import cz.mia.app.core.background.HealthPingWorker
import cz.mia.app.core.background.MetricsWorker
import dagger.hilt.android.HiltAndroidApp
import io.sentry.android.core.SentryAndroid
import javax.inject.Inject
import java.util.concurrent.TimeUnit

@HiltAndroidApp
class MIAApplication : Application(), Configuration.Provider {

	@Inject
	lateinit var workerFactory: HiltWorkerFactory

	override fun onCreate() {
		super.onCreate()
		Thread.setDefaultUncaughtExceptionHandler { t, e ->
			Log.e("MIA", "Uncaught exception in thread ${t.name}", e)
		}
		initSentry()
		createNotificationChannels()
		scheduleRetentionWorker()
		scheduleHealthPingWorker()
		scheduleMetricsWorker()
	}

	override fun onTerminate() {
		super.onTerminate()
		// Note: BLEManager cleanup is handled by its singleton lifecycle
		// Individual components should clean up their own resources
	}

	private fun initSentry() {
		val dsn = System.getenv("MIA_SENTRY_DSN")
		if (!dsn.isNullOrBlank()) {
			SentryAndroid.init(this) { options ->
				options.dsn = dsn
				options.isEnableAutoSessionTracking = true
				options.tracesSampleRate = 0.2
			}
		}
	}

	private fun createNotificationChannels() {
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
			val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

			// Driving Service Channel
			val drivingChannel = NotificationChannel(
				CHANNEL_DRIVING_SERVICE,
				"AI-SERVIS Driving Service",
				NotificationManager.IMPORTANCE_LOW
			).apply {
				description = "Foreground service for AI-SERVIS driving assistance"
				setShowBadge(false)
			}

			// Alerts Channel
			val alertsChannel = NotificationChannel(
				CHANNEL_ALERTS,
				"AI-SERVIS Alerts",
				NotificationManager.IMPORTANCE_HIGH
			).apply {
				description = "Vehicle alerts and notifications"
				enableVibration(true)
				enableLights(true)
			}

			// ANPR Channel
			val anprChannel = NotificationChannel(
				CHANNEL_ANPR,
				"AI-SERVIS ANPR",
				NotificationManager.IMPORTANCE_DEFAULT
			).apply {
				description = "License plate recognition notifications"
				setShowBadge(true)
			}

			notificationManager.createNotificationChannels(
				listOf(drivingChannel, alertsChannel, anprChannel)
			)
		}
	}

	private fun scheduleRetentionWorker() {
		val request = PeriodicWorkRequestBuilder<RetentionWorker>(1, TimeUnit.DAYS).build()
		WorkManager.getInstance(this).enqueueUniquePeriodicWork(
			"retention-worker",
			ExistingPeriodicWorkPolicy.UPDATE,
			request
		)
	}

	private fun scheduleHealthPingWorker() {
		val request = PeriodicWorkRequestBuilder<HealthPingWorker>(1, TimeUnit.HOURS).build()
		WorkManager.getInstance(this).enqueueUniquePeriodicWork(
			"health-ping-worker",
			ExistingPeriodicWorkPolicy.UPDATE,
			request
		)
	}

	private fun scheduleMetricsWorker() {
		val request = PeriodicWorkRequestBuilder<MetricsWorker>(1, TimeUnit.HOURS).build()
		WorkManager.getInstance(this).enqueueUniquePeriodicWork(
			"metrics-worker",
			ExistingPeriodicWorkPolicy.UPDATE,
			request
		)
	}

	override val workManagerConfiguration: Configuration
		get() = Configuration.Builder()
			.setWorkerFactory(workerFactory)
			.build()

	companion object {
		const val CHANNEL_DRIVING_SERVICE = "driving_service"
		const val CHANNEL_ALERTS = "alerts"
		const val CHANNEL_ANPR = "anpr"
	}
}

