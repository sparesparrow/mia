package cz.mia.app.features.voice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.BuildConfig
import cz.mia.app.core.voice.console.ConsoleCommand
import cz.mia.app.core.voice.console.OkHttpVoiceSocketFactory
import cz.mia.app.core.voice.console.VoiceConsoleClient
import cz.mia.app.core.voice.console.VoiceConsoleState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import okhttp3.OkHttpClient
import javax.inject.Inject
import javax.inject.Named

@HiltViewModel
class VoiceConsoleViewModel @Inject constructor(
    @Named("ws_base_url") baseUrl: String,
    okHttpClient: OkHttpClient,
) : ViewModel() {
    private val client = VoiceConsoleClient(
        url = consoleUrl(baseUrl),
        headers = authHeaders(BuildConfig.API_KEY),
        factory = OkHttpVoiceSocketFactory(okHttpClient),
        scope = viewModelScope,
    )

    val state: StateFlow<VoiceConsoleState> = client.state

    /** Called when the screen appears. */
    fun start() = client.connect()

    /** Called when the screen goes away, so a hidden console does not hold the session open. */
    fun stop() = client.disconnect()

    fun press(command: ConsoleCommand): Boolean = client.send(command)

    override fun onCleared() {
        client.disconnect()
    }

    companion object {
        fun consoleUrl(wsBaseUrl: String): String = wsBaseUrl.trimEnd('/') + "/ws/voice"

        /** The Pi wants the key in a header, never in the URL (REQ-SEC-001). No key, no header. */
        fun authHeaders(apiKey: String): Map<String, String> =
            if (apiKey.isBlank()) emptyMap() else mapOf("X-API-Key" to apiKey)
    }
}
