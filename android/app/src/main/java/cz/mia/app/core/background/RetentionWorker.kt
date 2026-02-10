package cz.mia.app.core.background

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import cz.mia.app.core.storage.PreferencesRepository
import cz.mia.app.data.db.AlertDao
import cz.mia.app.data.db.AnprEventDao
import cz.mia.app.data.db.TelemetryDao
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit

@HiltWorker
class RetentionWorker @AssistedInject constructor(
	@Assisted appContext: Context,
	@Assisted workerParams: WorkerParameters,
	private val telemetryDao: TelemetryDao,
	private val alertDao: AlertDao,
	private val anprDao: AnprEventDao,
	private val prefs: PreferencesRepository
) : CoroutineWorker(appContext, workerParams) {
	override suspend fun doWork(): Result {
		if (prefs.incognito().first()) return Result.success()
		val days = prefs.retentionDays().first().coerceIn(1, 90)
		val threshold = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(days.toLong())
		telemetryDao.deleteOlderThan(threshold)
		alertDao.deleteOlderThan(threshold)
		anprDao.deleteOlderThan(threshold)
		return Result.success()
	}
}
