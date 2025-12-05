package cz.mia.app.features.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.data.repositories.EventRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class DashboardViewModel @Inject constructor(
	private val repository: EventRepository
) : ViewModel() {
	val latest = repository.getTelemetry()
		.map { it.firstOrNull() }
		.stateIn(viewModelScope, SharingStarted.Lazily, null as TelemetryEntity?)
}
