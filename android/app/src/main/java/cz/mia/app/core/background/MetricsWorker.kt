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
class MetricsWorker @AssistedInject constructor(
	@Assisted appContext: Context,
	@Assisted workerParams: WorkerParameters,
	private val prefs: PreferencesRepository,
	private val mqtt: MQTTManager
) : CoroutineWorker(appContext, workerParams) {
	override suspend fun doWork(): Result {
		if (!prefs.metricsOptIn().first()) return Result.success()
		mqtt.publishMetrics(MetricsPayload())
		return Result.success()
	}
}
