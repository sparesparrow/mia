package cz.mia.app.features.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import cz.mia.app.core.networking.PiConnection
import cz.mia.app.core.networking.PiConnectionProvider
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.websocket.TelemetryWebSocket
import cz.mia.app.data.remote.websocket.WebSocketState
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.data.repositories.EventRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class DashboardViewModel @Inject constructor(
	private val repository: EventRepository,
	private val gson: Gson,
	private val piConnection: PiConnectionProvider
) : ViewModel() {
	val latest = repository.getTelemetry()
		.map { it.firstOrNull() }
		.stateIn(viewModelScope, SharingStarted.Lazily, null as TelemetryEntity?)

	private val _cycle1Telemetry = MutableStateFlow<Cycle1TelemetryEnvelope?>(null)
	val cycle1Telemetry: StateFlow<Cycle1TelemetryEnvelope?> = _cycle1Telemetry.asStateFlow()

	private val _cycle1Connection = MutableStateFlow<WebSocketState>(WebSocketState.Disconnected)
	val cycle1Connection: StateFlow<WebSocketState> = _cycle1Connection.asStateFlow()

	private var cycle1WebSocket: TelemetryWebSocket? = null
	private var cycle1Target: PiConnection? = null
	private var cycle1Collectors: Job? = null

	/** Connects to the Pi in Settings; when the address or key changed since the last call, reconnects to it. */
	fun initializeCycle1Telemetry() {
		val target = piConnection.current()
		if (cycle1WebSocket != null && cycle1Target == target) return
		closeCycle1()

		val webSocket = TelemetryWebSocket(target.wsBaseUrl, gson, target.authHeaders())
		cycle1WebSocket = webSocket
		cycle1Target = target

		cycle1Collectors = viewModelScope.launch {
			launch { webSocket.stateFlow.collectLatest { state -> _cycle1Connection.value = state } }
			launch {
				webSocket.telemetryFlow.collectLatest { message ->
					message.vehicleTelemetry?.let { _cycle1Telemetry.value = it }
				}
			}
		}
		webSocket.connect()
	}

	private fun closeCycle1() {
		cycle1Collectors?.cancel()
		cycle1Collectors = null
		cycle1WebSocket?.cleanup()
		cycle1WebSocket = null
		cycle1Target = null
	}

	override fun onCleared() {
		closeCycle1()
		super.onCleared()
	}
}
