package cz.mia.app.features.terminal

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.networking.PiConnectionProvider
import cz.mia.app.core.onboarding.KnownPiStore
import cz.mia.app.core.onboarding.PrefsKnownPiStorage
import cz.mia.app.core.terminal.newTerminalSshClient
import cz.mia.app.core.terminal.HostKeyCheck
import cz.mia.app.core.terminal.SshAuth
import cz.mia.app.core.terminal.SshTarget
import cz.mia.app.core.terminal.SshTerminalSession
import cz.mia.app.core.terminal.TerminalEmulator
import cz.mia.app.core.terminal.TerminalHostKeys
import cz.mia.app.core.terminal.TerminalKey
import cz.mia.app.core.terminal.TerminalKeys
import cz.mia.app.core.terminal.TerminalSnapshot
import cz.mia.app.core.update.OpenSshKey
import cz.mia.app.core.update.SshKeyStore
import dagger.hilt.android.lifecycle.HiltViewModel
import java.io.File
import java.io.IOException
import java.net.ConnectException
import java.net.NoRouteToHostException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.security.interfaces.ECPublicKey
import java.util.concurrent.Executors
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import net.schmizz.sshj.userauth.UserAuthException
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

sealed class TerminalStatus {
	object Idle : TerminalStatus()
	object Connecting : TerminalStatus()
	object Connected : TerminalStatus()
	data class Closed(val message: String) : TerminalStatus()
	data class Failed(val message: String, val changedKey: HostKeyCheck.Changed? = null) : TerminalStatus()
}

data class TerminalUiState(
	val host: String = "",
	val port: Int = 22,
	val user: String = "mia",
	val useKey: Boolean = false,
	val status: TerminalStatus = TerminalStatus.Idle,
	/** The phone's terminal public key as an OpenSSH line, once made. */
	val publicKeyLine: String? = null,
	/** Signed in with a password: the screen offers to add the phone key to the account. */
	val passwordSession: Boolean = false,
	val ctrl: Boolean = false,
	val alt: Boolean = false,
	val message: String? = null,
	val fontSize: Int = 12,
)

/**
 * The SSH terminal to the Pi (REQ-AND-029, ADR-0028). The session lives here, so it survives tab switches and
 * screen rotation until the user disconnects or the app ends. Network writes go through one worker thread: Android
 * refuses socket use on the main thread, and keystrokes must keep their order.
 */
@HiltViewModel
class TerminalViewModel @Inject constructor(
	private val app: Application,
	private val connection: PiConnectionProvider,
) : AndroidViewModel(app) {
	private val prefs = app.getSharedPreferences("terminal", Context.MODE_PRIVATE)
	private val dir = File(app.noBackupFilesDir, "terminal")
	private val keyStore = SshKeyStore(dir, SshKeyStore.wrapFor(dir, "mia_terminal_wrap"), name = "terminal_key")
	private val knownPis = KnownPiStore(PrefsKnownPiStorage(app))
	private val hostKeys = TerminalHostKeys(File(dir, "known_hosts")) { knownPis.known() }
	private val writer = Executors.newSingleThreadExecutor { r -> Thread(r, "ssh-terminal-writer").apply { isDaemon = true } }

	private var cols = 80
	private var rows = 24
	private var session: SshTerminalSession? = null
	private var emulator = newEmulator()

	private val _state = MutableStateFlow(load())
	val state: StateFlow<TerminalUiState> = _state.asStateFlow()

	private val _screen = MutableStateFlow<TerminalSnapshot>(emulator.snapshot())
	val screen: StateFlow<TerminalSnapshot> = _screen.asStateFlow()
	private val dirty = MutableSharedFlow<Unit>(extraBufferCapacity = 1, onBufferOverflow = BufferOverflow.DROP_OLDEST)

	init {
		viewModelScope.launch(Dispatchers.Default) {
			// At most one snapshot per frame however fast the Pi writes.
			dirty.collect {
				delay(FRAME_MS)
				_screen.value = emulator.snapshot()
			}
		}
		viewModelScope.launch(Dispatchers.IO) {
			val line = try {
				OpenSshKey.publicLine(keyStore.keyPair().public as ECPublicKey) + " mia-phone-terminal"
			} catch (e: Exception) {
				null
			}
			_state.update { it.copy(publicKeyLine = line) }
		}
	}

	private fun newEmulator() = TerminalEmulator(cols, rows) { reply -> writer.execute { session?.write(reply) } }

	private fun load(): TerminalUiState {
		val defaultHost = connection.current().apiBaseUrl.toHttpUrlOrNull()?.host.orEmpty()
		return TerminalUiState(
			host = prefs.getString("host", null)?.takeIf { it.isNotBlank() } ?: defaultHost,
			port = prefs.getInt("port", 22),
			user = prefs.getString("user", null) ?: "mia",
			useKey = prefs.getBoolean("use_key", false),
			fontSize = prefs.getInt("font_size", 12),
		)
	}

	fun setHost(v: String) = _state.update { it.copy(host = v.trim()) }
	/** Digits only; an empty field is 0, which [SshTarget] refuses on Connect. */
	fun setPort(v: String) = _state.update { it.copy(port = v.filter(Char::isDigit).take(5).toIntOrNull() ?: 0) }
	fun setUser(v: String) = _state.update { it.copy(user = v.trim()) }
	fun setUseKey(v: Boolean) = _state.update { it.copy(useKey = v) }
	fun dismissMessage() = _state.update { it.copy(message = null) }

	fun changeFont(delta: Int) {
		_state.update { it.copy(fontSize = (it.fontSize + delta).coerceIn(7, 24)) }
		prefs.edit().putInt("font_size", _state.value.fontSize).apply()
	}

	/** [password] is used for this one sign-in and then dropped. */
	fun connect(password: String) {
		val s = _state.value
		if (s.status == TerminalStatus.Connecting || s.status == TerminalStatus.Connected) return
		val target = try {
			SshTarget(s.host, s.port, s.user)
		} catch (e: IllegalArgumentException) {
			_state.update { it.copy(status = TerminalStatus.Failed(e.message ?: "Check the host, port and user")) }
			return
		}
		if (!s.useKey && password.isEmpty()) {
			_state.update { it.copy(status = TerminalStatus.Failed("Enter the password, or sign in with the phone key")) }
			return
		}
		prefs.edit().putString("host", target.host).putInt("port", target.port).putString("user", target.user)
			.putBoolean("use_key", s.useKey).apply()
		_state.update { it.copy(status = TerminalStatus.Connecting, message = null, passwordSession = !s.useKey) }
		viewModelScope.launch(Dispatchers.IO) {
			val auth = if (s.useKey) SshAuth.Key(keyStore.keyPair()) else SshAuth.Password(password)
			val next = SshTerminalSession({ newTerminalSshClient() }, hostKeys)
			emulator = newEmulator()
			hostKeys.clearLastCheck()
			session = next // before open: a shell that exits at once reports through onClosed, which checks this
			try {
				next.open(target, auth, cols, rows, onOutput = { text -> emulator.feed(text); dirty.tryEmit(Unit) }) { status, error ->
					onClosed(next, status, error)
				}
				when (val check = hostKeys.lastCheck) {
					is HostKeyCheck.New -> notice("New host ${target.host}: pinned its key ${check.fingerprint}")
					is HostKeyCheck.Known -> Unit
					else -> Unit
				}
				_state.update { if (session === next) it.copy(status = TerminalStatus.Connected) else it }
			} catch (e: IOException) {
				if (session === next) session = null
				_state.update { it.copy(status = failure(target, e)) }
			}
			dirty.tryEmit(Unit)
		}
	}

	private fun failure(target: SshTarget, e: IOException): TerminalStatus.Failed {
		return when (val check = hostKeys.lastCheck) {
			is HostKeyCheck.Changed -> TerminalStatus.Failed(
				"The host key of ${target.host} changed. Expected ${check.expected}, got ${check.seen}. " +
					"Connect only if you know why (a reinstalled Pi); forget the pinned key to accept the new one.",
				check,
			)
			HostKeyCheck.Unsupported -> TerminalStatus.Failed("${target.host} did not offer an ssh-ed25519 host key.")
			else -> TerminalStatus.Failed(
				when (e) {
					is UserAuthException ->
						if (_state.value.useKey) "${target.user}@${target.host} refused the phone key. Add it to ~/.ssh/authorized_keys first."
						else "${target.user}@${target.host} refused the password."
					else -> when (val cause = rootCause(e)) {
						is UnknownHostException -> "Unknown host ${target.host}."
						is ConnectException, is NoRouteToHostException -> "Could not reach ${target.host}:${target.port}."
						is SocketTimeoutException -> "${target.host}:${target.port} did not answer in time."
						else -> "SSH failed: ${cause.message ?: cause.javaClass.simpleName}"
					}
				}
			)
		}
	}

	private fun rootCause(e: Throwable): Throwable {
		var t = e
		while (t.cause != null && t.cause !== t) t = t.cause!!
		return t
	}

	private fun onClosed(which: SshTerminalSession, status: Int?, error: String?) {
		if (session !== which) return
		session = null
		val text = when {
			error != null -> "Connection lost: $error"
			status != null -> "Session ended (exit $status)"
			else -> "Session ended"
		}
		notice(text)
		_state.update { it.copy(status = TerminalStatus.Closed(text), ctrl = false, alt = false) }
	}

	/** A line from the app itself, dimmed so it does not look like the Pi's output. */
	private fun notice(text: String) {
		emulator.feed("\r\n\u001b[2m[MIA] $text\u001b[0m\r\n")
		dirty.tryEmit(Unit)
	}

	fun disconnect() {
		val s = session ?: return
		writer.execute { s.close() }
	}

	fun forgetHostKey() {
		val s = _state.value
		hostKeys.forget(s.host, s.port)
		_state.update { it.copy(status = TerminalStatus.Idle, message = "Forgot the pinned key for ${s.host}:${s.port}.") }
	}

	/** Back to the connection form after a session ended. */
	fun showForm() = _state.update { it.copy(status = TerminalStatus.Idle) }

	fun toggleCtrl() = _state.update { it.copy(ctrl = !it.ctrl) }
	fun toggleAlt() = _state.update { it.copy(alt = !it.alt) }

	fun send(text: String) {
		val s = _state.value
		val out = TerminalKeys.typed(text, ctrl = s.ctrl, alt = s.alt)
		if (s.ctrl || s.alt) _state.update { it.copy(ctrl = false, alt = false) }
		write(out)
	}

	fun key(key: TerminalKey) {
		val s = _state.value
		val seq = TerminalKeys.sequence(key, emulator.applicationCursorKeys)
		write(if (s.alt) "\u001b$seq" else seq)
		if (s.ctrl || s.alt) _state.update { it.copy(ctrl = false, alt = false) }
	}

	fun paste(text: String) = write(TerminalKeys.paste(text, emulator.bracketedPaste))

	/** Bytes as they are: control characters from the key row or a hardware keyboard. */
	fun sendRaw(text: String) = write(text)

	private fun write(text: String) {
		if (text.isEmpty()) return
		val s = session ?: return
		writer.execute { s.write(text) }
	}

	fun resize(newCols: Int, newRows: Int) {
		if (newCols < 10 || newRows < 3 || (newCols == cols && newRows == rows)) return
		cols = newCols
		rows = newRows
		emulator.resize(cols, rows)
		dirty.tryEmit(Unit)
		val s = session ?: return
		writer.execute { s.resize(cols, rows) }
	}

	/**
	 * Adds the phone's terminal key to the signed-in account's `~/.ssh/authorized_keys` on its own SSH channel
	 * (nothing is typed into the shell), so later sign-ins need no password. Only on the user's tap.
	 */
	fun installPhoneKey() {
		val line = _state.value.publicKeyLine ?: return
		val s = session ?: return
		require(!line.contains('\'') && !line.contains('\n'))
		val command = "umask 077; mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && " +
			"(grep -qxF '$line' ~/.ssh/authorized_keys || echo '$line' >> ~/.ssh/authorized_keys) && echo added"
		writer.execute {
			val result = try {
				s.exec(command)
			} catch (e: IOException) {
				Pair(null, e.message.orEmpty())
			}
			val ok = result.first == 0 && result.second.contains("added")
			if (ok) {
				prefs.edit().putBoolean("use_key", true).apply()
				_state.update { it.copy(useKey = true, message = "Phone key added. Next time, sign in with the phone key.") }
			} else {
				_state.update { it.copy(message = "Could not add the key: ${result.second.trim().take(200)}") }
			}
		}
	}

	override fun onCleared() {
		session?.let { s -> writer.execute { s.close() } }
		writer.shutdown()
	}

	private companion object { const val FRAME_MS = 16L }
}
