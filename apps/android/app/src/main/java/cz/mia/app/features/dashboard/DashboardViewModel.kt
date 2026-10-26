package cz.mia.app.features.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.websocket.Cycle1TelemetrySource
import cz.mia.app.data.remote.websocket.WebSocketState
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.data.repositories.EventRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class DashboardViewModel @Inject constructor(
	private val repository: EventRepository,
	private val cycle1Source: Cycle1TelemetrySource,
) : ViewModel() {
	val latest = repository.getTelemetry()
		.map { it.firstOrNull() }
		.stateIn(viewModelScope, SharingStarted.Lazily, null as TelemetryEntity?)

	val cycle1Telemetry: StateFlow<Cycle1TelemetryEnvelope?> = cycle1Source.envelope

	val cycle1Connection: StateFlow<WebSocketState> = cycle1Source.connection

	private var cycle1Lease: Cycle1TelemetrySource.Lease? = null

	/**
	 * Starts receiving the Pi's Cycle 1 telemetry. The connection is shared with the driving service and follows
	 * the Pi address and key in Settings on its own.
	 */
	fun initializeCycle1Telemetry() {
		if (cycle1Lease == null) cycle1Lease = cycle1Source.acquire()
	}

	override fun onCleared() {
		cycle1Lease?.release()
		cycle1Lease = null
		super.onCleared()
	}
}
