package cz.mia.app.core.voice.mic

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * What the UI and [MicStreamService] tell each other: whether the user switched the phone microphone on, whether
 * the Pi wants audio right now (push-to-talk) and the state of the stream.
 */
object MicStreamController {
    private val _enabled = MutableStateFlow(false)
    private val _talking = MutableStateFlow(false)
    private val _link = MutableStateFlow(MicLink.OFF)

    val enabled: StateFlow<Boolean> = _enabled.asStateFlow()
    val talking: StateFlow<Boolean> = _talking.asStateFlow()
    val link: StateFlow<MicLink> = _link.asStateFlow()

    fun setEnabled(value: Boolean) {
        _enabled.value = value
        if (!value) {
            _talking.value = false
            _link.value = MicLink.OFF
        }
    }

    fun setTalking(value: Boolean) {
        _talking.value = value && _enabled.value
    }

    fun setLink(value: MicLink) {
        _link.value = value
    }
}
