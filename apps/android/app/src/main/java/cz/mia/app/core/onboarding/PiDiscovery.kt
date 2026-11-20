package cz.mia.app.core.onboarding

import cz.mia.app.core.networking.MdnsDiscovery
import java.security.MessageDigest
import java.security.PublicKey
import java.security.Security
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.common.Buffer
import net.schmizz.sshj.transport.verification.HostKeyVerifier
import org.bouncycastle.jce.provider.BouncyCastleProvider

/** How the phone reaches a Pi. [classify] derives the Wi-Fi and USB variants from the address; Bluetooth has none. */
sealed interface Transport {
	data object Usb : Transport
	data object Hotspot : Transport
	data object MiaWifi : Transport
	data object Bluetooth : Transport
}

/** A Pi that answered the scan and whose SSH host key the auth server registered for this account. */
data class FoundPi(val host: String, val transport: Transport, val deviceFp: String?)

/** The mDNS scan. Returns "host:port" strings, as [MdnsDiscovery.discoverApi] does. */
fun interface MdnsSource {
	suspend fun discoverApi(timeoutMs: Long): List<String>
}

/** Reads a host's SSH host-key fingerprint in the OpenSSH form `SHA256:<base64>`, or null when it cannot be read. */
fun interface HostKeyReader {
	fun fingerprint(host: String): String?
}

/**
 * Finds the Pi the phone can reach. There is no trust on first use: a Pi counts only when its host-key fingerprint is
 * in [trustedDeviceFps], the set the auth server returned for this account (ADR-0025, REQ-ONB-008).
 */
class PiDiscovery(
	private val mdns: MdnsSource,
	private val hostKeyReader: HostKeyReader,
	private val trustedDeviceFps: () -> Set<String>,
) {
	suspend fun find(timeoutMs: Long): List<FoundPi> {
		// mDNS gives "host:port" for the API port; the SSH probe below always uses port 22, so only the host is kept.
		val hosts = mdns.discoverApi(timeoutMs)
			.map { it.substringBeforeLast(':') }
			.filter { it.isNotEmpty() }
			.distinct()
		if (hosts.isEmpty()) return emptyList()
		// The trusted set may come from a blocking call (AuthServerClient.devices) and each host-key read blocks on the
		// network, so both run off the caller's dispatcher.
		return withContext(Dispatchers.IO) {
			val trusted = trustedDeviceFps()
			if (trusted.isEmpty()) return@withContext emptyList()
			hosts.mapNotNull { host ->
				val fp = hostKeyReader.fingerprint(host)
				if (fp != null && fp in trusted) FoundPi(host, classify(host), fp) else null
			}
		}
	}
}

/**
 * Maps a Pi's address to how the phone reaches it: 192.168.4.x is the Pi's own MIA Wi-Fi, 192.168.42.x and 172.x are
 * USB-tether ranges, and everything else on Wi-Fi (10.15.60.x, a phone hotspot, any other range) is
 * [Transport.Hotspot].
 */
fun classify(host: String): Transport {
	val parts = host.split('.')
	if (parts.size != 4 || parts.any { it.toIntOrNull() == null }) return Transport.Hotspot
	val (a, b, c) = parts.map { it.toInt() }
	return when {
		a == 192 && b == 168 && c == 4 -> Transport.MiaWifi
		a == 192 && b == 168 && c == 42 -> Transport.Usb
		a == 172 -> Transport.Usb
		else -> Transport.Hotspot
	}
}

/** The OpenSSH fingerprint of a public key: `SHA256:` plus SHA-256 of the SSH wire blob, base64 without padding. */
internal fun fingerprintOf(wireBlob: ByteArray): String =
	"SHA256:" + base64NoPadding(MessageDigest.getInstance("SHA-256").digest(wireBlob))

private const val BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

/** Base64 without '=' padding, as OpenSSH prints it. java.util.Base64 needs API 26 and minSdk is 22. */
private fun base64NoPadding(data: ByteArray): String {
	val out = StringBuilder()
	var i = 0
	while (i < data.size) {
		val n = minOf(3, data.size - i)
		var triple = 0
		for (k in 0 until 3) {
			triple = (triple shl 8) or (if (k < n) (data[i + k].toInt() and 0xff) else 0)
		}
		for (k in 0..n) {
			out.append(BASE64_ALPHABET[(triple shr (18 - 6 * k)) and 63])
		}
		i += 3
	}
	return out.toString()
}

/**
 * Production [HostKeyReader]: one SSH handshake to port 22 that stops at the host key. The verifier refuses the key on
 * purpose, so the connection never reaches authentication. Blocking: call it off the main thread.
 */
class SshHostKeyReader(private val timeoutMs: Int = 5_000) : HostKeyReader {
	override fun fingerprint(host: String): String? {
		// sshj needs the full BouncyCastle, not the cut-down copy Android ships under the same name (as SshUploader).
		Security.removeProvider("BC")
		Security.insertProviderAt(BouncyCastleProvider(), 1)
		var seen: String? = null
		val client = SSHClient()
		client.addHostKeyVerifier(object : HostKeyVerifier {
			override fun verify(hostname: String, port: Int, key: PublicKey): Boolean {
				seen = fingerprintOf(Buffer.PlainBuffer().putPublicKey(key).compactData)
				return false
			}

			override fun findExistingAlgorithms(hostname: String, port: Int): List<String> = emptyList()
		})
		client.connectTimeout = timeoutMs
		client.timeout = timeoutMs
		try {
			client.connect(host, 22)
		} catch (_: Exception) {
			// Expected: the verifier refuses every key, so connect always fails right after the host key.
		} finally {
			runCatching { client.disconnect() }
		}
		return seen
	}
}

/** Production [MdnsSource]: the MIA API scan the app already runs. */
class MdnsApiSource(private val mdns: MdnsDiscovery) : MdnsSource {
	override suspend fun discoverApi(timeoutMs: Long): List<String> = mdns.discoverApi(timeoutMs)
}
