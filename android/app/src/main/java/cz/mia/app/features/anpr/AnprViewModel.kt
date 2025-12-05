package cz.mia.app.features.anpr

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.data.db.AnprEventDao
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class AnprViewModel @Inject constructor(
	anprDao: AnprEventDao
) : ViewModel() {
	val recent = anprDao.recent().stateIn(viewModelScope, SharingStarted.Lazily, emptyList())
}
