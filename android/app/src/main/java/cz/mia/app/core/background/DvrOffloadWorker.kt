package cz.mia.app.core.background

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import cz.mia.app.data.db.ClipsDao
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class DvrOffloadWorker @AssistedInject constructor(
	@Assisted appContext: Context,
	@Assisted workerParams: WorkerParameters,
	private val clipsDao: ClipsDao
) : CoroutineWorker(appContext, workerParams) {
	override suspend fun doWork(): Result {
		// Placeholder: iterate recent clips and mark offloaded after transfer
		// Future: check Wi‑Fi SSID/home network, upload to storage, markOffloaded(id)
		return Result.success()
	}
}
