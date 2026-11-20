package cz.mia.app.core.update

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.BuildConfig
import cz.mia.app.core.networking.PiConnectionProvider
import dagger.hilt.android.lifecycle.HiltViewModel
import java.io.File
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

sealed class UpdateProgress {
	object Idle : UpdateProgress()
	data class Working(val what: String, val fraction: Float? = null) : UpdateProgress()
	data class Finished(val result: UpdateResult) : UpdateProgress()
}

data class UpdateUiState(
	val config: UpdateConfig = UpdateConfig(),
	val version: String = BuildConfig.VERSION_NAME.substringBefore("-debug"),
	/** Config edited since the last push: the screen offers to update. */
	val configChanged: Boolean = false,
	val message: String? = null,
	val progress: UpdateProgress = UpdateProgress.Idle,
)

@HiltViewModel
class UpdateViewModel @Inject constructor(
	app: Application,
	private val connection: PiConnectionProvider,
) : AndroidViewModel(app) {
	private val dir = File(app.noBackupFilesDir, "update")
	private val keys = SshKeyStore(dir, SshKeyStore.wrapFor(dir))
	private val prefs = app.getSharedPreferences("software_update", Context.MODE_PRIVATE)
	private val _state = MutableStateFlow(UpdateUiState(config = load()))
	val state: StateFlow<UpdateUiState> = _state.asStateFlow()

	fun setVersion(v: String) = _state.update { it.copy(version = v.trim()) }

	/** Saves the edited config; the screen then offers to push it. */
	fun saveConfig(config: UpdateConfig) {
		val problems = config.problems()
		if (problems.isNotEmpty()) {
			_state.update { it.copy(message = problems.joinToString("\n")) }
			return
		}
		prefs.edit()
			.putString("device_name", config.deviceName).putString("log_level", config.logLevel)
			.putInt("retention", config.logRetentionDays ?: -1).putInt("interval", config.telemetryIntervalMs ?: -1)
			.apply()
		_state.update { it.copy(config = config, configChanged = true, message = "Saved. Update the Pi now to apply it.") }
	}

	/** Shows the command the administrator runs on the Pi; the app cannot pair itself (ADR-0023). */
	fun showPairing() {
		val command = UpdatePairing().command("phone", keys.publicLine())
		_state.update { it.copy(message = "Run this on the Pi, as an administrator:\n$command") }
	}

	/** Lists the phones the Pi has paired (read-only). */
	fun checkPaired() = launchWork("Asking the Pi") {
		val pi = connection.current()
		val result = UpdatePairing().paired(pi.apiBaseUrl, pi.apiKey)
		_state.update {
			it.copy(
				progress = UpdateProgress.Idle,
				message = result.fold({ list -> if (list.isEmpty()) "No phone is paired yet." else "Paired:\n" + list.joinToString("\n") }, { e -> "Check failed: ${e.message}" }),
			)
		}
	}

	/** Downloads the release, builds the package, pushes it, shows the Pi's result. */
	fun update() = launchWork("Downloading release ${_state.value.version}") {
		val s = _state.value
		val pkg = try {
			val release = ReleaseDownloader().download(s.version)
			_state.update { it.copy(progress = UpdateProgress.Working("Building the package")) }
			PackageBuilder.build(s.version, release.bundle, release.sha256sums, s.config, BuildConfig.MIA_SCHEMA_HASH)
		} catch (e: UpdateRefused) {
			finish(UpdateResult(false, "build", null, e.message)); return@launchWork
		} catch (e: java.io.IOException) {
			finish(UpdateResult(false, "download", null, e.message)); return@launchWork
		}
		val host = java.net.URI(connection.current().apiBaseUrl).host
		val result = SshUploader(PinnedHostKeys(File(dir, "known_hosts"))).upload(host, keys.keyPair(), pkg) { sent, total ->
			_state.update { it.copy(progress = UpdateProgress.Working("Sending to the Pi", sent.toFloat() / total)) }
		}
		finish(result)
	}

	private fun finish(result: UpdateResult) =
		_state.update { it.copy(progress = UpdateProgress.Finished(result), configChanged = it.configChanged && !result.ok) }

	private fun launchWork(what: String, block: suspend () -> Unit) {
		if (_state.value.progress is UpdateProgress.Working) return
		_state.update { it.copy(progress = UpdateProgress.Working(what), message = null) }
		viewModelScope.launch(Dispatchers.IO) { block() }
	}

	private fun load() = UpdateConfig(
		deviceName = prefs.getString("device_name", null),
		logLevel = prefs.getString("log_level", null),
		logRetentionDays = prefs.getInt("retention", -1).takeIf { it > 0 },
		telemetryIntervalMs = prefs.getInt("interval", -1).takeIf { it > 0 },
	)
}
