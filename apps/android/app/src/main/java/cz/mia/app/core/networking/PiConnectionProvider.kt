package cz.mia.app.core.networking

import cz.mia.app.BuildConfig
import cz.mia.app.core.storage.PreferencesRepository
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.runBlocking

/**
 * The current [PiConnection]: the Pi address and key from Settings, or the build's defaults.
 *
 * [current] is a plain read, so a request interceptor or a view model can use it without suspending. The
 * stored settings are read once when this singleton is first created (a few bytes of preferences) so
 * that the first caller never sees the defaults by mistake; after that a collector keeps it current.
 * [connections] carries the same value as a flow, for long-lived connections that must follow a change.
 */
@Singleton
class PiConnectionProvider @Inject constructor(
    private val prefs: PreferencesRepository,
) {
    val defaults = PiConnection(
        apiBaseUrl = BuildConfig.API_BASE_URL,
        wsBaseUrl = BuildConfig.WS_BASE_URL,
        apiKey = BuildConfig.API_KEY,
    )

    private val _connections = MutableStateFlow(
        runBlocking(Dispatchers.IO) {
            prefs.readPiSettings().let { resolvePiConnection(it.address, it.apiKey, defaults) }
        }
    )
    val connections: StateFlow<PiConnection> = _connections.asStateFlow()

    init {
        prefs.piSettings
            .onEach { _connections.value = resolvePiConnection(it.address, it.apiKey, defaults) }
            .launchIn(CoroutineScope(SupervisorJob() + Dispatchers.IO))
    }

    fun current(): PiConnection = _connections.value

    /** Stores the address and key, and makes them current before returning. */
    suspend fun save(address: String, apiKey: String) {
        prefs.setPiSettings(address, apiKey)
        _connections.value = resolvePiConnection(address, apiKey, defaults)
    }
}
