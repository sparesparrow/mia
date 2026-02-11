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
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

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

	fun vin(): Flow<String> = vin
	fun incognito(): Flow<Boolean> = incognitoMode
	fun retentionDays(): Flow<Int> = retentionDays
	fun metricsOptIn(): Flow<Boolean> = metricsOptIn
}
