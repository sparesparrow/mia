package cz.mia.app.data.repositories

import android.content.Context
import com.google.gson.Gson
import cz.mia.app.core.background.ANPREvent
import cz.mia.app.core.background.OBDData
import cz.mia.app.core.background.VehicleAlert
import cz.mia.app.data.db.AlertDao
import cz.mia.app.data.db.AlertEntity
import cz.mia.app.data.db.AnprEventDao
import cz.mia.app.data.db.AnprEventEntity
import cz.mia.app.data.db.ClipEntity
import cz.mia.app.data.db.ClipsDao
import cz.mia.app.data.db.TelemetryDao
import cz.mia.app.data.db.TelemetryEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

interface EventRepository {
	suspend fun recordTelemetry(data: OBDData)
	suspend fun recordAlert(alert: VehicleAlert)
	suspend fun recordAnpr(event: ANPREvent)
	fun getTelemetry(): Flow<List<TelemetryEntity>>
	fun getAlerts(): Flow<List<AlertEntity>>
	fun getAnprEvents(): Flow<List<AnprEventEntity>>
	fun getClips(): Flow<List<ClipEntity>>
	suspend fun exportJson(context: Context, limitPerType: Int = 200): File
	suspend fun deleteOldData(retentionDays: Int)
}

@Singleton
class EventRepositoryImpl @Inject constructor(
	private val telemetryDao: TelemetryDao,
	private val alertDao: AlertDao,
	private val anprDao: AnprEventDao,
	private val clipsDao: ClipsDao,
	private val gson: Gson
) : EventRepository {
	override suspend fun recordTelemetry(data: OBDData) {
		telemetryDao.insert(
			TelemetryEntity(
				ts = System.currentTimeMillis(),
				fuelLevel = data.fuelLevel,
				engineRpm = data.engineRpm,
				vehicleSpeed = data.vehicleSpeed,
				coolantTemp = data.coolantTemp,
				engineLoad = data.engineLoad
			)
		)
	}

	override suspend fun recordAlert(alert: VehicleAlert) {
		alertDao.insert(
			AlertEntity(
				ts = alert.timestamp,
				severity = alert.severity.name,
				code = alert.code,
				message = alert.message
			)
		)
	}

	override suspend fun recordAnpr(event: ANPREvent) {
		anprDao.insert(
			AnprEventEntity(
				ts = event.timestamp,
				plateHash = event.plateHash,
				confidence = event.confidence,
				snapshotId = event.snapshotId
			)
		)
	}

	override fun getTelemetry(): Flow<List<TelemetryEntity>> = telemetryDao.recent()
	override fun getAlerts(): Flow<List<AlertEntity>> = alertDao.recent()
	override fun getAnprEvents(): Flow<List<AnprEventEntity>> = anprDao.recent()
	override fun getClips(): Flow<List<ClipEntity>> = clipsDao.recent()

	data class ExportBundle(
		val telemetry: List<TelemetryEntity>,
		val alerts: List<AlertEntity>,
		val anpr: List<AnprEventEntity>,
		val clips: List<ClipEntity>
	)

	override suspend fun exportJson(context: Context, limitPerType: Int): File = withContext(Dispatchers.IO) {
		val bundle = ExportBundle(
			telemetry = telemetryDao.snapshotRecent(limitPerType),
			alerts = alertDao.snapshotRecent(limitPerType),
			anpr = anprDao.snapshotRecent(limitPerType),
			clips = clipsDao.snapshotRecent(limitPerType)
		)
		val json = gson.toJson(bundle)
		val dir = File(context.filesDir, "exports").apply { if (!exists()) mkdirs() }
		val file = File(dir, "ai_servis_export_${System.currentTimeMillis()}.json")
		file.writeText(json)
		file
	}

	override suspend fun deleteOldData(retentionDays: Int) {
		val cutoffTime = System.currentTimeMillis() - (retentionDays * 24 * 60 * 60 * 1000L)
		telemetryDao.deleteOlderThan(cutoffTime)
		alertDao.deleteOlderThan(cutoffTime)
		anprDao.deleteOlderThan(cutoffTime)
		clipsDao.deleteOlderThan(cutoffTime)
	}
}
