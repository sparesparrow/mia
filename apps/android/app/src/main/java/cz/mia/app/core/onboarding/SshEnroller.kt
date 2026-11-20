package cz.mia.app.core.onboarding

import com.google.gson.JsonParser
import java.io.IOException
import java.security.KeyPair
import java.security.PrivateKey
import java.security.PublicKey
import java.util.concurrent.TimeUnit
import net.schmizz.sshj.common.Buffer
import net.schmizz.sshj.common.KeyType
import net.schmizz.sshj.transport.verification.HostKeyVerifier
import net.schmizz.sshj.userauth.keyprovider.KeyProvider

/** What `mia-enroll` reported on its last stdout line: {"ok","step","error"[,"warning"]}. */
data class EnrollOutcome(val ok: Boolean, val step: String, val error: String?, val warning: String?) {
	companion object {
		/** The last line that is a JSON object wins; earlier lines (banners, noise) are ignored. */
		fun parse(stdout: String, exitStatus: Int? = null): EnrollOutcome {
			val line = stdout.lineSequence().map { it.trim() }.lastOrNull { it.startsWith("{") }
				?: return EnrollOutcome(false, "no_result", "The Pi sent no result.", null)
			return try {
				val json = JsonParser.parseString(line).asJsonObject
				fun text(name: String) = json.get(name)?.takeUnless { it.isJsonNull }?.asString
				EnrollOutcome(
					ok = json.get("ok").asBoolean && (exitStatus == null || exitStatus == 0),
					step = json.get("step").asString,
					error = text("error"),
					warning = text("warning"),
				)
			} catch (e: RuntimeException) {
				EnrollOutcome(false, "bad_result", "The Pi's result could not be read.", null)
			}
		}
	}
}

/** Sends the enroll request to the Pi and returns its answer. Blocking; never throws for network failures. */
fun interface EnrollTransport {
	/** [expectedFp] is the host-key fingerprint the auth server vouched for ([FoundPi.deviceFp]); the Pi must present it. */
	fun enroll(host: String, expectedFp: String, requestJson: String): EnrollOutcome
}

/**
 * Accepts only the host key whose ssh-ed25519 fingerprint equals [expectedFp], the one the auth server vouched for
 * (REQ-ONB-008). No trust on first use: any other key, or a non-ed25519 key, is refused.
 */
class FingerprintPinVerifier(private val expectedFp: String) : HostKeyVerifier {
	/** [wireBlob] is the SSH wire encoding of the host public key. */
	fun accepts(wireBlob: ByteArray): Boolean = ed25519FingerprintOrNull(wireBlob) == expectedFp

	override fun verify(hostname: String, port: Int, key: PublicKey): Boolean =
		try {
			accepts(Buffer.PlainBuffer().putPublicKey(key).compactData)
		} catch (e: RuntimeException) {
			false
		}

	override fun findExistingAlgorithms(hostname: String, port: Int): List<String> = emptyList()
}

/**
 * Production [EnrollTransport]: SSH user `mia-enroll`, public-key auth with the phone key, the host key pinned to the fingerprint the machine passes (ed25519 only), the request JSON line on
 * the command's stdin, the last stdout line as the answer. The server runs its forced command whatever is asked, so
 * the command text is only a label. The request holds the signed grant: it is never logged and never put in an error.
 */
class SshEnroller(private val keys: KeyPair) : EnrollTransport {
	override fun enroll(host: String, expectedFp: String, requestJson: String): EnrollOutcome {
		val client = newEd25519SshClient()
		try {
			client.addHostKeyVerifier(FingerprintPinVerifier(expectedFp))
			client.connectTimeout = TIMEOUT_MS
			client.timeout = TIMEOUT_MS
			client.connect(host, 22)
			client.authPublickey("mia-enroll", provider())
			client.startSession().use { session ->
				val command = session.exec("mia-enroll")
				val out = command.outputStream
				out.write((requestJson.trim() + "\n").toByteArray(Charsets.UTF_8))
				out.flush()
				out.close() // EOF: the Pi starts checking
				val stdout = command.inputStream.bufferedReader().readText()
				command.join(TIMEOUT_MS.toLong(), TimeUnit.MILLISECONDS)
				return EnrollOutcome.parse(stdout, command.exitStatus)
			}
		} catch (e: IOException) {
			// Only the exception class: a message could echo connection details, never the request.
			return EnrollOutcome(false, "ssh", "SSH to the Pi failed (${e.javaClass.simpleName}).", null)
		} finally {
			try { client.disconnect() } catch (_: IOException) {}
		}
	}

	private fun provider() = object : KeyProvider {
		override fun getPrivate(): PrivateKey = keys.private
		override fun getPublic(): PublicKey = keys.public
		override fun getType(): KeyType = KeyType.ECDSA256
	}

	private companion object { const val TIMEOUT_MS = 10_000 }
}
