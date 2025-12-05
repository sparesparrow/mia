package cz.mia.app.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "telemetry")
data class TelemetryEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val fuelLevel: Int,
	val engineRpm: Int,
	val vehicleSpeed: Int,
	val coolantTemp: Int,
	val engineLoad: Int
)

@Entity(tableName = "alerts")
data class AlertEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val severity: String,
	val code: String,
	val message: String
)

@Entity(tableName = "anpr_events")
data class AnprEventEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val plateHash: String,
	val confidence: Float,
	val snapshotId: String?
)

@Entity(tableName = "clips")
data class ClipEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val reason: String,
	val filePath: String,
	val durationMs: Int?,
	val sizeBytes: Long,
	val offloaded: Boolean
)

@Entity(tableName = "audit_events")
data class AuditEventEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val category: String,
	val action: String,
	val details: String?
)
