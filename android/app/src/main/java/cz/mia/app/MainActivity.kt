package cz.mia.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarDefaults
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.background.DrivingService
import cz.mia.app.core.background.SamplingMode
import cz.mia.app.data.db.AlertEntity
import cz.mia.app.data.db.AnprEventEntity
import cz.mia.app.data.db.ClipEntity
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.features.alerts.AlertsViewModel
import cz.mia.app.features.anpr.AnprViewModel
import cz.mia.app.features.clips.ClipsViewModel
import cz.mia.app.features.dashboard.DashboardViewModel
import cz.mia.app.features.dashboard.PolicyViewModel
import cz.mia.app.features.settings.SettingsViewModel
import cz.mia.app.ui.components.DashboardGauges
import cz.mia.app.ui.screens.CameraPreviewScreen
import cz.mia.app.ui.screens.OBDPairingScreen
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
	override fun onCreate(savedInstanceState: Bundle?) {
		super.onCreate(savedInstanceState)
		setContent { AppRoot() }
	}

	private fun startDrivingService() {
		val intent = Intent(this, DrivingService::class.java).apply { action = DrivingService.ACTION_START }
		startForegroundService(intent)
	}

	private fun stopDrivingService() {
		val intent = Intent(this, DrivingService::class.java).apply { action = DrivingService.ACTION_STOP }
		startService(intent)
	}

	@OptIn(ExperimentalMaterial3Api::class)
	@Composable
	private fun AppRoot() {
		var selected by remember { mutableStateOf(0) }
		val snackbarHostState: SnackbarHostState = remember { SnackbarHostState() }
		Scaffold(
			snackbarHost = { SnackbarHost(snackbarHostState) },
			bottomBar = {
				NavigationBar {
					NavigationBarItem(
						selected = selected == 0,
						onClick = { selected = 0 },
						icon = { Icon(Icons.Default.Dashboard, contentDescription = null) },
						label = { Text("Dashboard") }
					)
					NavigationBarItem(
						selected = selected == 1,
						onClick = { selected = 1 },
						icon = { Icon(Icons.Default.Warning, contentDescription = null) },
						label = { Text("Alerts") }
					)
					NavigationBarItem(
						selected = selected == 2,
						onClick = { selected = 2 },
						icon = { Icon(Icons.Default.CameraAlt, contentDescription = null) },
						label = { Text("Camera") }
					)
					NavigationBarItem(
						selected = selected == 3,
						onClick = { selected = 3 },
						icon = { Icon(Icons.Default.Bluetooth, contentDescription = null) },
						label = { Text("OBD") }
					)
					NavigationBarItem(
						selected = selected == 4,
						onClick = { selected = 4 },
						icon = { Icon(Icons.Default.Settings, contentDescription = null) },
						label = { Text("Settings") }
					)
				}
			}
		) { padding ->
			when (selected) {
				0 -> DashboardScreen(Modifier.padding(padding))
				1 -> AlertsScreen(Modifier.padding(padding))
				2 -> CameraPreviewScreen(Modifier.padding(padding))
				3 -> OBDPairingScreen(Modifier.padding(padding))
				else -> SettingsScreen(Modifier.padding(padding))
			}
		}
	}

	@Composable
	private fun DashboardScreen(modifier: Modifier = Modifier) {
		val vm: DashboardViewModel = hiltViewModel()
		val policyVm: PolicyViewModel = hiltViewModel()
		val latest = vm.latest.value
		val policy = policyVm.state.value
		var isServiceRunning by remember { mutableStateOf(false) }
		
		Column(modifier = modifier.fillMaxSize().padding(16.dp)) {
			Text(
				text = "Dashboard",
				style = MaterialTheme.typography.headlineMedium
			)
			
			Spacer(Modifier.height(8.dp))
			
			PolicyAdvisory(policy.advisoryMessage, policy.samplingMode.name, policy.batteryPercent)
			
			Spacer(Modifier.height(16.dp))
			
			DashboardGauges(latest)

			Spacer(Modifier.height(16.dp))

			// Citroën C4 specific controls
			CitroenControls(latest)

			Spacer(Modifier.height(16.dp))

			// Service control buttons
			Row(
				modifier = Modifier.fillMaxWidth(),
				horizontalArrangement = Arrangement.spacedBy(8.dp)
			) {
				Button(
					onClick = { 
						startDrivingService()
						isServiceRunning = true
					},
					enabled = !isServiceRunning,
					modifier = Modifier.weight(1f),
					colors = ButtonDefaults.buttonColors(
						containerColor = MaterialTheme.colorScheme.primary
					)
				) { 
					Icon(Icons.Default.PlayArrow, contentDescription = null)
					Spacer(Modifier.width(4.dp))
					Text("Start Service") 
				}
				
				OutlinedButton(
					onClick = { 
						stopDrivingService()
						isServiceRunning = false
					},
					enabled = isServiceRunning,
					modifier = Modifier.weight(1f),
					colors = ButtonDefaults.outlinedButtonColors(
						contentColor = Color.Red
					)
				) {
					Icon(Icons.Default.Stop, contentDescription = null)
					Spacer(Modifier.width(4.dp))
					Text("Stop Service") 
				}
			}
		}
	}

	@Composable
	private fun TelemetrySummary(latest: TelemetryEntity?) {
		if (latest == null) {
			Text("No telemetry yet")
		} else {
			Column {
				Text("Fuel: ${latest.fuelLevel}%  RPM: ${latest.engineRpm}  Speed: ${latest.vehicleSpeed} km/h  Coolant: ${latest.coolantTemp}°C")

				// Citroën C4 specific telemetry
				if (latest.dpfSootMass != null || latest.adBlueLevel != null || latest.dpfStatus != null) {
					Spacer(Modifier.height(8.dp))
					Text("Citroën C4 Diagnostics:", style = MaterialTheme.typography.titleSmall)

					if (latest.dpfSootMass != null) {
						Text("DPF Soot: ${String.format("%.1f", latest.dpfSootMass)}g")
					}
					if (latest.adBlueLevel != null) {
						Text("AdBlue Level: ${latest.adBlueLevel}%")
					}
					if (latest.dpfStatus != null) {
						Text("DPF Status: ${latest.dpfStatus}")
					}
					if (latest.particulateFilterEfficiency != null) {
						Text("Filter Efficiency: ${latest.particulateFilterEfficiency}%")
					}
				}
			}
		}
	}

	@Composable
	private fun AlertsScreen(modifier: Modifier = Modifier) {
		val vm: AlertsViewModel = hiltViewModel()
		LazyColumn(modifier = modifier.fillMaxSize().padding(16.dp)) {
			items(vm.recent.value) { alert: AlertEntity ->
				Text("[${alert.severity}] ${alert.message}")
			}
		}
	}

	@Composable
	private fun AnprScreen(modifier: Modifier = Modifier) {
		val vm: AnprViewModel = hiltViewModel()
		LazyColumn(modifier = modifier.fillMaxSize().padding(16.dp)) {
			items(vm.recent.value) { ev: AnprEventEntity ->
				Text("ANPR: ${ev.plateHash.take(8)}…  conf=${ev.confidence}")
			}
		}
	}

	@Composable
	private fun ClipsScreen(modifier: Modifier = Modifier) {
		val vm: ClipsViewModel = hiltViewModel()
		val clips by vm.clips.collectAsState(initial = emptyList())
		LazyColumn(modifier = modifier.fillMaxSize().padding(16.dp)) {
			items(clips) { clip: ClipEntity ->
				Text("Clip: ${clip.reason}  ${clip.filePath}  offloaded=${clip.offloaded}")
			}
		}
	}

	@Composable
	private fun SettingsScreen(modifier: Modifier = Modifier) {
		val vm: SettingsViewModel = hiltViewModel()
		val currentVin = vm.vin.value
		var vinText by remember(currentVin) { mutableStateOf(currentVin) }
		val incognito = vm.incognito.value
		val retention = vm.retentionDays.value.toFloat()
		val metrics = vm.metricsOptIn.value
		val region = vm.anprRegion.value
		var lastExportPath by remember { mutableStateOf("") }

		Column(modifier = modifier.padding(16.dp)) {
			Text(text = "Settings")
			Spacer(modifier = Modifier.height(12.dp))
			OutlinedTextField(value = vinText, onValueChange = { vinText = it }, label = { Text("VIN") })
			Spacer(modifier = Modifier.height(8.dp))
			Button(onClick = { vm.setVin(vinText) }) { Text("Save VIN") }
			Spacer(modifier = Modifier.height(16.dp))
			Text("Incognito")
			Switch(checked = incognito, onCheckedChange = { vm.setIncognito(it) })
			Spacer(modifier = Modifier.height(8.dp))
			Text("Retention: ${retention.toInt()} days")
			Slider(value = retention, onValueChange = { vm.setRetentionDays(it.toInt()) }, valueRange = 1f..30f)
			Spacer(Modifier.height(16.dp))
			Text("Metrics opt-in (health pings)")
			Switch(checked = metrics, onCheckedChange = { vm.setMetricsOptIn(it) })
			Spacer(Modifier.height(16.dp))
			Text("ANPR Region: ${region}")
			RowToggle(options = listOf("CZ", "EU"), selected = region, onSelected = { vm.setAnprRegion(it) })
			Spacer(Modifier.height(16.dp))
			Button(onClick = {
				vm.exportLogs { file -> lastExportPath = file.absolutePath }
			}) { Text("Export Logs") }
			if (lastExportPath.isNotEmpty()) {
				Spacer(Modifier.height(8.dp))
				Text("Exported: ${lastExportPath}")
			}
		}
	}
}
@Composable
private fun PolicyAdvisory(message: String?, mode: String, battery: Int) {
	if (!message.isNullOrBlank()) {
		Snackbar(
			shape = SnackbarDefaults.shape,
			action = { Text("Mode: ${mode}") }
		) {
			Text("${message}  •  Battery ${battery}%")
		}
	}
}


@Composable
private fun CitroenControls(latest: TelemetryEntity?) {
	val snackbarHostState: SnackbarHostState = remember { SnackbarHostState() }

	Column(modifier = Modifier.fillMaxWidth()) {
		Text("Citroën C4 Controls", style = MaterialTheme.typography.titleMedium)

		Spacer(Modifier.height(8.dp))

		// DPF Controls
		if (latest?.dpfSootMass != null) {
			Text("DPF Management", style = MaterialTheme.typography.titleSmall)
			Spacer(Modifier.height(4.dp))

			Row(
				modifier = Modifier.fillMaxWidth(),
				horizontalArrangement = Arrangement.spacedBy(8.dp)
			) {
				OutlinedButton(
					onClick = {
						// TODO: Implement DPF status check via MCP bridge
						// This would send command to automotive-mcp-bridge
					},
					modifier = Modifier.weight(1f)
				) {
					Icon(Icons.Default.Info, contentDescription = null)
					Spacer(Modifier.width(8.dp))
					Text("Check DPF")
				}

				Button(
					onClick = {
						// TODO: Implement DPF regeneration via MCP bridge
						// This would send regeneration command to citroen-c4-bridge
					},
					modifier = Modifier.weight(1f),
					enabled = latest?.dpfStatus == "ok" || latest?.dpfStatus == "warning",
					colors = ButtonDefaults.buttonColors(
						containerColor = Color(0xFF4CAF50) // Green for regeneration
					)
				) {
					Icon(Icons.Default.Refresh, contentDescription = null)
					Spacer(Modifier.width(8.dp))
					Text("Regenerate")
				}
			}

			Spacer(Modifier.height(8.dp))
		}

		// AdBlue Controls
		if (latest?.adBlueLevel != null) {
			Text("AdBlue System", style = MaterialTheme.typography.titleSmall)
			Spacer(Modifier.height(4.dp))

			OutlinedButton(
				onClick = {
					// TODO: Implement AdBlue status check via MCP bridge
				},
				modifier = Modifier.fillMaxWidth()
			) {
				Icon(Icons.Default.LocalGasStation, contentDescription = null)
				Spacer(Modifier.width(8.dp))
				Text("Check AdBlue Level (${latest.adBlueLevel}%)")
			}

			Spacer(Modifier.height(8.dp))
		}

		// Diagnostics
		Text("Diagnostics", style = MaterialTheme.typography.titleSmall)
		Spacer(Modifier.height(4.dp))

		Row(
			modifier = Modifier.fillMaxWidth(),
			horizontalArrangement = Arrangement.spacedBy(8.dp)
		) {
			OutlinedButton(
				onClick = {
					// TODO: Implement full diagnostics via MCP bridge
					// This would run comprehensive vehicle health check
				},
				modifier = Modifier.weight(1f)
			) {
				Icon(Icons.Default.Build, contentDescription = null)
				Spacer(Modifier.width(8.dp))
				Text("Run Diag")
			}

			OutlinedButton(
				onClick = {
					// TODO: Implement DTC code reading via MCP bridge
				},
				modifier = Modifier.weight(1f)
			) {
				Icon(Icons.Default.Warning, contentDescription = null)
				Spacer(Modifier.width(8.dp))
				Text("Check DTC")
			}
		}
	}
}

@Composable
private fun RowToggle(options: List<String>, selected: String, onSelected: (String) -> Unit) {
	Row(
		horizontalArrangement = Arrangement.spacedBy(8.dp)
	) {
		options.forEach { opt ->
			Button(
				onClick = { onSelected(opt) },
				enabled = opt != selected
			) {
				Text(opt)
			}
		}
	}
}
