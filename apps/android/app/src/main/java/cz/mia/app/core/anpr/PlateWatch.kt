package cz.mia.app.core.anpr

import cz.mia.app.data.db.AnprEventDao
import cz.mia.app.data.db.WatchlistDao
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** What a plate sighting is worth telling the driver. */
sealed class PlateAlert {
	abstract val plateHash: String

	/** A plate from the black book was seen (REQ-AND-020). */
	data class Listed(override val plateHash: String, val label: String) : PlateAlert()

	/** A plate not in the black book keeps turning up (REQ-AND-021). */
	data class Repeated(override val plateHash: String, val episodes: Int, val spanMs: Long) : PlateAlert()
}

/**
 * Checks each stored sighting against the black book and against the plate's own recent sightings.
 *
 * - A black-book plate is announced at most once per [listedRepeatMs] (10 min) and never as a repeated plate.
 * - Any other plate is announced as repeated when [RepeatSightings] says so over the last [lookbackMs] (24 h, never
 *   longer than the retention period, whose minimum is a day), at most once per [repeatedRepeatMs] (24 h).
 *
 * Both limits are kept in memory, so they start over when the app process does.
 */
@Singleton
class PlateWatch(
	private val watchlist: WatchlistDao,
	private val sightings: AnprEventDao,
	private val now: () -> Long,
	private val listedRepeatMs: Long = 10 * 60_000L,
	private val repeatedRepeatMs: Long = DAY_MS,
	private val lookbackMs: Long = DAY_MS,
) {
	@Inject
	constructor(watchlist: WatchlistDao, sightings: AnprEventDao) :
		this(watchlist, sightings, System::currentTimeMillis)

	private val lock = Mutex()
	private val lastListed = mutableMapOf<String, Long>()
	private val lastRepeated = mutableMapOf<String, Long>()

	/** Call once the sighting of [plateHash] has been stored. */
	suspend fun check(plateHash: String): PlateAlert? = lock.withLock {
		val time = now()
		lastListed.values.removeAll { time - it >= listedRepeatMs }
		lastRepeated.values.removeAll { time - it >= repeatedRepeatMs }

		val listed = watchlist.find(plateHash)
		if (listed != null) {
			if (plateHash in lastListed) return@withLock null
			lastListed[plateHash] = time
			return@withLock PlateAlert.Listed(plateHash, listed.label)
		}

		if (plateHash in lastRepeated) return@withLock null
		val times = sightings.sightingTimes(plateHash, time - lookbackMs)
		if (!RepeatSightings.isRepeated(times)) return@withLock null
		lastRepeated[plateHash] = time
		PlateAlert.Repeated(
			plateHash = plateHash,
			episodes = RepeatSightings.episodeStarts(times).size,
			spanMs = times.max() - times.min(),
		)
	}

	companion object {
		const val DAY_MS = 24 * 3_600_000L
	}
}
