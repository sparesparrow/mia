package cz.mia.app.data.db

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "telemetry")
data class TelemetryEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val fuelLevel: Int,
	val engineRpm: Int,
	val vehicleSpeed: Int,
	val coolantTemp: Int,
	val engineLoad: Int,
	// Citroën C4 specific fields
	val dpfSootMass: Float? = null,
	val adBlueLevel: Int? = null,
	val dpfStatus: String? = null,
	val particulateFilterEfficiency: Float? = null,
	val differentialPressure: Float? = null,
	val eolysAdditiveLevel: Float? = null
)

@Entity(tableName = "alerts")
data class AlertEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val severity: String,
	val code: String,
	val message: String
)

/** One camera sighting. Indexed by plate and time for the repeated-sighting lookup (REQ-AND-021). */
@Entity(tableName = "anpr_events", indices = [Index(value = ["plateHash", "ts"])])
data class AnprEventEntity(
	@PrimaryKey(autoGenerate = true) val id: Long = 0,
	val ts: Long,
	val plateHash: String,
	val confidence: Float,
	val snapshotId: String?
)

/**
 * A black-book plate (REQ-AND-020): the hash of a plate the user chose to be told about, and their label for it. The
 * clear plate is never stored. Entries stay until the user removes them; retention does not apply (ADR-0018).
 */
@Entity(tableName = "watchlist")
data class WatchlistEntity(
	@PrimaryKey val plateHash: String,
	val label: String,
	val addedAt: Long
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
