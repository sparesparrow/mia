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
	private val releases = ReleasePackageSource(File(dir, "release-cache")) { version -> ReleaseDownloader(http).download(version) }

	private val machine = OnboardingMachine(
		// Plain objects, not SAM lambdas: kotlinc 1.9 miscompiled a suspend/Result SAM lambda in the machine test (it hung).
		auth = object : AuthPort {
			override fun requestGrant(activationKey: String, devicePublicFp: String, phonePublicKeyLine: String): Result<Grant> =
				authClient.requestGrant(activationKey, devicePublicFp, phonePublicKeyLine)
		},
		discovery = object : DiscoveryPort {
			override suspend fun find(activationKey: String): Result<List<FoundPi>> = withContext(Dispatchers.IO) {
				val devices = authClient.devices(activationKey).getOrElse { return@withContext Result.failure<List<FoundPi>>(it) }
				val trusted = devices.map { it.fp }.toSet()
				Result.success(PiDiscovery(MdnsApiSource(mdns), SshHostKeyReader(), trustedDeviceFps = { trusted }).find(SCAN_MS))
			}
		},
		enroller = EnrollTransport { host, expectedFp, request -> SshEnroller(keys.keyPair()).enroll(host, expectedFp, request) },
		installer = InstallPort { pi, config, onProgress, onNote -> install(pi, config, onProgress, onNote) },
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
		pairingSlot.attach(pairing)
	}

	private fun install(pi: FoundPi, config: UpdateConfig, onProgress: (Int, Int) -> Unit, onNote: (String) -> Unit): UpdateResult {
		val fp = pi.deviceFp ?: return UpdateResult(false, "ssh", null, "The Pi's fingerprint was not vouched for.")
		val version = BuildConfig.VERSION_NAME.substringBefore("-debug")
		val pkg = try {
			// Downloads and saves the release, or uses the verified copy saved earlier when the network fails.
			val got = releases.obtain(version)
			got.note?.let(onNote)
			PackageBuilder.build(version, got.release.bundle, got.release.sha256sums, config, BuildConfig.MIA_SCHEMA_HASH)
		} catch (e: UpdateRefused) {
			return UpdateResult(false, "build", null, e.message)
		} catch (e: ReleaseUnavailable) {
			return UpdateResult(false, "download", null, e.message)
		} catch (e: IOException) {
			return UpdateResult(false, "download", null, ReleaseUnavailable.MESSAGE)
		}
		// Same pin as the enroll step (the fingerprint the machine holds for this Pi), ed25519 host keys only.
		return SshUploader(FingerprintPinVerifier(fp), ::newEd25519SshClient).upload(pi.host, keys.keyPair(), pkg, onProgress)
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
