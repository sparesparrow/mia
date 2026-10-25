package cz.mia.app.data.db

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map

/** In-memory stand-ins for the plate DAOs, for JVM tests. */
class FakeAnprEventDao : AnprEventDao {
	val rows = MutableStateFlow<List<AnprEventEntity>>(emptyList())

	fun seen(plateHash: String, vararg times: Long) {
		rows.value = rows.value + times.map { AnprEventEntity(ts = it, plateHash = plateHash, confidence = 0.9f, snapshotId = null) }
	}

	override suspend fun insert(entity: AnprEventEntity) {
		rows.value = rows.value + entity
	}

	override fun recent(limit: Int): Flow<List<AnprEventEntity>> = rows.map { all -> all.sortedByDescending { it.ts }.take(limit) }

	override suspend fun snapshotRecent(limit: Int): List<AnprEventEntity> = rows.value.sortedByDescending { it.ts }.take(limit)

	override suspend fun deleteOlderThan(threshold: Long): Int {
		val before = rows.value.size
		rows.value = rows.value.filter { it.ts >= threshold }
		return before - rows.value.size
	}

	override suspend fun sightingTimes(plateHash: String, since: Long): List<Long> =
		rows.value.filter { it.plateHash == plateHash && it.ts >= since }.map { it.ts }.sorted()
}

class FakeWatchlistDao : WatchlistDao {
	val rows = MutableStateFlow<Map<String, WatchlistEntity>>(emptyMap())

	override suspend fun upsert(entity: WatchlistEntity) {
		rows.value = rows.value + (entity.plateHash to entity)
	}

	override fun all(): Flow<List<WatchlistEntity>> = rows.map { it.values.sortedByDescending { e -> e.addedAt } }

	override suspend fun find(plateHash: String): WatchlistEntity? = rows.value[plateHash]

	override suspend fun delete(plateHash: String): Int {
		val had = plateHash in rows.value
		rows.value = rows.value - plateHash
		return if (had) 1 else 0
	}
}
