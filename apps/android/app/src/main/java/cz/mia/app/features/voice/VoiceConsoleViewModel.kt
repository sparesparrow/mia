package cz.mia.app.features.voice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.networking.PiConnection
import cz.mia.app.core.networking.PiConnectionProvider
import cz.mia.app.core.voice.console.ConsoleCommand
import cz.mia.app.core.voice.console.OkHttpVoiceSocketFactory
import cz.mia.app.core.voice.console.VoiceConsoleClient
import cz.mia.app.core.voice.console.VoiceConsoleState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import javax.inject.Inject

@HiltViewModel
class VoiceConsoleViewModel @Inject constructor(
    private val piConnection: PiConnectionProvider,
    private val okHttpClient: OkHttpClient,
) : ViewModel() {
    private var client: VoiceConsoleClient? = null
    private var clientTarget: PiConnection? = null
    private var stateJob: Job? = null

    private val _state = MutableStateFlow(VoiceConsoleState())
    val state: StateFlow<VoiceConsoleState> = _state.asStateFlow()

    /** Called when the screen appears. Connects to the Pi in Settings, which may have changed since last time. */
    fun start() {
        val target = piConnection.current()
        if (client == null || clientTarget != target) {
            client?.disconnect()
            stateJob?.cancel()
            val fresh = VoiceConsoleClient(
                url = consoleUrl(target.wsBaseUrl),
                headers = authHeaders(target.apiKey),
                factory = OkHttpVoiceSocketFactory(okHttpClient),
                scope = viewModelScope,
            )
            client = fresh
            clientTarget = target
            stateJob = viewModelScope.launch { fresh.state.collect { _state.value = it } }
        }
        client?.connect()
    }

    /** Called when the screen goes away, so a hidden console does not hold the session open. */
    fun stop() {
        client?.disconnect()
    }

    fun press(command: ConsoleCommand): Boolean = client?.send(command) ?: false

    override fun onCleared() {
        client?.disconnect()
    }

    companion object {
        fun consoleUrl(wsBaseUrl: String): String = wsBaseUrl.trimEnd('/') + "/ws/voice"

        /** The Pi wants the key in a header, never in the URL (REQ-SEC-001). No key, no header. */
        fun authHeaders(apiKey: String): Map<String, String> = PiConnection.headersFor(apiKey)
    }
}
