package cz.mia.app.core.onboarding

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.BuildConfig
import cz.mia.app.core.networking.MdnsDiscovery
import cz.mia.app.core.update.PackageBuilder
import cz.mia.app.core.update.ReleaseDownloader
import cz.mia.app.core.update.SshKeyStore
import cz.mia.app.core.update.SshUploader
import cz.mia.app.core.update.UpdateConfig
import cz.mia.app.core.update.UpdateRefused
import cz.mia.app.core.update.UpdateResult
import dagger.hilt.android.lifecycle.HiltViewModel
import java.io.File
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient

/** [KnownPiStorage] on SharedPreferences: fingerprints and hosts only, nothing secret. */
class PrefsKnownPiStorage(context: Context) : KnownPiStorage {
	private val prefs = context.getSharedPreferences("known_pis", Context.MODE_PRIVATE)

	override fun read(): Set<String> = prefs.getStringSet(KEY, null)?.toSet() ?: emptySet()

	override fun write(lines: Set<String>) {
		prefs.edit().putStringSet(KEY, lines).apply()
	}

	private companion object { const val KEY = "pis" }
}

/** Until the screens attach the real dialogs, system pairing is reported as unavailable (the wizard skips it). */
private class PairingSlot : SystemPairing {
	@Volatile var target: SystemPairing? = null

	override suspend fun bondBluetooth(): StepOutcome =
		target?.bondBluetooth() ?: StepOutcome.Unavailable("the Bluetooth dialog is not available in this screen")

	override suspend fun suggestWifi(): StepOutcome =
		target?.suggestWifi() ?: StepOutcome.Unavailable("the Wi-Fi dialog is not available in this screen")
}

/**
 * The wizard's ViewModel: wires [OnboardingMachine] to the production ports (auth server, mDNS plus host-key check,
 * SSH enroll, release download and upload). All logic is in the machine; screens only render [state] and call it.
 */
@HiltViewModel
class OnboardingViewModel @Inject constructor(
	app: Application,
	mdns: MdnsDiscovery,
) : AndroidViewModel(app) {
	private val dir = File(app.noBackupFilesDir, "update")
	private val keys = SshKeyStore(dir, SshKeyStore.wrapFor(dir))
	private val http = OkHttpClient()
	private val authClient = AuthServerClient(AUTH_SERVER_URL, http)
	private val pairingSlot = PairingSlot()

	/** Host to the host-key fingerprint the server vouched for; the SSH steps pin to it and refuse unknown hosts. */
	private val vouched = ConcurrentHashMap<String, String>()

	private val machine = OnboardingMachine(
		auth = AuthPort { key, fp, phoneKey -> authClient.requestGrant(key, fp, phoneKey) },
		discovery = DiscoveryPort { key ->
			withContext(Dispatchers.IO) {
				val devices = authClient.devices(key).getOrElse { return@withContext Result.failure<List<FoundPi>>(it) }
				val trusted = devices.map { it.fp }.toSet()
				val found = PiDiscovery(MdnsApiSource(mdns), SshHostKeyReader(), trustedDeviceFps = { trusted }).find(SCAN_MS)
				found.forEach { pi -> pi.deviceFp?.let { vouched[pi.host] = it } }
				Result.success(found)
			}
		},
		enroller = EnrollTransport { host, request ->
			val fp = vouched[host]
				?: return@EnrollTransport EnrollOutcome(false, "ssh", "The Pi's fingerprint was not vouched for.", null)
			SshEnroller(FingerprintPinVerifier(fp), keys.keyPair()).enroll(host, request)
		},
		installer = InstallPort { pi, config, onProgress -> install(pi, config, onProgress) },
		pairing = pairingSlot,
		known = KnownPiStore(PrefsKnownPiStorage(app)),
		phoneKeyLine = { keys.publicLine() },
		scope = viewModelScope,
		io = Dispatchers.IO,
	)

	val state: StateFlow<OnboardingState> = machine.state
	val notes: StateFlow<List<String>> = machine.notes
	val formProblems: StateFlow<List<String>> = machine.formProblems
	val pairingIssue: StateFlow<String?> = machine.pairingIssue

	fun begin() = machine.begin()
	fun restart() = machine.restart()
	fun submitActivationKey(key: String) = machine.submitActivationKey(key)
	fun submitFirstSetup(config: UpdateConfig) = machine.submitFirstSetup(config)
	fun resume() = machine.resume()
	fun retry() = machine.retry()
	fun finishAdapterStep() = machine.finishAdapterStep()

	/** The screen supplies the Activity-bound Bluetooth and Wi-Fi dialogs; null detaches them. */
	fun attachPairing(pairing: SystemPairing?) {
		pairingSlot.target = pairing
	}

	private fun install(pi: FoundPi, config: UpdateConfig, onProgress: (Int, Int) -> Unit): UpdateResult {
		val fp = pi.deviceFp ?: return UpdateResult(false, "ssh", null, "The Pi's fingerprint was not vouched for.")
		val version = BuildConfig.VERSION_NAME.substringBefore("-debug")
		val pkg = try {
			val release = ReleaseDownloader(http).download(version)
			PackageBuilder.build(version, release.bundle, release.sha256sums, config, BuildConfig.MIA_SCHEMA_HASH)
		} catch (e: UpdateRefused) {
			return UpdateResult(false, "build", null, e.message)
		} catch (e: IOException) {
			return UpdateResult(false, "download", null, e.message)
		}
		return SshUploader(FingerprintPinVerifier(fp)).upload(pi.host, keys.keyPair(), pkg, onProgress)
	}

	private companion object {
		/**
		 * Placeholder: the auth server does not exist yet (ADR-0024/0025). The reserved .example name never resolves, so
		 * the wizard shows its retry state until a real address replaces this.
		 */
		const val AUTH_SERVER_URL = "https://auth.mia.example"
		const val SCAN_MS = 5_000L
	}
}
