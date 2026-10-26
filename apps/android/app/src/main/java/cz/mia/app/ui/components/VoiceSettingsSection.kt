package cz.mia.app.ui.components

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import cz.mia.app.core.voice.console.ConnectionState
import cz.mia.app.core.voice.console.ConsoleCommand
import cz.mia.app.core.voice.console.VerbosityLevel
import cz.mia.app.core.voice.console.VoiceConsoleState

/**
 * MIA's voice settings as the Pi reports them (ADR-0019): verbosity, persona and language (REQ-AND-017). The
 * persona and language chips are drawn from what this Pi offers, so a new persona package needs no app change.
 * A chip only asks; the selection moves when the Pi reports the change.
 */
@Composable
fun VoiceSettingsSection(state: VoiceConsoleState, onPress: (ConsoleCommand) -> Boolean, modifier: Modifier = Modifier) {
    val connected = state.connection == ConnectionState.CONNECTED
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Verbosity (from the Pi)", style = MaterialTheme.typography.titleMedium)
        if (state.verbosity == null) {
            Text("not reported", style = MaterialTheme.typography.bodySmall, modifier = Modifier.testTag("voice_verbosity_unknown"))
        }
        ChipRow {
            VerbosityLevel.values().forEach { level ->
                val name = level.name.lowercase()
                FilterChip(
                    selected = state.verbosity == level,
                    onClick = { onPress(ConsoleCommand.SetVerbosity(level)) },
                    enabled = connected,
                    label = { Text(name) },
                    modifier = Modifier.testTag("voice_verbosity_$name"),
                )
            }
        }

        Text("Persona", style = MaterialTheme.typography.titleMedium)
        if (state.personas.isEmpty()) {
            Text("not reported", style = MaterialTheme.typography.bodySmall, modifier = Modifier.testTag("voice_persona_unknown"))
        }
        ChipRow {
            state.personas.forEach { persona ->
                FilterChip(
                    selected = state.persona == persona,
                    onClick = { onPress(ConsoleCommand.SwitchPersona(persona)) },
                    enabled = connected,
                    label = { Text(displayName(persona)) },
                    modifier = Modifier.testTag("voice_persona_$persona"),
                )
            }
        }

        Text("Language MIA speaks", style = MaterialTheme.typography.titleMedium)
        if (state.languages.isEmpty()) {
            Text("not reported", style = MaterialTheme.typography.bodySmall, modifier = Modifier.testTag("voice_language_unknown"))
        }
        ChipRow {
            state.languages.forEach { language ->
                FilterChip(
                    selected = state.language == language,
                    onClick = { onPress(ConsoleCommand.SetLanguage(language)) },
                    enabled = connected,
                    label = { Text(LANGUAGE_NAMES[language] ?: language) },
                    modifier = Modifier.testTag("voice_language_$language"),
                )
            }
        }
        Text(
            "Spoken commands stay English for now; the language changes only what MIA says.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun ChipRow(content: @Composable () -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
        content()
    }
}

private val LANGUAGE_NAMES = mapOf("cs" to "Čeština", "en" to "English")

/** `mia` is MIA's own voice; a persona package's name is shown capitalised. */
internal fun displayName(persona: String): String =
    if (persona == "mia") "MIA" else persona.replaceFirstChar { it.uppercase() }
