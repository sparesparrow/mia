package cz.mia.app.features.settings

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.networking.PiAddress
import cz.mia.app.core.networking.PiAddressResult
import cz.mia.app.core.networking.PiConnection
import cz.mia.app.core.networking.PiConnectionProvider
import cz.mia.app.core.networking.resolvePiConnection
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
	private val audit: AuditRepository,
	private val piConnection: PiConnectionProvider
) : AndroidViewModel(app) {
	val vin: StateFlow<String> = prefs.vin
	val incognito: StateFlow<Boolean> = prefs.incognitoMode
	val retentionDays: StateFlow<Int> = prefs.retentionDays
	val metricsOptIn: StateFlow<Boolean> = prefs.metricsOptIn
	val anprRegion: StateFlow<String> = prefs.anprRegion
	val piAddress: StateFlow<String> = prefs.piAddress
	val piApiKey: StateFlow<String> = prefs.piApiKey

	fun setVin(v: String) { viewModelScope.launch { prefs.setVin(v); audit.record("policy", "set_vin", v) } }
	fun setIncognito(enabled: Boolean) { viewModelScope.launch { prefs.setIncognitoMode(enabled); audit.record("policy", "set_incognito", enabled.toString()) } }
	fun setRetentionDays(days: Int) { viewModelScope.launch { prefs.setRetentionDays(days); audit.record("policy", "set_retention_days", days.toString()) } }
	fun setMetricsOptIn(enabled: Boolean) { viewModelScope.launch { prefs.setMetricsOptIn(enabled); audit.record("policy", "set_metrics_opt_in", enabled.toString()) } }
	fun setAnprRegion(region: String) { viewModelScope.launch { prefs.setAnprRegion(region); audit.record("policy", "set_anpr_region", region) } }

	/** Where the app would connect with this address and key (the build's defaults when the address is blank). */
	fun preview(address: String, apiKey: String): PiConnection =
		resolvePiConnection(address, apiKey, piConnection.defaults)

	/**
	 * Saves the Pi address and API key. Returns why the address was refused, or null once it is saved.
	 * The audit log records the address and only whether a key is set, never the key.
	 */
	fun savePiConnection(address: String, apiKey: String): String? {
		val trimmed = address.trim()
		val target = if (trimmed.isEmpty()) {
			"default"
		} else {
			when (val parsed = PiAddress.parse(trimmed)) {
				is PiAddressResult.Invalid -> return parsed.reason
				is PiAddressResult.Valid -> parsed.apiBaseUrl
			}
		}
		val key = apiKey.trim()
		viewModelScope.launch {
			piConnection.save(trimmed, key)
			audit.record("policy", "set_pi_address", target)
			audit.record("policy", "set_pi_api_key", if (key.isEmpty()) "cleared" else "set")
		}
		return null
	}

	fun exportLogs(limit: Int = 200, onDone: (File) -> Unit) {
		viewModelScope.launch(Dispatchers.IO) {
			val file = events.exportJson(getApplication(), limit)
			audit.record("export", "logs", file.absolutePath)
			onDone(file)
		}
	}
}
