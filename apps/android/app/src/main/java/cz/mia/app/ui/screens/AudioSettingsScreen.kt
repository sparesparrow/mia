package cz.mia.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.audio.AudioSettingsReport
import cz.mia.app.core.audio.MicTransport
import cz.mia.app.core.audio.ReplyOutput
import cz.mia.app.features.voice.AudioSettingsUi
import cz.mia.app.features.voice.AudioSettingsViewModel
import cz.mia.app.ui.components.SectionCard

/**
 * Audio settings (ADR-0021, ADR-0019): where MIA's microphone comes from and where replies are heard. The Pi
 * owns the choice; this shows what it reports and marks what it cannot do, never a choice it did not accept.
 */
@Composable
fun AudioSettingsScreen(modifier: Modifier = Modifier, viewModel: AudioSettingsViewModel = hiltViewModel()) {
    val ui by viewModel.state.collectAsState()
    LaunchedEffect(viewModel) { viewModel.refresh() }
    AudioSettingsContent(ui, viewModel::chooseMic, viewModel::chooseReply, modifier)
}

@Composable
fun AudioSettingsContent(
    ui: AudioSettingsUi,
    onMic: (MicTransport) -> Unit,
    onReply: (ReplyOutput) -> Unit,
    modifier: Modifier = Modifier,
) {
    val report = ui.report
    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (report == null) {
            Text(
                text = if (ui.loading) "Asking the Pi..." else ui.message ?: "Not read from the Pi yet",
                modifier = Modifier.testTag("audio_status"),
            )
            return@Column
        }
        SectionCard(title = "Microphone") {
            MicTransport.values().forEach { option ->
                Option(
                    label = option.label,
                    selected = report.micTransport == option,
                    available = report.available(option),
                    tag = "audio_mic_${option.wire}",
                ) { onMic(option) }
            }
        }
        SectionCard(title = "Replies") {
            ReplyOutput.values().forEach { option ->
                Option(
                    label = option.label,
                    selected = report.replyOutput == option,
                    available = report.available(option),
                    tag = "audio_reply_${option.wire}",
                ) { onReply(option) }
            }
        }
        Text(footnote(report), style = MaterialTheme.typography.bodySmall, modifier = Modifier.testTag("audio_footnote"))
        ui.message?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.testTag("audio_status")) }
    }
}

/** Why options are greyed out; the Pi's own report decides, so this never claims Bluetooth works. */
fun footnote(report: AudioSettingsReport): String =
    if (report.btAudioAvailable) {
        "Greyed-out options are not available on this Pi."
    } else {
        "Bluetooth audio is not available on this Pi: it has no audio service for it yet. Greyed-out options cannot be chosen."
    }

@Composable
private fun Option(label: String, selected: Boolean, available: Boolean, tag: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().testTag(tag),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = selected, onClick = onClick, enabled = available)
        Text(
            text = if (available) label else "$label (unavailable)",
            color = if (available) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
