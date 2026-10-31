package cz.mia.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.foundation.background
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.background.DrivingService
import cz.mia.app.core.background.SamplingMode
import cz.mia.app.data.db.AlertEntity
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.features.alerts.AlertsViewModel
import cz.mia.app.features.dashboard.DashboardViewModel
import cz.mia.app.features.dashboard.PolicyViewModel
import cz.mia.app.features.settings.SettingsViewModel
import cz.mia.app.features.led.LEDMonitorViewModel
import cz.mia.app.features.voice.VoiceConsoleViewModel
import cz.mia.app.core.voice.console.ConnectionState
import cz.mia.app.ui.components.VoiceSettingsSection
import cz.mia.app.ui.components.CitroenReadings
import cz.mia.app.ui.components.Cycle1TelemetryCard
import cz.mia.app.ui.components.AlertRow
import cz.mia.app.ui.components.DashboardTelemetrySection
import cz.mia.app.ui.components.ScreenTitle
import cz.mia.app.ui.components.SectionCard
import cz.mia.app.ui.screens.MoreDestination
import cz.mia.app.ui.screens.MoreScreen
import cz.mia.app.ui.theme.MiaTheme
import cz.mia.app.ui.theme.mia
import cz.mia.app.ui.screens.camera.CameraScreen
import cz.mia.app.ui.screens.OBDPairingScreen
import cz.mia.app.ui.screens.VoiceConsoleScreen
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
	override fun onCreate(savedInstanceState: Bundle?) {
		super.onCreate(savedInstanceState)
		setContent { MiaTheme { AppRoot() } }
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
		var selected by rememberSaveable { mutableStateOf(0) }
		var moreDestination by rememberSaveable { mutableStateOf<MoreDestination?>(null) }
		val snackbarHostState: SnackbarHostState = remember { SnackbarHostState() }
		Scaffold(
			snackbarHost = { SnackbarHost(snackbarHostState) },
			bottomBar = {
				NavigationBar {
					NavTab(selected == 0, Icons.Default.Dashboard, "Dashboard") { selected = 0 }
					NavTab(selected == 1, Icons.Default.CameraAlt, "Camera") { selected = 1 }
					NavTab(selected == 2, Icons.Default.Mic, "Voice") { selected = 2 }
					NavTab(selected == 3, Icons.Default.Lightbulb, "LED") { selected = 3 }
					// Tapping More again returns to its list.
					NavTab(selected == 4, Icons.Default.MoreHoriz, "More") {
						selected = 4
						moreDestination = null
					}
				}
			}
		) { padding ->
			when (selected) {
				0 -> DashboardScreen(Modifier.padding(padding))
				1 -> CameraScreen(Modifier.padding(padding))
				2 -> VoiceConsoleScreen(Modifier.padding(padding))
				3 -> LEDMonitorScreen(Modifier.padding(padding))
				else -> MoreScreen(
					current = moreDestination,
					onSelect = { moreDestination = it },
					modifier = Modifier.padding(padding),
				) { destination, inner ->
					when (destination) {
						MoreDestination.Alerts -> AlertsScreen(inner)
						MoreDestination.ObdPairing -> OBDPairingScreen(inner)
						MoreDestination.Settings -> SettingsScreen(inner)
					}
				}
			}
		}
	}

	@Composable
	private fun RowScope.NavTab(selected: Boolean, icon: ImageVector, label: String, onClick: () -> Unit) {
		NavigationBarItem(
			selected = selected,
			onClick = onClick,
			icon = { Icon(icon, contentDescription = null) },
			label = { Text(label, maxLines = 1, softWrap = false) },
			modifier = Modifier.heightIn(min = 64.dp),
		)
	}

	@Composable
	private fun DashboardScreen(modifier: Modifier = Modifier) {
		val vm: DashboardViewModel = hiltViewModel()
		val policyVm: PolicyViewModel = hiltViewModel()
		val latest = vm.latest.value
		val cycle1Telemetry by vm.cycle1Telemetry.collectAsState()
		val cycle1Connection by vm.cycle1Connection.collectAsState()
		val policy = policyVm.state.value
		var isServiceRunning by remember { mutableStateOf(false) }

		LaunchedEffect(Unit) {
			vm.initializeCycle1Telemetry()
		}
		
		// Scrollable so the Cycle 1 card below the service controls stays reachable on small screens.
		Column(modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
			ScreenTitle("Dashboard")
			
			PolicyAdvisory(policy.advisoryMessage, policy.samplingMode.name, policy.batteryPercent)
			
			Spacer(Modifier.height(16.dp))
			
			// One status chip; the gauges' "No telemetry data" placeholder is skipped while live Cycle 1 data exists.
			DashboardTelemetrySection(
				latest = latest,
				cycle1Telemetry = cycle1Telemetry,
				cycle1Connection = cycle1Connection,
			)

			Spacer(Modifier.height(16.dp))

			// Citroën C4 readings: text only, nothing is shown when the Pi sends none (ADR-0006)
			CitroenReadings(latest)

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
						contentColor = MaterialTheme.colorScheme.error
					)
				) {
					Icon(Icons.Default.Stop, contentDescription = null)
					Spacer(Modifier.width(4.dp))
					Text("Stop Service") 
				}
			}

			Spacer(Modifier.height(16.dp))

			Cycle1TelemetryCard(
				telemetry = cycle1Telemetry,
				connection = cycle1Connection,
			)
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
		val alerts = vm.recent.value
		Column(modifier = modifier.fillMaxSize().padding(horizontal = 16.dp)) {
			ScreenTitle("Alerts")
			if (alerts.isEmpty()) {
				SectionCard { Text("No alerts yet.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
			} else {
				LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
					items(alerts) { alert: AlertEntity ->
						AlertRow(severity = alert.severity, message = alert.message)
					}
				}
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
		val savedPiAddress = vm.piAddress.collectAsState().value
		val savedPiApiKey = vm.piApiKey.collectAsState().value
		var piAddressText by remember(savedPiAddress) { mutableStateOf(savedPiAddress) }
		var piApiKeyText by remember(savedPiApiKey) { mutableStateOf(savedPiApiKey) }
		var piAddressError by remember { mutableStateOf<String?>(null) }
		var lastExportPath by remember { mutableStateOf("") }

		Column(
			modifier = modifier.verticalScroll(rememberScrollState()).padding(16.dp),
			verticalArrangement = Arrangement.spacedBy(12.dp),
		) {
			ScreenTitle("Settings")
			SectionCard(title = "Vehicle") {
			OutlinedTextField(value = vinText, onValueChange = { vinText = it }, label = { Text("VIN") })
			Button(onClick = { vm.setVin(vinText) }) { Text("Save VIN") }
			}
			SectionCard(title = "Privacy") {
			Text("Incognito")
			Switch(checked = incognito, onCheckedChange = { vm.setIncognito(it) })
			Text("Retention: ${retention.toInt()} days")
			Slider(value = retention, onValueChange = { vm.setRetentionDays(it.toInt()) }, valueRange = 1f..30f)
			Text("Metrics opt-in (health pings)")
			Switch(checked = metrics, onCheckedChange = { vm.setMetricsOptIn(it) })
			}
			SectionCard(title = "ANPR") {
			Text("ANPR Region: ${region}")
			RowToggle(options = listOf("CZ", "EU"), selected = region, onSelected = { vm.setAnprRegion(it) })
			}
			SectionCard(title = "Pi connection") {
			OutlinedTextField(
				value = piAddressText,
				onValueChange = { piAddressText = it; piAddressError = null },
				label = { Text("Pi address (blank = build default)") },
				placeholder = { Text("192.168.1.50 or pi.local:8000") },
				singleLine = true,
				isError = piAddressError != null,
				supportingText = piAddressError?.let { message -> { Text(message) } }
			)
			OutlinedTextField(
				value = piApiKeyText,
				onValueChange = { piApiKeyText = it },
				label = { Text("API key") },
				singleLine = true,
				visualTransformation = PasswordVisualTransformation()
			)
			Button(onClick = { piAddressError = vm.savePiConnection(piAddressText, piApiKeyText) }) {
				Text("Save connection")
			}
			val active = vm.preview(savedPiAddress, savedPiApiKey)
			Text("Using: ${active.apiBaseUrl} (API key ${if (active.apiKey.isBlank()) "none" else "set"})")
			Text("Takes effect when you open Dashboard, LED or Voice next.")
			}
			SectionCard(title = "Logs") {
			Button(onClick = {
				vm.exportLogs { file -> lastExportPath = file.absolutePath }
			}) { Text("Export Logs") }
			if (lastExportPath.isNotEmpty()) {
				Text("Exported: ${lastExportPath}")
			}
			}
			SectionCard { VoiceSettings() }
		}
	}

	/** MIA's voice settings live on the Pi (ADR-0019); this asks the voice console for them. */
	@Composable
	private fun VoiceSettings() {
		val voiceVm: VoiceConsoleViewModel = hiltViewModel()
		val voice by voiceVm.state.collectAsState()
		var wanted by remember { mutableStateOf(false) }
		DisposableEffect(voiceVm, wanted) {
			if (wanted) voiceVm.start()
			onDispose { if (wanted) voiceVm.stop() }
		}
		Text("MIA's voice", style = MaterialTheme.typography.titleLarge)
		if (voice.connection != ConnectionState.CONNECTED) {
			Text("Read from the Pi's voice console when connected.")
			OutlinedButton(onClick = { wanted = true }, enabled = voice.connection == ConnectionState.DISCONNECTED) {
				Text(if (voice.connection == ConnectionState.CONNECTING) "Connecting..." else "Connect")
			}
		}
		Spacer(Modifier.height(8.dp))
		VoiceSettingsSection(voice, voiceVm::press)
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
private fun LEDMonitorScreen(modifier: Modifier = Modifier) {
	val dashboardVm: DashboardViewModel = hiltViewModel()
	val ledVm: LEDMonitorViewModel = hiltViewModel()
	val latest = dashboardVm.latest.value

	// Initialize WebSocket connection
	androidx.compose.runtime.LaunchedEffect(Unit) {
		ledVm.initializeWebSocket()
	}

	val ledState by ledVm.ledState.collectAsState()
	val serviceStatuses by ledVm.serviceStatuses.collectAsState()
	val wsState by ledVm.webSocketState.collectAsState()

	// Use WebSocket data if available, otherwise use local state
	var selectedMode by remember(ledState?.mode) { mutableStateOf(ledState?.mode ?: "Drive") }
	var aiState by remember(ledState?.aiState) { mutableStateOf(ledState?.aiState ?: "idle") }
	var brightness by remember(ledState?.brightness) { mutableStateOf(ledState?.brightness ?: 0.7f) }
	var emergencyOverride by remember(ledState?.emergency) { mutableStateOf(ledState?.emergency ?: false) }

	Column(modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
		ScreenTitle("LED Monitor Control")

		// WebSocket connection status
		Text(
			text = "WebSocket: ${wsState::class.simpleName}",
			style = MaterialTheme.typography.bodySmall,
			color = when (wsState) {
				is cz.mia.app.data.remote.websocket.WebSocketState.Connected -> MaterialTheme.mia.success
				is cz.mia.app.data.remote.websocket.WebSocketState.Error -> MaterialTheme.colorScheme.error
				else -> MaterialTheme.colorScheme.onSurfaceVariant
			}
		)

		Spacer(Modifier.height(16.dp))

		// Service Health Dashboard
		SectionCard { ServiceHealthDashboard(serviceStatuses) }

		Spacer(Modifier.height(16.dp))

		// LED Status Visualization
		SectionCard { LEDStatusVisualization(aiState, selectedMode, brightness, emergencyOverride) }

		Spacer(Modifier.height(16.dp))

		// Control Interface
		SectionCard {
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
		}

		Spacer(Modifier.height(16.dp))

		// Real-time OBD Data Display
		SectionCard { OBDDataDisplay(latest, ledState?.obdData) }

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
	val color = if (isHealthy) MaterialTheme.mia.success else MaterialTheme.colorScheme.error
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
					checkedThumbColor = MaterialTheme.colorScheme.error,
					checkedTrackColor = MaterialTheme.colorScheme.error.copy(alpha = 0.5f)
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
		Text(value, style = MaterialTheme.typography.titleMedium.copy(fontFamily = cz.mia.app.ui.theme.MiaMono, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold))
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
			tint = if (heartbeat) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
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
