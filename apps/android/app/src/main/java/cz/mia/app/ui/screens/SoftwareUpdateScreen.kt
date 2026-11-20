package cz.mia.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.update.UpdateConfig
import cz.mia.app.core.update.UpdateProgress
import cz.mia.app.core.update.UpdateViewModel

/**
 * Settings > Software update (ADR-0023, REQ-UPD-007): edit the configuration, pair once, then build and send the
 * update. After a config edit the screen offers to update the Pi, because the config only reaches it that way.
 */
@Composable
fun SoftwareUpdateScreen(onBack: () -> Unit, modifier: Modifier = Modifier) {
	val vm: UpdateViewModel = hiltViewModel()
	val state by vm.state.collectAsState()
	val config = state.config
	var name by remember(config) { mutableStateOf(config.deviceName.orEmpty()) }
	var level by remember(config) { mutableStateOf(config.logLevel.orEmpty()) }
	var retention by remember(config) { mutableStateOf(config.logRetentionDays?.toString().orEmpty()) }
	var interval by remember(config) { mutableStateOf(config.telemetryIntervalMs?.toString().orEmpty()) }
	val busy = state.progress is UpdateProgress.Working

	Column(
		modifier = modifier.verticalScroll(rememberScrollState()).padding(16.dp),
		verticalArrangement = Arrangement.spacedBy(12.dp),
	) {
		OutlinedButton(onClick = onBack) { Text("Back to Settings") }
		Text("Software update", style = MaterialTheme.typography.headlineSmall)
		Text("Updates a Pi that is already installed. Needs the Pi's admin API key (Settings) and a Wi-Fi, LAN or USB-tether link to it.")

		Text("Configuration", style = MaterialTheme.typography.titleMedium)
		OutlinedTextField(name, { name = it }, label = { Text("Device name") }, modifier = Modifier.fillMaxWidth())
		OutlinedTextField(level, { level = it }, label = { Text("Log level (${UpdateConfig.LEVELS.joinToString("/")})") }, modifier = Modifier.fillMaxWidth())
		OutlinedTextField(retention, { retention = it }, label = { Text("Log retention days (1-90)") }, modifier = Modifier.fillMaxWidth())
		OutlinedTextField(interval, { interval = it }, label = { Text("Telemetry interval ms (100-60000)") }, modifier = Modifier.fillMaxWidth())
		Button(
			enabled = !busy,
			onClick = {
				vm.saveConfig(
					UpdateConfig(
						deviceName = name.trim().ifEmpty { null },
						logLevel = level.trim().ifEmpty { null },
						logRetentionDays = retention.trim().toIntOrNull(),
						telemetryIntervalMs = interval.trim().toIntOrNull(),
					)
				)
			},
		) { Text("Save configuration") }

		Text("Release", style = MaterialTheme.typography.titleMedium)
		OutlinedTextField(state.version, vm::setVersion, label = { Text("Version to install") }, modifier = Modifier.fillMaxWidth())
		Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
			OutlinedButton(enabled = !busy, onClick = vm::pair) { Text("Pair with the Pi") }
			Button(enabled = !busy, onClick = vm::update) { Text("Update the Pi") }
		}
		if (state.configChanged) {
			Text("Configuration changed. Update the Pi to apply it.", color = MaterialTheme.colorScheme.primary)
		}
		state.message?.let { Text(it) }
		when (val p = state.progress) {
			is UpdateProgress.Idle -> Unit
			is UpdateProgress.Working -> {
				Text(p.what)
				if (p.fraction != null) LinearProgressIndicator(progress = { p.fraction }, modifier = Modifier.fillMaxWidth())
				else LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
			}
			is UpdateProgress.Finished -> {
				val r = p.result
				if (r.ok) Text("Updated to ${r.version}. The Pi restarted its services.")
				else Text("Failed at step ${r.step}: ${r.error}", color = MaterialTheme.colorScheme.error)
				Text("Roll back on the Pi: sudo /opt/mia/bin/mia-apply-update --rollback")
			}
		}
	}
}
