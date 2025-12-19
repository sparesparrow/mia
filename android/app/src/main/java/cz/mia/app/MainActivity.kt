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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.foundation.background
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
import cz.mia.app.features.led.LEDMonitorViewModel
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
						icon = { Icon(Icons.Default.Lightbulb, contentDescription = null) },
						label = { Text("LED") }
					)
					NavigationBarItem(
						selected = selected == 5,
						onClick = { selected = 5 },
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
				4 -> LEDMonitorScreen(Modifier.padding(padding))
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
private fun LEDMonitorScreen(modifier: Modifier = Modifier) {
	val dashboardVm: DashboardViewModel = hiltViewModel()
	val ledVm: LEDMonitorViewModel = hiltViewModel()
	val latest = dashboardVm.latest.value

	// Initialize WebSocket connection
	androidx.compose.runtime.LaunchedEffect(Unit) {
		// TODO: Get base URL from settings/preferences
		// Changed from Android emulator (10.0.2.2) to Raspberry Pi IP
		// Replace with actual Raspberry Pi IP address on the same network
		ledVm.initializeWebSocket("ws://192.168.1.100:8000") // Raspberry Pi default
	}

	val ledState by ledVm.ledState.collectAsState()
	val serviceStatuses by ledVm.serviceStatuses.collectAsState()
	val wsState by ledVm.webSocketState.collectAsState()

	// Use WebSocket data if available, otherwise use local state
	var selectedMode by remember(ledState?.mode) { mutableStateOf(ledState?.mode ?: "Drive") }
	var aiState by remember(ledState?.aiState) { mutableStateOf(ledState?.aiState ?: "idle") }
	var brightness by remember(ledState?.brightness) { mutableStateOf(ledState?.brightness ?: 0.7f) }
	var emergencyOverride by remember(ledState?.emergency) { mutableStateOf(ledState?.emergency ?: false) }

	Column(modifier = modifier.fillMaxSize().padding(16.dp)) {
		Text(
			text = "LED Monitor Control",
			style = MaterialTheme.typography.headlineMedium
		)

		// WebSocket connection status
		Text(
			text = "WebSocket: ${wsState::class.simpleName}",
			style = MaterialTheme.typography.bodySmall,
			color = when (wsState) {
				is cz.mia.app.data.remote.websocket.WebSocketState.Connected -> Color.Green
				is cz.mia.app.data.remote.websocket.WebSocketState.Error -> Color.Red
				else -> Color.Gray
			}
		)

		Spacer(Modifier.height(16.dp))

		// Service Health Dashboard
		ServiceHealthDashboard(serviceStatuses)

		Spacer(Modifier.height(16.dp))

		// LED Status Visualization
		LEDStatusVisualization(aiState, selectedMode, brightness, emergencyOverride)

		Spacer(Modifier.height(16.dp))

		// Control Interface
		LEDControlInterface(
			selectedMode = selectedMode,
			onModeChange = {
				selectedMode = it
				// Send mode command to Raspberry Pi
				when (it.lowercase()) {
					"drive" -> ledVm.setDriveMode()
					"parked" -> ledVm.setParkedMode()
					"night" -> ledVm.setNightMode()
					"service" -> ledVm.setServiceMode()
				}
			},
			aiState = aiState,
			onAiStateChange = {
				aiState = it
				// Send AI state command to Raspberry Pi
				ledVm.setAiState(it)
			},
			brightness = brightness,
			onBrightnessChange = {
				brightness = it
				// Send brightness command to Raspberry Pi
				ledVm.setLedBrightness((it * 255).toInt())
			},
			emergencyOverride = emergencyOverride,
			onEmergencyOverride = {
				emergencyOverride = it
				// Send emergency command to Raspberry Pi
				if (it) {
					ledVm.triggerEmergency()
				} else {
					ledVm.clearEmergency()
				}
			}
		)

		Spacer(Modifier.height(16.dp))

		// Real-time OBD Data Display
		OBDDataDisplay(latest, ledState?.obdData)

		Spacer(Modifier.height(16.dp))

		// System Heartbeat
		SystemHeartbeat()
	}
}

@Composable
private fun ServiceHealthDashboard(serviceStatuses: Map<String, Boolean>) {
	Column(modifier = Modifier.fillMaxWidth()) {
		Text("Service Health", style = MaterialTheme.typography.titleMedium)
		Spacer(Modifier.height(8.dp))

		Row(
			modifier = Modifier.fillMaxWidth(),
			horizontalArrangement = Arrangement.spacedBy(8.dp)
		) {
			serviceStatuses.forEach { (service, isHealthy) ->
				ServiceStatusIndicator(service, isHealthy)
			}
		}
	}
}

@Composable
private fun ServiceStatusIndicator(service: String, isHealthy: Boolean) {
	val color = if (isHealthy) Color.Green else Color.Red
	val icon = if (isHealthy) Icons.Default.CheckCircle else Icons.Default.Error

	Column(
		horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
		modifier = Modifier.width(48.dp)
	) {
		Icon(
			icon,
			contentDescription = "$service status",
			tint = color,
			modifier = Modifier.size(24.dp)
		)
		Text(
			service,
			style = MaterialTheme.typography.bodySmall,
			textAlign = androidx.compose.ui.text.style.TextAlign.Center
		)
	}
}

@Composable
private fun LEDStatusVisualization(aiState: String, mode: String, brightness: Float, emergency: Boolean) {
	Column(modifier = Modifier.fillMaxWidth()) {
		Text("LED Status", style = MaterialTheme.typography.titleMedium)
		Spacer(Modifier.height(8.dp))

		// Visual LED strip representation
		Row(
			modifier = Modifier
				.fillMaxWidth()
				.height(60.dp)
				.background(
					color = when {
						emergency -> Color.Red
						aiState == "listening" -> Color.Blue
						aiState == "speaking" -> Color.Green
						aiState == "thinking" -> Color.Yellow
						aiState == "recording" -> Color.Magenta
						aiState == "error" -> Color.Red
						else -> Color.Gray
					}.copy(alpha = brightness),
					shape = MaterialTheme.shapes.medium
				)
				.padding(8.dp),
			horizontalArrangement = Arrangement.Center,
			verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
		) {
			Text(
				text = "Mode: $mode | AI: $aiState",
				color = Color.White,
				style = MaterialTheme.typography.bodyMedium
			)
		}
	}
}

@Composable
private fun LEDControlInterface(
	selectedMode: String,
	onModeChange: (String) -> Unit,
	aiState: String,
	onAiStateChange: (String) -> Unit,
	brightness: Float,
	onBrightnessChange: (Float) -> Unit,
	emergencyOverride: Boolean,
	onEmergencyOverride: (Boolean) -> Unit
) {
	Column(modifier = Modifier.fillMaxWidth()) {
		Text("Controls", style = MaterialTheme.typography.titleMedium)
		Spacer(Modifier.height(8.dp))

		// Mode Selection
		Text("System Mode", style = MaterialTheme.typography.titleSmall)
		RowToggle(
			options = listOf("Drive", "Parked", "Night", "Service"),
			selected = selectedMode,
			onSelected = onModeChange
		)

		Spacer(Modifier.height(12.dp))

		// AI State Control
		Text("AI State", style = MaterialTheme.typography.titleSmall)
		RowToggle(
			options = listOf("idle", "listening", "speaking", "thinking", "recording"),
			selected = aiState,
			onSelected = onAiStateChange
		)

		Spacer(Modifier.height(12.dp))

		// Brightness Control
		Text("Brightness: ${(brightness * 100).toInt()}%", style = MaterialTheme.typography.titleSmall)
		Slider(
			value = brightness,
			onValueChange = onBrightnessChange,
			valueRange = 0f..1f,
			modifier = Modifier.fillMaxWidth()
		)

		Spacer(Modifier.height(12.dp))

		// Emergency Override
		Row(
			modifier = Modifier.fillMaxWidth(),
			horizontalArrangement = Arrangement.SpaceBetween,
			verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
		) {
			Text("Emergency Override", style = MaterialTheme.typography.titleSmall)
			Switch(
				checked = emergencyOverride,
				onCheckedChange = onEmergencyOverride,
				colors = androidx.compose.material3.SwitchDefaults.colors(
					checkedThumbColor = Color.Red,
					checkedTrackColor = Color.Red.copy(alpha = 0.5f)
				)
			)
		}
	}
}

@Composable
private fun OBDDataDisplay(latest: TelemetryEntity?, wsObdData: Map<String, Any>?) {
	Column(modifier = Modifier.fillMaxWidth()) {
		Text("OBD Data", style = MaterialTheme.typography.titleMedium)
		Spacer(Modifier.height(8.dp))

		val rpm = wsObdData?.get("rpm")?.toString() ?: latest?.engineRpm?.toString() ?: "N/A"
		val speed = wsObdData?.get("speed_kmh")?.toString() ?: latest?.vehicleSpeed?.toString() ?: "N/A"
		val temp = wsObdData?.get("coolant_temp_c")?.toString() ?: latest?.coolantTemp?.toString() ?: "N/A"
		val load = wsObdData?.get("engine_load_percent")?.toString() ?: latest?.engineLoad?.toString() ?: "N/A"

		Row(
			modifier = Modifier.fillMaxWidth(),
			horizontalArrangement = Arrangement.spacedBy(16.dp)
		) {
			OBDMetric("RPM", rpm)
			OBDMetric("Speed", if (speed != "N/A") "$speed km/h" else speed)
			OBDMetric("Temp", if (temp != "N/A") "$temp°C" else temp)
			OBDMetric("Load", if (load != "N/A") "$load%" else load)
		}
	}
}

@Composable
private fun OBDMetric(label: String, value: String) {
	Column(horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
		Text(value, style = MaterialTheme.typography.headlineSmall)
		Text(label, style = MaterialTheme.typography.bodySmall)
	}
}

@Composable
private fun SystemHeartbeat() {
	var heartbeat by remember { mutableStateOf(true) }

	// Simulate heartbeat animation
	androidx.compose.runtime.LaunchedEffect(Unit) {
		while (true) {
			kotlinx.coroutines.delay(1000)
			heartbeat = !heartbeat
		}
	}

	Row(
		modifier = Modifier.fillMaxWidth(),
		horizontalArrangement = Arrangement.Center,
		verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
	) {
		Icon(
			if (heartbeat) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
			contentDescription = "System heartbeat",
			tint = if (heartbeat) Color.Red else Color.Gray,
			modifier = Modifier.size(24.dp)
		)
		Spacer(Modifier.width(8.dp))
		Text("System Online", style = MaterialTheme.typography.bodyMedium)
	}
}

@Composable
private fun RowToggle(options: List<String>, selected: String, onSelected: (String) -> Unit) {
	Row(
		horizontalArrangement = Arrangement.spacedBy(8.dp)
	) {
		options.forEach { opt ->
			OutlinedButton(
				onClick = { onSelected(opt) },
				enabled = opt != selected,
				colors = ButtonDefaults.outlinedButtonColors(
					contentColor = if (opt == selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
				)
			) {
				Text(opt)
			}
		}
	}
}
