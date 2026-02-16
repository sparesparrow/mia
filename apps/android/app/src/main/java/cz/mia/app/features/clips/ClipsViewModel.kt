package cz.mia.app.features.clips

import androidx.lifecycle.ViewModel
import cz.mia.app.data.db.ClipEntity
import cz.mia.app.data.repositories.EventRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import javax.inject.Inject

@HiltViewModel
class ClipsViewModel @Inject constructor(
    private val eventRepository: EventRepository
) : ViewModel() {
    private val scope = CoroutineScope(Dispatchers.IO)

    val clips: StateFlow<List<ClipEntity>> = eventRepository
        .getClips()
        .stateIn(scope, SharingStarted.Eagerly, emptyList())
}
