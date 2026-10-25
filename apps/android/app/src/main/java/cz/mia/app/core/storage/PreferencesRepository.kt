package cz.mia.app.core.storage

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

/** The Pi address and API key the user typed in Settings; both empty until the user sets them. */
data class PiSettings(val address: String = "", val apiKey: String = "") {
	/** Never prints the key. */
	override fun toString(): String = "PiSettings(address=$address, apiKey=${if (apiKey.isBlank()) "none" else "set"})"
}

private val Context.dataStore by preferencesDataStore(name = "settings")

@Singleton
class PreferencesRepository @Inject constructor(
	@ApplicationContext private val context: Context
) {
	private object Keys {
		val VIN = stringPreferencesKey("vin")
		val INCOGNITO = booleanPreferencesKey("incognito")
		val RETENTION_DAYS = intPreferencesKey("retention_days")
		val METRICS_OPT_IN = booleanPreferencesKey("metrics_opt_in")
		val LAST_HEALTH_PING_TS = longPreferencesKey("last_health_ping_ts")
		val ANPR_REGION = stringPreferencesKey("anpr_region")
		val PI_ADDRESS = stringPreferencesKey("pi_address")
		val PI_API_KEY = stringPreferencesKey("pi_api_key")
	}

	private val scope = CoroutineScope(Dispatchers.IO)

	val vin: StateFlow<String> = context.dataStore.data.map { prefs: Preferences ->
		prefs[Keys.VIN] ?: "DEMO_VIN"
	}.stateIn(scope, SharingStarted.Eagerly, "DEMO_VIN")

	suspend fun setVin(vin: String) {
		context.dataStore.edit { prefs ->
			prefs[Keys.VIN] = vin
		}
	}

	val incognitoMode: StateFlow<Boolean> = context.dataStore.data.map { prefs ->
		prefs[Keys.INCOGNITO] ?: false
	}.stateIn(scope, SharingStarted.Eagerly, false)

	suspend fun setIncognitoMode(enabled: Boolean) {
		context.dataStore.edit { it[Keys.INCOGNITO] = enabled }
	}

	val retentionDays: StateFlow<Int> = context.dataStore.data.map { prefs ->
		prefs[Keys.RETENTION_DAYS] ?: 2
	}.stateIn(scope, SharingStarted.Eagerly, 2)

	suspend fun setRetentionDays(days: Int) {
		context.dataStore.edit { it[Keys.RETENTION_DAYS] = days }
	}

	val metricsOptIn: StateFlow<Boolean> = context.dataStore.data.map { prefs ->
		prefs[Keys.METRICS_OPT_IN] ?: false
	}.stateIn(scope, SharingStarted.Eagerly, false)

	suspend fun setMetricsOptIn(enabled: Boolean) {
		context.dataStore.edit { it[Keys.METRICS_OPT_IN] = enabled }
	}

	suspend fun setLastHealthPingTs(ts: Long) {
		context.dataStore.edit { it[Keys.LAST_HEALTH_PING_TS] = ts }
	}

	val anprRegion: StateFlow<String> = context.dataStore.data.map { prefs ->
		prefs[Keys.ANPR_REGION] ?: "CZ"
	}.stateIn(scope, SharingStarted.Eagerly, "CZ")

	suspend fun setAnprRegion(region: String) {
		context.dataStore.edit { it[Keys.ANPR_REGION] = region }
	}

	val piAddress: StateFlow<String> = context.dataStore.data.map { prefs ->
		prefs[Keys.PI_ADDRESS] ?: ""
	}.stateIn(scope, SharingStarted.Eagerly, "")

	val piApiKey: StateFlow<String> = context.dataStore.data.map { prefs ->
		prefs[Keys.PI_API_KEY] ?: ""
	}.stateIn(scope, SharingStarted.Eagerly, "")

	/**
	 * What is stored. Unlike [piAddress] and [piApiKey], whose first value is an empty default until the
	 * file has been read, the first value of this flow is the stored one.
	 */
	val piSettings: Flow<PiSettings> = context.dataStore.data.map { prefs ->
		PiSettings(prefs[Keys.PI_ADDRESS] ?: "", prefs[Keys.PI_API_KEY] ?: "")
	}

	suspend fun readPiSettings(): PiSettings = piSettings.first()

	suspend fun setPiSettings(address: String, apiKey: String) {
		context.dataStore.edit { prefs ->
			prefs[Keys.PI_ADDRESS] = address
			prefs[Keys.PI_API_KEY] = apiKey
		}
	}

	fun vin(): Flow<String> = vin
	fun incognito(): Flow<Boolean> = incognitoMode
	fun retentionDays(): Flow<Int> = retentionDays
	fun metricsOptIn(): Flow<Boolean> = metricsOptIn
}
