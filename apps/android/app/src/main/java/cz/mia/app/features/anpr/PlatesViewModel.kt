package cz.mia.app.features.anpr

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.security.PlateIdentity
import cz.mia.app.data.db.AnprEventDao
import cz.mia.app.data.db.WatchlistDao
import cz.mia.app.data.db.WatchlistEntity
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.withContext

/** A plate the camera saw lately, known only by its hash. */
data class RecentPlate(
	val plateHash: String,
	val lastSeen: Long,
	val sightings: Int,
	val listed: Boolean,
)

sealed class AddPlateResult {
	object Added : AddPlateResult()
	data class Refused(val reason: String) : AddPlateResult()
}

/**
 * The black book (REQ-AND-020): plates the user wants to be told about, added by typing a plate or by picking a
 * recent sighting. A typed plate is hashed at once with this install's key and only the hash is stored; the screen
 * clears the text afterwards.
 */
@HiltViewModel
class PlatesViewModel(
	private val watchlist: WatchlistDao,
	anpr: AnprEventDao,
	private val identity: PlateIdentity,
	private val now: () -> Long,
	private val io: CoroutineDispatcher,
) : ViewModel() {
	@Inject
	constructor(watchlist: WatchlistDao, anpr: AnprEventDao, identity: PlateIdentity) :
		this(watchlist, anpr, identity, System::currentTimeMillis, Dispatchers.IO)

	val entries: StateFlow<List<WatchlistEntity>> =
		watchlist.all().stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

	val recent: StateFlow<List<RecentPlate>> = combine(anpr.recent(RECENT_EVENTS), watchlist.all()) { events, listed ->
		val listedHashes = listed.mapTo(HashSet()) { it.plateHash }
		events.groupBy { it.plateHash }
			.map { (hash, seen) -> RecentPlate(hash, seen.maxOf { it.ts }, seen.size, hash in listedHashes) }
			.sortedByDescending { it.lastSeen }
			.take(RECENT_PLATES)
	}.stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

	suspend fun addTyped(plate: String, label: String): AddPlateResult {
		if (!identity.isPlausible(plate)) {
			return AddPlateResult.Refused("A plate is 4 to 10 letters and digits")
		}
		withContext(io) { watchlist.upsert(WatchlistEntity(identity.hash(plate), cleanLabel(label), now())) }
		return AddPlateResult.Added
	}

	suspend fun addSighting(plateHash: String, label: String) {
		withContext(io) { watchlist.upsert(WatchlistEntity(plateHash, cleanLabel(label), now())) }
	}

	suspend fun remove(plateHash: String) {
		withContext(io) { watchlist.delete(plateHash) }
	}

	companion object {
		const val MAX_LABEL = 40
		private const val RECENT_EVENTS = 200
		private const val RECENT_PLATES = 20

		fun cleanLabel(label: String): String = label.trim().replace(Regex("\\s+"), " ").take(MAX_LABEL)
	}
}
