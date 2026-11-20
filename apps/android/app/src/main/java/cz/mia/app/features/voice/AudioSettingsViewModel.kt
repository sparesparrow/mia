package cz.mia.app.features.voice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.audio.AudioSettingsReport
import cz.mia.app.core.audio.AudioSettingsRepository
import cz.mia.app.core.audio.AudioSettingsResult
import cz.mia.app.core.audio.MicTransport
import cz.mia.app.core.audio.ReplyOutput
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AudioSettingsUi(
    val loading: Boolean = false,
    /** What the Pi reported; null until it did. The screen shows this, never what was last asked for. */
    val report: AudioSettingsReport? = null,
    val message: String? = null,
)

@HiltViewModel
class AudioSettingsViewModel @Inject constructor(
    private val repository: AudioSettingsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AudioSettingsUi())
    val state: StateFlow<AudioSettingsUi> = _state.asStateFlow()

    fun refresh() = launchCall { repository.load() }

    fun chooseMic(option: MicTransport) = launchCall { repository.change(option, null) }

    fun chooseReply(option: ReplyOutput) = launchCall { repository.change(null, option) }

    private fun launchCall(call: suspend () -> AudioSettingsResult) {
        _state.value = _state.value.copy(loading = true, message = null)
        viewModelScope.launch {
            _state.value = when (val result = call()) {
                is AudioSettingsResult.Ok -> AudioSettingsUi(report = result.report)
                AudioSettingsResult.Unavailable -> _state.value.copy(
                    loading = false,
                    message = "The Pi cannot do that yet",
                )
                is AudioSettingsResult.Failed -> _state.value.copy(loading = false, message = result.message)
            }
        }
    }
}
