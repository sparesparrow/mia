package cz.mia.app.core.background

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import cz.mia.app.core.storage.PreferencesRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first

@HiltWorker
class HealthPingWorker @AssistedInject constructor(
	@Assisted appContext: Context,
	@Assisted workerParams: WorkerParameters,
	private val prefs: PreferencesRepository,
	private val mqtt: MQTTManager
) : CoroutineWorker(appContext, workerParams) {
	override suspend fun doWork(): Result {
		val enabled = prefs.metricsOptIn().first()
		if (!enabled) return Result.success()

		val ping = HealthPing()
		mqtt.publishHealth(ping)
		prefs.setLastHealthPingTs(ping.ts)
		return Result.success()
	}
}
