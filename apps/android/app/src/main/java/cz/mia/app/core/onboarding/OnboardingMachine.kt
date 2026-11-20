package cz.mia.app.core.onboarding

import com.google.gson.JsonObject
import cz.mia.app.core.update.UpdateConfig
import cz.mia.app.core.update.UpdateResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Asks the auth server for a grant (blocking; the machine calls it on its io dispatcher). */
fun interface AuthPort {
	fun requestGrant(activationKey: String, devicePublicFp: String, phonePublicKeyLine: String): Result<Grant>
}

/**
 * Finds the Pis the auth server vouches for: GET /v1/devices, then the mDNS scan and the host-key check
 * ([PiDiscovery]). A failure of the devices call comes back as the [AuthServerError] inside the failed [Result].
 */
fun interface DiscoveryPort {
	suspend fun find(activationKey: String): Result<List<FoundPi>>
}

/** Downloads the release, builds the package with [config] and uploads it to [pi] (ADR-0023). */
fun interface InstallPort {
	suspend fun install(pi: FoundPi, config: UpdateConfig, onProgress: (sent: Int, total: Int) -> Unit): UpdateResult
}

/**
 * The wizard of ADR-0025 as a state machine over small ports (REQ-ONB-008). Order: Welcome, EnterActivationKey,
 * FindingPi, Authorizing, FirstSetup, Installing, PairingPhone, PairAdapter, Done, plus Failed.
 *
 * Rules: nothing is enrolled or installed unless the auth server gave a grant; an unreachable server never lets the
 * wizard go on; the activation key lives in this object's memory only until the Pi is enrolled and is never in a
 * state, a message or a log; [KnownPiStore] is written once, at Done. State is in memory: a killed process starts over.
 */
class OnboardingMachine(
	private val auth: AuthPort,
	private val discovery: DiscoveryPort,
	private val enroller: EnrollTransport,
	private val installer: InstallPort,
	private val pairing: SystemPairing,
	private val known: KnownPiStore,
	private val phoneKeyLine: () -> String,
	private val scope: CoroutineScope,
	private val io: CoroutineDispatcher,
) {
	private enum class Phase { FIND, AUTHORIZE, INSTALL, PAIR }

	private val _state = MutableStateFlow<OnboardingState>(OnboardingState.Welcome)
	val state: StateFlow<OnboardingState> = _state.asStateFlow()

	/** Things the user should see that are not failures: enroll warnings, steps skipped as unavailable. */
	private val _notes = MutableStateFlow<List<String>>(emptyList())
	val notes: StateFlow<List<String>> = _notes.asStateFlow()

	/** Why FirstSetup did not accept the form; empty when it did. */
	private val _formProblems = MutableStateFlow<List<String>>(emptyList())
	val formProblems: StateFlow<List<String>> = _formProblems.asStateFlow()

	/** Why the last Bluetooth or Wi-Fi attempt did not finish (cancelled, failed); the state stays PairingPhone. */
	private val _pairingIssue = MutableStateFlow<String?>(null)
	val pairingIssue: StateFlow<String?> = _pairingIssue.asStateFlow()

	private val lock = Any()
	private var activationKey: String? = null
	private var pi: FoundPi? = null
	private var enrolled = false
	private var config: UpdateConfig? = null
	private var pairStep = 0 // 0 Bluetooth, 1 Wi-Fi, 2 finished
	private var failedPhase: Phase? = null
	private var job: Job? = null

	/** Welcome -> EnterActivationKey. */
	fun begin() {
		synchronized(lock) {
			if (_state.value == OnboardingState.Welcome) _state.value = OnboardingState.EnterActivationKey
		}
	}

	/** Forgets everything of this run (the key included) and returns to the key entry. */
	fun restart() {
		synchronized(lock) {
			job?.cancel()
			job = null
			activationKey = null
			pi = null
			enrolled = false
			config = null
			pairStep = 0
			failedPhase = null
			_notes.value = emptyList()
			_formProblems.value = emptyList()
			_pairingIssue.value = null
			_state.value = OnboardingState.EnterActivationKey
		}
	}

	fun submitActivationKey(key: String) {
		synchronized(lock) {
			val trimmed = key.trim()
			if (_state.value != OnboardingState.EnterActivationKey || trimmed.isEmpty() || busy()) return
			activationKey = trimmed
			_state.value = OnboardingState.FindingPi
			launch(Phase.FIND)
		}
	}

	/** Valid config: install with it. Problems: stay in FirstSetup and publish them in [formProblems]. */
	fun submitFirstSetup(config: UpdateConfig) {
		synchronized(lock) {
			if (_state.value != OnboardingState.FirstSetup || busy()) return
			val problems = config.problems()
			_formProblems.value = problems
			if (problems.isNotEmpty()) return
			this.config = config
			_state.value = OnboardingState.Installing(0, 0)
			launch(Phase.INSTALL)
		}
	}

	/**
	 * Continues the current step. In PairingPhone it runs the next Bluetooth or Wi-Fi dialog (the screen says what the
	 * dialog is before calling); after a cancelled or failed dialog it asks for the same one again.
	 */
	fun resume() {
		synchronized(lock) {
			if (_state.value == OnboardingState.PairingPhone && !busy()) {
				_pairingIssue.value = null
				launch(Phase.PAIR)
			}
		}
	}

	/** Repeats the failed phase when it is retryable (or the pairing dialog); otherwise does nothing. */
	fun retry() {
		synchronized(lock) {
			val current = _state.value
			if (current == OnboardingState.PairingPhone) {
				resume()
				return
			}
			val phase = failedPhase
			if (current !is OnboardingState.Failed || !current.retryable || phase == null || busy()) return
			when (phase) {
				Phase.FIND -> {
					if (activationKey == null) { _state.value = OnboardingState.EnterActivationKey; return }
					_state.value = OnboardingState.FindingPi
				}
				Phase.AUTHORIZE -> _state.value = OnboardingState.Authorizing
				Phase.INSTALL -> _state.value = OnboardingState.Installing(0, 0)
				Phase.PAIR -> return
			}
			launch(phase)
		}
	}

	/** The OBD adapter step ended (paired or skipped by the user): the wizard is Done and the Pi is remembered. */
	fun finishAdapterStep() {
		synchronized(lock) {
			if (_state.value != OnboardingState.PairAdapter) return
			val target = pi ?: return
			val fp = target.deviceFp ?: return
			known.save(fp, target.host)
			_state.value = OnboardingState.Done
		}
	}

	private fun busy() = job?.isActive == true

	private fun launch(phase: Phase) {
		job = scope.launch(io) {
			try {
				when (phase) {
					Phase.FIND -> find()
					Phase.AUTHORIZE -> authorize()
					Phase.INSTALL -> install()
					Phase.PAIR -> pair()
				}
			} catch (e: CancellationException) {
				throw e
			} catch (e: Exception) {
				// Never echo the exception text: it could carry request data.
				if (phase == Phase.PAIR) _pairingIssue.value = "The step failed unexpectedly. Try again."
				else fail(phase, step(phase), true, "Something went wrong unexpectedly. Try again.")
			}
		}
	}

	private suspend fun find() {
		val key = activationKey ?: return fail(Phase.FIND, "finding_pi", false, "The activation key is missing.")
		_state.value = OnboardingState.FindingPi
		val found = discovery.find(key).getOrElse { return failFrom(Phase.FIND, it) }
		if (found.isEmpty()) {
			return fail(Phase.FIND, "finding_pi", true, "No MIA Pi registered to your account was found. Check that it is powered and reachable, then try again.")
		}
		val chosen = found.first()
		if (chosen.deviceFp == null) return fail(Phase.FIND, "finding_pi", false, "The Pi did not present a fingerprint the server vouched for.")
		synchronized(lock) { pi = chosen }
		authorize()
	}

	private fun authorize() {
		val key = activationKey ?: return fail(Phase.AUTHORIZE, "authorizing", false, "The activation key is missing.")
		val target = pi ?: return fail(Phase.AUTHORIZE, "authorizing", false, "No Pi is selected.")
		val fp = target.deviceFp ?: return fail(Phase.AUTHORIZE, "authorizing", false, "The Pi has no vouched fingerprint.")
		_state.value = OnboardingState.Authorizing
		val phoneKey = phoneKeyLine()
		val grant = auth.requestGrant(key, fp, phoneKey).getOrElse { return failFrom(Phase.AUTHORIZE, it) }
		// The grant text is forwarded byte for byte: the Pi verifies the signature over exactly these characters.
		val request = JsonObject().apply {
			addProperty("grant", grant.json)
			addProperty("signature", grant.signature)
			addProperty("phone_public_key", phoneKey)
		}
		val outcome = enroller.enroll(target.host, request.toString())
		if (!outcome.ok) {
			// A used grant is burned on the Pi; retry asks the server for a new one.
			return fail(Phase.AUTHORIZE, "authorizing", true, outcome.error ?: "The Pi refused the enrollment (${outcome.step}).")
		}
		synchronized(lock) {
			enrolled = true
			activationKey = null // not needed any more
			outcome.warning?.let { w -> _notes.update { it + w } }
			_state.value = OnboardingState.FirstSetup
		}
	}

	private suspend fun install() {
		val snapshot = synchronized(lock) { Triple(enrolled, pi, config) }
		// Without an obtained grant and a finished enrollment nothing is installed.
		if (!snapshot.first) return fail(Phase.INSTALL, "installing", false, "The phone is not enrolled on the Pi.")
		val target = snapshot.second ?: return fail(Phase.INSTALL, "installing", false, "No Pi is selected.")
		val cfg = snapshot.third ?: return fail(Phase.INSTALL, "installing", false, "The first setup is missing.")
		val result = installer.install(target, cfg) { sent, total ->
			_state.update { if (it is OnboardingState.Installing) OnboardingState.Installing(sent, total) else it }
		}
		if (!result.ok) {
			return fail(Phase.INSTALL, "installing", true, result.error ?: "The install failed at step ${result.step}.")
		}
		synchronized(lock) {
			pairStep = 0
			_state.value = OnboardingState.PairingPhone
		}
	}

	private suspend fun pair() {
		while (true) {
			val index = synchronized(lock) { pairStep }
			if (index >= 2) break
			val label = if (index == 0) "Bluetooth" else "Wi-Fi"
			val outcome = if (index == 0) pairing.bondBluetooth() else pairing.suggestWifi()
			when (outcome) {
				StepOutcome.Done -> synchronized(lock) { pairStep = index + 1 }
				is StepOutcome.Unavailable -> synchronized(lock) {
					pairStep = index + 1
					_notes.update { it + "$label skipped: ${outcome.why}" }
				}
				is StepOutcome.Cancelled -> { _pairingIssue.value = "$label was cancelled (${outcome.why}). Try again."; return }
				is StepOutcome.Failed -> { _pairingIssue.value = "$label failed (${outcome.msg}). Try again."; return }
			}
		}
		_state.value = OnboardingState.PairAdapter
	}

	private fun step(phase: Phase) = when (phase) {
		Phase.FIND -> "finding_pi"
		Phase.AUTHORIZE -> "authorizing"
		Phase.INSTALL -> "installing"
		Phase.PAIR -> "pairing"
	}

	private fun failFrom(phase: Phase, e: Throwable) {
		val retryable = when (e) {
			is AuthServerError.Unauthorized, is AuthServerError.UnknownDevice, is AuthServerError.Rejected -> false
			else -> true
		}
		val message = if (e is AuthServerError) e.message.orEmpty() else "Something went wrong. Try again."
		fail(phase, step(phase), retryable, message)
	}

	private fun fail(phase: Phase, step: String, retryable: Boolean, message: String) {
		synchronized(lock) {
			failedPhase = phase
			_state.value = OnboardingState.Failed(step, retryable, message)
		}
	}
}
