package cz.mia.app.features.settings

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.storage.PreferencesRepository
import cz.mia.app.data.repositories.EventRepository
import cz.mia.app.data.repositories.AuditRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.io.File

@HiltViewModel
class SettingsViewModel @Inject constructor(
	app: Application,
	private val prefs: PreferencesRepository,
	private val events: EventRepository,
	private val audit: AuditRepository
) : AndroidViewModel(app) {
	val vin: StateFlow<String> = prefs.vin
	val incognito: StateFlow<Boolean> = prefs.incognitoMode
	val retentionDays: StateFlow<Int> = prefs.retentionDays
	val metricsOptIn: StateFlow<Boolean> = prefs.metricsOptIn
	val anprRegion: StateFlow<String> = prefs.anprRegion

	fun setVin(v: String) { viewModelScope.launch { prefs.setVin(v); audit.record("policy", "set_vin", v) } }
	fun setIncognito(enabled: Boolean) { viewModelScope.launch { prefs.setIncognitoMode(enabled); audit.record("policy", "set_incognito", enabled.toString()) } }
	fun setRetentionDays(days: Int) { viewModelScope.launch { prefs.setRetentionDays(days); audit.record("policy", "set_retention_days", days.toString()) } }
	fun setMetricsOptIn(enabled: Boolean) { viewModelScope.launch { prefs.setMetricsOptIn(enabled); audit.record("policy", "set_metrics_opt_in", enabled.toString()) } }
	fun setAnprRegion(region: String) { viewModelScope.launch { prefs.setAnprRegion(region); audit.record("policy", "set_anpr_region", region) } }

	fun exportLogs(limit: Int = 200, onDone: (File) -> Unit) {
		viewModelScope.launch(Dispatchers.IO) {
			val file = events.exportJson(getApplication(), limit)
			audit.record("export", "logs", file.absolutePath)
			onDone(file)
		}
	}
}
