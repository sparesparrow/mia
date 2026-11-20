package cz.mia.app.core.update

import java.io.File
import java.io.IOException
import java.security.KeyPair
import java.security.PrivateKey
import java.security.PublicKey
import java.security.Security
import java.util.concurrent.TimeUnit
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.common.KeyType
import net.schmizz.sshj.common.SecurityUtils
import net.schmizz.sshj.transport.verification.HostKeyVerifier
import net.schmizz.sshj.userauth.keyprovider.KeyProvider
import org.bouncycastle.jce.provider.BouncyCastleProvider

/** Trust on first use: the first host key seen for a Pi is kept, a different one later is refused. */
class PinnedHostKeys(private val file: File) : HostKeyVerifier {
	override fun verify(hostname: String, port: Int, key: PublicKey): Boolean {
		val seen = SecurityUtils.getFingerprint(key)
		val pins = if (file.exists()) file.readLines().associate { it.substringBefore(' ') to it.substringAfter(' ') } else emptyMap()
		val id = "$hostname:$port"
		val pinned = pins[id]
		if (pinned == null) {
			file.parentFile?.mkdirs()
			file.appendText("$id $seen\n")
			return true
		}
		return pinned == seen
	}

	override fun findExistingAlgorithms(hostname: String, port: Int): List<String> = emptyList()
}

/**
 * Streams the package to `mia-apply-update` on the Pi (ADR-0023). The server runs the key's forced command whatever
 * is asked for, so the command text is only a label. Needs the Pi's `mia-update` user and a paired key.
 */
class SshUploader(
	private val hostKeys: HostKeyVerifier,
	/** Builds the SSH client; the onboarding wizard passes one that offers only ssh-ed25519 host keys. */
	private val newClient: () -> SSHClient = { SSHClient() },
) {
	fun upload(host: String, keys: KeyPair, pkg: ByteArray, onProgress: (sent: Int, total: Int) -> Unit): UpdateResult {
		// sshj needs the full BouncyCastle, not the cut-down copy Android ships under the same name.
		Security.removeProvider("BC")
		Security.insertProviderAt(BouncyCastleProvider(), 1)
		val client = newClient()
		try {
			client.addHostKeyVerifier(hostKeys)
			client.connectTimeout = 10_000
			client.connect(host, 22)
			client.authPublickey("mia-update", provider(keys))
			client.startSession().use { session ->
				val command = session.exec("mia-apply-update")
				val out = command.outputStream
				var sent = 0
				while (sent < pkg.size) {
					val n = minOf(CHUNK, pkg.size - sent)
					out.write(pkg, sent, n)
					sent += n
					onProgress(sent, pkg.size)
				}
				out.close() // sends EOF: the Pi starts checking
				val stdout = command.inputStream.bufferedReader().readText()
				command.join(10, TimeUnit.MINUTES)
				return UpdateResult.parse(stdout, command.exitStatus)
			}
		} catch (e: IOException) {
			return UpdateResult(false, "ssh", null, "SSH failed: ${e.message ?: e.javaClass.simpleName}")
		} finally {
			try { client.disconnect() } catch (_: IOException) {}
		}
	}

	private fun provider(keys: KeyPair) = object : KeyProvider {
		override fun getPrivate(): PrivateKey = keys.private
		override fun getPublic(): PublicKey = keys.public
		override fun getType(): KeyType = KeyType.ECDSA256
	}

	private companion object { const val CHUNK = 32 * 1024 }
}
