package cz.mia.app.ui.screens.vehicle

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.onboarding.AndroidSystemPairing
import cz.mia.app.core.onboarding.OnboardingState
import cz.mia.app.core.onboarding.OnboardingViewModel
import cz.mia.app.core.update.UpdateConfig
import cz.mia.app.ui.components.ScreenTitle
import cz.mia.app.ui.screens.OBDPairingScreen
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * More > Install MIA on a car (ADR-0025, REQ-ONB-008). Renders [OnboardingViewModel.state] only; the logic is the
 * ViewModel's machine. The activation key lives in a text field in memory and is cleared on submit; it is never saved,
 * shown again or put in a message.
 */
@Composable
fun InstallMiaScreen(modifier: Modifier = Modifier) {
	val vm: OnboardingViewModel = hiltViewModel()
	val state by vm.state.collectAsState()
	val notes by vm.notes.collectAsState()
	val problems by vm.formProblems.collectAsState()
	val issue by vm.pairingIssue.collectAsState()

	AttachSystemPairing(vm)

	val ui = uiModelFor(state)
	when (state) {
		OnboardingState.EnterActivationKey -> EnterActivationKey(ui, notes, onContinue = vm::submitActivationKey, modifier = modifier)
		OnboardingState.FirstSetup -> FirstSetup(ui, problems, notes, onInstall = vm::submitFirstSetup, modifier = modifier)
		OnboardingState.PairingPhone -> PairVehicleStep(
			ui, issue, notes,
			onPrimary = vm::resume,
			onSecondary = {},
			modifier = modifier.fillMaxSize().padding(16.dp),
		)
		OnboardingState.PairAdapter -> PairAdapter(ui, notes, onFinish = vm::finishAdapterStep, modifier = modifier)
		OnboardingState.Done -> Done(ui, notes, pis = remember { vm.knownPis().map { it.host } }, onAnother = vm::restart, modifier = modifier)
		else -> Plain(
			ui, notes,
			onPrimary = {
				when (state) {
					OnboardingState.Welcome -> vm.begin()
					is OnboardingState.Failed -> if ((state as OnboardingState.Failed).retryable) vm.retry() else vm.restart()
					else -> Unit
				}
			},
			onSecondary = vm::restart,
			modifier = modifier,
		)
	}
}

/** Gives the machine the Activity-bound Bluetooth and Wi-Fi dialogs while this screen shows, and takes them away after. */
@Composable
private fun AttachSystemPairing(vm: OnboardingViewModel) {
	val context = LocalContext.current
	val pending = remember { AtomicReference<CompletableDeferred<Boolean>?>(null) }
	val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
		pending.getAndSet(null)?.complete(granted)
	}
	val pairing = remember(context) {
		AndroidSystemPairing(
			context = context,
			requestConnectPermission = {
				val answer = CompletableDeferred<Boolean>()
				pending.set(answer)
				// The machine calls from a background dispatcher; the permission dialog must start on the main thread.
				withContext(Dispatchers.Main) { launcher.launch(Manifest.permission.BLUETOOTH_CONNECT) }
				answer.await()
			},
		)
	}
	DisposableEffect(vm, pairing) {
		vm.attachPairing(pairing)
		onDispose {
			vm.attachPairing(null)
			// A permission request still open must not leave the wizard waiting forever.
			pending.getAndSet(null)?.complete(false)
		}
	}
}

@Composable
private fun Plain(ui: VehicleUi, notes: List<String>, onPrimary: () -> Unit, onSecondary: () -> Unit, modifier: Modifier) {
	StepColumn(ui, notes, modifier) {
		Buttons(ui, onPrimary, onSecondary)
	}
}

@Composable
private fun EnterActivationKey(ui: VehicleUi, notes: List<String>, onContinue: (String) -> Unit, modifier: Modifier) {
	// remember, not rememberSaveable: the key must never reach saved instance state.
	var key by remember { mutableStateOf("") }
	StepColumn(ui, notes, modifier) {
		OutlinedTextField(
			value = key,
			onValueChange = { key = it },
			label = { Text("Activation key") },
			singleLine = true,
			visualTransformation = PasswordVisualTransformation(),
			keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, autoCorrect = false),
			modifier = Modifier.fillMaxWidth(),
		)
		Buttons(
			ui,
			onPrimary = {
				val entered = key
				key = ""
				onContinue(entered)
			},
			onSecondary = {},
		)
	}
}

@Composable
private fun FirstSetup(ui: VehicleUi, problems: List<String>, notes: List<String>, onInstall: (UpdateConfig) -> Unit, modifier: Modifier) {
	var name by rememberSaveable { mutableStateOf("") }
	var level by rememberSaveable { mutableStateOf("") }
	var retention by rememberSaveable { mutableStateOf("") }
	var interval by rememberSaveable { mutableStateOf("") }
	StepColumn(ui, notes, modifier) {
		OutlinedTextField(name, { name = it }, label = { Text("Device name") }, modifier = Modifier.fillMaxWidth())
		OutlinedTextField(level, { level = it }, label = { Text("Log level (${UpdateConfig.LEVELS.joinToString("/")})") }, modifier = Modifier.fillMaxWidth())
		OutlinedTextField(retention, { retention = it }, label = { Text("Log retention days (1-90)") }, modifier = Modifier.fillMaxWidth())
		OutlinedTextField(interval, { interval = it }, label = { Text("Telemetry interval ms (100-60000)") }, modifier = Modifier.fillMaxWidth())
		problems.forEach { Text(it, color = MaterialTheme.colorScheme.error) }
		Buttons(
			ui,
			onPrimary = {
				onInstall(
					UpdateConfig(
						deviceName = name.trim().ifEmpty { null },
						logLevel = level.trim().ifEmpty { null },
						logRetentionDays = number(retention),
						telemetryIntervalMs = number(interval),
					)
				)
			},
			onSecondary = {},
		)
	}
}

/** Empty is "use the default"; text that is not a number becomes an out-of-range value the form check rejects. */
private fun number(text: String): Int? {
	val t = text.trim()
	return if (t.isEmpty()) null else t.toIntOrNull() ?: Int.MIN_VALUE
}

@Composable
private fun PairAdapter(ui: VehicleUi, notes: List<String>, onFinish: () -> Unit, modifier: Modifier) {
	var showAdapter by rememberSaveable { mutableStateOf(false) }
	if (showAdapter) {
		// The existing OBD pairing screen is the adapter step; "Done" ends the step.
		Column(modifier = modifier.fillMaxSize()) {
			OBDPairingScreen(modifier = Modifier.weight(1f))
			Button(onClick = onFinish, modifier = Modifier.fillMaxWidth().padding(16.dp)) { Text("Done") }
		}
	} else {
		PairVehicleStep(
			ui, issue = null, notes = notes,
			onPrimary = { showAdapter = true },
			onSecondary = onFinish,
			modifier = modifier.fillMaxSize().padding(16.dp),
		)
	}
}

@Composable
private fun Done(ui: VehicleUi, notes: List<String>, pis: List<String>, onAnother: () -> Unit, modifier: Modifier) {
	StepColumn(ui, notes, modifier) {
		pis.forEach { Text("Pi: $it") }
		Buttons(ui, onPrimary = {}, onSecondary = onAnother)
	}
}

@Composable
private fun StepColumn(ui: VehicleUi, notes: List<String>, modifier: Modifier, content: @Composable () -> Unit) {
	Column(
		modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
		verticalArrangement = Arrangement.spacedBy(12.dp),
	) {
		ScreenTitle(ui.title)
		Text(ui.body)
		if (ui.busy) {
			val fraction = ui.fraction
			if (fraction != null) LinearProgressIndicator(progress = { fraction }, modifier = Modifier.fillMaxWidth())
			else LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
		}
		notes.forEach { Text(it) }
		content()
	}
}

@Composable
private fun Buttons(ui: VehicleUi, onPrimary: () -> Unit, onSecondary: () -> Unit) {
	Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
		ui.primaryLabel?.let { Button(onClick = onPrimary) { Text(it) } }
		ui.secondaryLabel?.let { OutlinedButton(onClick = onSecondary) { Text(it) } }
	}
}
