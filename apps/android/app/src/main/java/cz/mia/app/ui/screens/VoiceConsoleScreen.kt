package cz.mia.app.ui.screens

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.voice.console.ConnectionState
import cz.mia.app.core.voice.console.ConsoleCommand
import cz.mia.app.core.voice.console.LedLook
import cz.mia.app.core.voice.console.LedPattern
import cz.mia.app.core.voice.console.LogKind
import cz.mia.app.core.voice.console.LogLine
import cz.mia.app.core.voice.console.VoiceConsoleState
import cz.mia.app.features.voice.VoiceConsoleViewModel
import cz.mia.app.ui.components.VoiceSettingsSection

/**
 * The voice state machine as seen from the phone (REQ-AND-016): the steering-wheel buttons as buttons,
 * the LED, the voice settings (REQ-AND-017), what was heard, what MIA said and the event queue.
 */
@Composable
fun VoiceConsoleScreen(modifier: Modifier = Modifier, viewModel: VoiceConsoleViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    DisposableEffect(viewModel) {
        viewModel.start()
        onDispose { viewModel.stop() }
    }
    VoiceConsoleContent(state, viewModel::press, modifier)
}

@Composable
fun VoiceConsoleContent(state: VoiceConsoleState, onPress: (ConsoleCommand) -> Boolean, modifier: Modifier = Modifier) {
    val connected = state.connection == ConnectionState.CONNECTED
    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Voice console", style = MaterialTheme.typography.headlineMedium)
        Text(
            text = connectionText(state),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.testTag("voice_connection"),
        )

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            LedIndicator(state.ledLook, Modifier.testTag("voice_led"))
            Column {
                Text(state.machineState, style = MaterialTheme.typography.titleLarge, modifier = Modifier.testTag("voice_state"))
                Text("LED ${state.led}, tone ${state.tone}" + (state.cue?.let { " ($it)" } ?: ""), style = MaterialTheme.typography.bodySmall)
            }
        }

        Text("Steering wheel", style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = { onPress(ConsoleCommand.GoNow) }, enabled = connected, modifier = Modifier.testTag("voice_go_now")) { Text("Go now") }
            Button(onClick = { onPress(ConsoleCommand.Cancel) }, enabled = connected, modifier = Modifier.testTag("voice_cancel")) { Text("Cancel") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(onClick = { onPress(ConsoleCommand.Wake) }, enabled = connected, modifier = Modifier.testTag("voice_wake")) { Text("Wake") }
            OutlinedButton(onClick = { onPress(ConsoleCommand.Confirm) }, enabled = connected, modifier = Modifier.testTag("voice_yes")) { Text("Yes") }
            OutlinedButton(onClick = { onPress(ConsoleCommand.Deny) }, enabled = connected, modifier = Modifier.testTag("voice_no")) { Text("No") }
            OutlinedButton(onClick = { onPress(ConsoleCommand.EndDictation) }, enabled = connected, modifier = Modifier.testTag("voice_end_dictation")) { Text("End note") }
        }

        VoiceSettingsSection(state, onPress)

        Text("Heard", style = MaterialTheme.typography.titleMedium)
        Text(state.transcript.ifEmpty { "-" }, modifier = Modifier.testTag("voice_transcript"))

        Text("MIA said", style = MaterialTheme.typography.titleMedium)
        LogList(state.spoken.takeLast(5), Modifier.testTag("voice_spoken"))

        Text("Event queue", style = MaterialTheme.typography.titleMedium)
        LogList(state.log.takeLast(25).reversed(), Modifier.testTag("voice_log"))
    }
}

private fun connectionText(state: VoiceConsoleState): String = when (state.connection) {
    ConnectionState.CONNECTED -> "Connected"
    ConnectionState.CONNECTING -> "Connecting..."
    ConnectionState.DISCONNECTED -> "Disconnected" + (state.lastError?.let { ": $it" } ?: "")
}

@Composable
private fun LedIndicator(look: LedLook, modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "led")
    val blink by transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.15f,
        animationSpec = infiniteRepeatable(tween(450), RepeatMode.Reverse),
        label = "blink",
    )
    val pulse by transition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(900), RepeatMode.Reverse),
        label = "pulse",
    )
    val alpha = when (look.pattern) {
        LedPattern.BLINK -> blink
        LedPattern.PULSE -> pulse
        else -> 1f
    }
    Box(modifier.size(56.dp).clip(CircleShape).alpha(alpha).background(Color(look.argb)))
}

@Composable
private fun LogList(lines: List<LogLine>, modifier: Modifier = Modifier) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        if (lines.isEmpty()) Text("-", style = MaterialTheme.typography.bodySmall)
        lines.forEach { line ->
            Text(
                text = line.text,
                style = MaterialTheme.typography.bodySmall,
                color = if (line.kind == LogKind.ERROR) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface,
            )
        }
        Spacer(Modifier.height(2.dp))
    }
}
