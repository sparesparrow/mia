package cz.mia.app.core.terminal

import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.nio.ByteBuffer
import java.nio.CharBuffer
import java.nio.charset.CodingErrorAction
import java.security.KeyPair
import java.security.PrivateKey
import java.security.PublicKey
import java.util.concurrent.TimeUnit
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.common.KeyType
import net.schmizz.sshj.connection.channel.direct.Session
import net.schmizz.sshj.transport.verification.HostKeyVerifier
import net.schmizz.sshj.userauth.keyprovider.KeyProvider

/** Where the terminal connects: a login user on the Pi. */
data class SshTarget(val host: String, val port: Int = 22, val user: String = "mia") {
	init {
		require(host.isNotBlank()) { "host is required" }
		require(port in 1..65535) { "port must be 1-65535" }
		require(USER.matches(user)) { "user must be a plain login name" }
	}

	private companion object { val USER = Regex("^[a-z_][a-z0-9_.-]{0,31}$") }
}

/** How the terminal signs in. A password lives only as long as the connect call; it is never stored. */
sealed class SshAuth {
	class Password(val password: String) : SshAuth() {
		override fun toString() = "Password(****)"
	}

	/** The phone's terminal key (an EC P-256 pair), authorised by the Pi's administrator. */
	class Key(val keys: KeyPair) : SshAuth()

	/** Anything else sshj can do; for tests and tools. */
	class Custom(val authenticate: (SSHClient, String) -> Unit) : SshAuth()
}

/** Reads bytes as UTF-8 text in chunks, keeping a multi-byte character that is split across reads. */
class Utf8Chunker {
	private val decoder = Charsets.UTF_8.newDecoder()
		.onMalformedInput(CodingErrorAction.REPLACE)
		.onUnmappableCharacter(CodingErrorAction.REPLACE)
	private var pending = ByteBuffer.allocate(0)
	private val out = CharBuffer.allocate(8192)

	fun decode(bytes: ByteArray, length: Int = bytes.size): String {
		val input = ByteBuffer.allocate(pending.remaining() + length)
		input.put(pending).put(bytes, 0, length).flip()
		val text = StringBuilder()
		while (true) {
			out.clear()
			val result = decoder.decode(input, out, false)
			out.flip()
			text.append(out)
			if (!result.isOverflow) break
		}
		pending = input.slice()
		return text.toString()
	}
}

/**
 * One interactive SSH shell with a pseudo-terminal (REQ-AND-029). [open] connects, signs in, asks for an
 * `xterm-256color` PTY and starts the login shell, then a reader thread hands the output to [onOutput] until the
 * shell ends, when [onClosed] gets the exit status (null when the link dropped) and an error text.
 */
class SshTerminalSession(
	private val newClient: () -> SSHClient,
	private val hostKeys: HostKeyVerifier,
	private val connectTimeoutMs: Int = 10_000,
) {
	@Volatile private var client: SSHClient? = null
	@Volatile private var shell: Session.Shell? = null
	@Volatile private var input: OutputStream? = null
	@Volatile private var closing = false

	val isOpen: Boolean get() = shell?.isOpen == true

	/** Blocking. Throws [IOException] when the connection, sign-in or shell fails; everything is closed then. */
	@Throws(IOException::class)
	fun open(target: SshTarget, auth: SshAuth, cols: Int, rows: Int, onOutput: (String) -> Unit, onClosed: (Int?, String?) -> Unit) {
		closing = false
		val c = newClient()
		client = c
		try {
			c.addHostKeyVerifier(hostKeys)
			c.connectTimeout = connectTimeoutMs
			c.connect(target.host, target.port)
			c.connection.keepAlive.keepAliveInterval = 15
			when (auth) {
				is SshAuth.Password -> c.authPassword(target.user, auth.password)
				is SshAuth.Key -> c.authPublickey(target.user, provider(auth.keys))
				is SshAuth.Custom -> auth.authenticate(c, target.user)
			}
			val session = c.startSession()
			// UTF-8 whatever the Pi's default locale; sshd may refuse the variable, which changes nothing.
			try { session.setEnvVar("LANG", "C.UTF-8") } catch (_: IOException) {}
			session.allocatePTY("xterm-256color", cols, rows, 0, 0, emptyMap())
			val s = session.startShell()
			shell = s
			input = s.outputStream
			Thread({ pump(s.inputStream, onOutput, onClosed) }, "ssh-terminal-reader").apply { isDaemon = true }.start()
		} catch (e: IOException) {
			close()
			throw e
		}
	}

	private fun pump(stream: InputStream, onOutput: (String) -> Unit, onClosed: (Int?, String?) -> Unit) {
		val chunker = Utf8Chunker()
		val buffer = ByteArray(8192)
		var error: String? = null
		try {
			while (true) {
				val n = stream.read(buffer)
				if (n < 0) break
				if (n > 0) onOutput(chunker.decode(buffer, n))
			}
		} catch (e: IOException) {
			if (!closing) error = e.message ?: e.javaClass.simpleName
		}
		val status = try {
			// sshj's SessionChannel is both a Shell and a Command; the exit status can arrive just after EOF.
			(shell as? Session.Command)?.let { it.join(2, TimeUnit.SECONDS); it.exitStatus }
		} catch (e: Exception) {
			null
		}
		close()
		onClosed(status, error)
	}

	/** Sends keystrokes. Returns false when the session is gone. */
	fun write(text: String): Boolean {
		val out = input ?: return false
		return try {
			synchronized(out) {
				out.write(text.toByteArray(Charsets.UTF_8))
				out.flush()
			}
			true
		} catch (e: IOException) {
			false
		}
	}

	/**
	 * Runs [command] on its own channel of the open connection, beside the shell, so nothing is typed into whatever
	 * runs in the terminal. Blocking. Returns the exit status (null when unknown) and the output.
	 */
	@Throws(IOException::class)
	fun exec(command: String, timeoutSeconds: Long = 20): Pair<Int?, String> {
		val c = client ?: throw IOException("not connected")
		c.startSession().use { session ->
			val cmd = session.exec(command)
			val out = cmd.inputStream.bufferedReader().readText() + cmd.errorStream.bufferedReader().readText()
			cmd.join(timeoutSeconds, TimeUnit.SECONDS)
			return Pair(cmd.exitStatus, out)
		}
	}

	fun resize(cols: Int, rows: Int) {
		try {
			shell?.changeWindowDimensions(cols, rows, 0, 0)
		} catch (e: Exception) {
			// The shell is going away; the reader reports it.
		}
	}

	fun close() {
		closing = true
		val s = shell
		val c = client
		shell = null
		input = null
		client = null
		try { s?.close() } catch (_: Exception) {}
		try { c?.disconnect() } catch (_: Exception) {}
	}

	private fun provider(keys: KeyPair) = object : KeyProvider {
		override fun getPrivate(): PrivateKey = keys.private
		override fun getPublic(): PublicKey = keys.public
		override fun getType(): KeyType = KeyType.ECDSA256
	}
}
