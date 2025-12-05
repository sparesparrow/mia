package cz.mia.app.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface TelemetryDao {
	@Insert(onConflict = OnConflictStrategy.IGNORE)
	suspend fun insert(entity: TelemetryEntity)

	@Query("SELECT * FROM telemetry ORDER BY ts DESC LIMIT :limit")
	fun recent(limit: Int = 100): Flow<List<TelemetryEntity>>

	@Query("SELECT * FROM telemetry ORDER BY ts DESC LIMIT :limit")
	suspend fun snapshotRecent(limit: Int = 100): List<TelemetryEntity>

	@Query("DELETE FROM telemetry WHERE ts < :threshold")
	suspend fun deleteOlderThan(threshold: Long): Int
}

@Dao
interface AlertDao {
	@Insert(onConflict = OnConflictStrategy.IGNORE)
	suspend fun insert(entity: AlertEntity)

	@Query("SELECT * FROM alerts ORDER BY ts DESC LIMIT :limit")
	fun recent(limit: Int = 100): Flow<List<AlertEntity>>

	@Query("SELECT * FROM alerts ORDER BY ts DESC LIMIT :limit")
	suspend fun snapshotRecent(limit: Int = 100): List<AlertEntity>

	@Query("DELETE FROM alerts WHERE ts < :threshold")
	suspend fun deleteOlderThan(threshold: Long): Int
}

@Dao
interface AnprEventDao {
	@Insert(onConflict = OnConflictStrategy.IGNORE)
	suspend fun insert(entity: AnprEventEntity)

	@Query("SELECT * FROM anpr_events ORDER BY ts DESC LIMIT :limit")
	fun recent(limit: Int = 100): Flow<List<AnprEventEntity>>

	@Query("SELECT * FROM anpr_events ORDER BY ts DESC LIMIT :limit")
	suspend fun snapshotRecent(limit: Int = 100): List<AnprEventEntity>

	@Query("DELETE FROM anpr_events WHERE ts < :threshold")
	suspend fun deleteOlderThan(threshold: Long): Int
}

@Dao
interface ClipsDao {
	@Insert(onConflict = OnConflictStrategy.IGNORE)
	suspend fun insert(entity: ClipEntity)

	@Query("SELECT * FROM clips ORDER BY ts DESC LIMIT :limit")
	fun recent(limit: Int = 50): Flow<List<ClipEntity>>

	@Query("SELECT * FROM clips ORDER BY ts DESC LIMIT :limit")
	suspend fun snapshotRecent(limit: Int = 50): List<ClipEntity>

	@Query("UPDATE clips SET offloaded = 1 WHERE id = :id")
	suspend fun markOffloaded(id: Long)

	@Query("DELETE FROM clips WHERE ts < :threshold")
	suspend fun deleteOlderThan(threshold: Long): Int
}

@Dao
interface AuditDao {
	@Insert(onConflict = OnConflictStrategy.IGNORE)
	suspend fun insert(entity: AuditEventEntity)

	@Query("SELECT * FROM audit_events ORDER BY ts DESC LIMIT :limit")
	fun recent(limit: Int = 100): Flow<List<AuditEventEntity>>

	@Query("SELECT * FROM audit_events ORDER BY ts DESC LIMIT :limit")
	suspend fun snapshotRecent(limit: Int = 100): List<AuditEventEntity>

	@Query("DELETE FROM audit_events WHERE ts < :threshold")
	suspend fun deleteOlderThan(threshold: Long): Int
}
