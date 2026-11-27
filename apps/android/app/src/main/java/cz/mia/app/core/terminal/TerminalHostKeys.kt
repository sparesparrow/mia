package cz.mia.app.core.terminal

import cz.mia.app.core.onboarding.KnownPi
import cz.mia.app.core.onboarding.ed25519FingerprintOrNull
import java.io.File
import java.security.PublicKey
import net.schmizz.sshj.common.Buffer
import net.schmizz.sshj.transport.verification.HostKeyVerifier

/** What the last host-key check found, for the screen to tell the user. */
sealed class HostKeyCheck {
	/** First connection to this address: the key was pinned. */
	data class New(val fingerprint: String) : HostKeyCheck()
	/** The key matches the pin, or the fingerprint the onboarding wizard was vouched. */
	data class Known(val fingerprint: String) : HostKeyCheck()
	/** The key differs from the pin: refused. */
	data class Changed(val expected: String, val seen: String) : HostKeyCheck()
	/** Not an ssh-ed25519 key: refused. */
	object Unsupported : HostKeyCheck()
}

/**
 * Host-key policy for the terminal (REQ-AND-029, ADR-0028): ssh-ed25519 only, pinned per `host:port` in [file] on
 * first use, and a different key later is refused until the user forgets the pin. A Pi that finished the onboarding
 * wizard ([vouched]) is pinned from the start to the fingerprint the auth server vouched for.
 */
class TerminalHostKeys(
	private val file: File,
	private val vouched: () -> List<KnownPi> = { emptyList() },
) : HostKeyVerifier {
	@Volatile
	var lastCheck: HostKeyCheck? = null
		private set

	override fun verify(hostname: String, port: Int, key: PublicKey): Boolean {
		val blob = try {
			Buffer.PlainBuffer().putPublicKey(key).compactData
		} catch (e: RuntimeException) {
			null
		}
		return check(hostname, port, blob)
	}

	/** Forgets the last result, before a new connection attempt. */
	fun clearLastCheck() { lastCheck = null }

	/** [wireBlob] is the SSH wire encoding of the host key. */
	@Synchronized
	fun check(hostname: String, port: Int, wireBlob: ByteArray?): Boolean {
		val seen = wireBlob?.let { ed25519FingerprintOrNull(it) }
		if (seen == null) {
			lastCheck = HostKeyCheck.Unsupported
			return false
		}
		val id = "$hostname:$port"
		val expected = pins()[id] ?: if (port == 22) vouched().firstOrNull { it.host == hostname }?.fp else null
		lastCheck = when {
			expected == null -> { pin(id, seen); HostKeyCheck.New(seen) }
			expected == seen -> HostKeyCheck.Known(seen)
			else -> HostKeyCheck.Changed(expected, seen)
		}
		return lastCheck !is HostKeyCheck.Changed
	}

	/** Drops the pin for [hostname]:[port]; the next connection pins whatever key it sees. */
	@Synchronized
	fun forget(hostname: String, port: Int) {
		val id = "$hostname:$port"
		val kept = pins().filterKeys { it != id }
		file.parentFile?.mkdirs()
		file.writeText(kept.entries.joinToString("") { "${it.key} ${it.value}\n" })
	}

	private fun pins(): Map<String, String> =
		if (file.exists()) file.readLines().filter { ' ' in it }.associate { it.substringBefore(' ') to it.substringAfter(' ') }
		else emptyMap()

	private fun pin(id: String, fp: String) {
		file.parentFile?.mkdirs()
		file.appendText("$id $fp\n")
	}

	override fun findExistingAlgorithms(hostname: String, port: Int): List<String> = emptyList()
}
