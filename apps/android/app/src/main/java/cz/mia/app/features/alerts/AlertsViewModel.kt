package cz.mia.app.features.alerts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.data.db.AlertDao
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class AlertsViewModel @Inject constructor(
	alertDao: AlertDao
) : ViewModel() {
	val recent = alertDao.recent().stateIn(viewModelScope, SharingStarted.Lazily, emptyList())
}
