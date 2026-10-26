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

	/** When one plate was seen since [since], oldest first. */
	@Query("SELECT ts FROM anpr_events WHERE plateHash = :plateHash AND ts >= :since ORDER BY ts")
	suspend fun sightingTimes(plateHash: String, since: Long): List<Long>
}

@Dao
interface WatchlistDao {
	/** Adds a plate, or replaces the label of one already listed. */
	@Insert(onConflict = OnConflictStrategy.REPLACE)
	suspend fun upsert(entity: WatchlistEntity)

	@Query("SELECT * FROM watchlist ORDER BY addedAt DESC")
	fun all(): Flow<List<WatchlistEntity>>

	@Query("SELECT * FROM watchlist WHERE plateHash = :plateHash")
	suspend fun find(plateHash: String): WatchlistEntity?

	@Query("DELETE FROM watchlist WHERE plateHash = :plateHash")
	suspend fun delete(plateHash: String): Int
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
