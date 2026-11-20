package cz.mia.app.core.onboarding

import cz.mia.app.core.networking.MdnsDiscovery
import java.security.MessageDigest
import java.security.PublicKey
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.runInterruptible
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import net.schmizz.sshj.common.Buffer
import net.schmizz.sshj.transport.verification.HostKeyVerifier

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

/**
 * Reads a host's ssh-ed25519 host-key fingerprint in the OpenSSH form `SHA256:<base64>`. Contract: returns the ed25519
 * fingerprint or null (unreadable, negotiation failed, or the host offered no ed25519 key); never another key type's
 * fingerprint, because the server registers only the fingerprint of /etc/ssh/ssh_host_ed25519_key.pub.
 */
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
	private val probeGraceMs: Long = MAX_PROBE_GRACE_MS,
	private val trustedDeviceFps: () -> Set<String>,
) {
	/**
	 * Probes the mDNS hits one by one and returns those whose fingerprint is trusted.
	 *
	 * Deadline: [timeoutMs] plus the probe grace. It is a soft bound. Cancelling interrupts the probing thread, but
	 * Thread.interrupt does not unblock a plain java.net.Socket connect or read, so a probe already in flight runs on
	 * until its own limits. Worst case for [find] = timeoutMs + grace + connectTimeout + timeout of the host in flight
	 * (with [SshHostKeyReader] defaults: timeoutMs + up to 5 s + 5 s + 5 s). No further host is started after the
	 * deadline. A reader that throws InterruptedException also stops the loop; hosts found so far are returned.
	 */
	suspend fun find(timeoutMs: Long): List<FoundPi> {
		// mDNS gives "host:port" for the API port; the SSH probe below always uses port 22, so only the host is kept.
		val hosts = mdns.discoverApi(timeoutMs)
			.map { it.substringBeforeLast(':') }
			.filter { it.isNotEmpty() }
			.distinct()
			.take(MAX_PROBE_HOSTS)
		if (hosts.isEmpty()) return emptyList()
		// The probe phase gets the same budget as the scan, plus at most MAX_PROBE_GRACE_MS; hosts past it are dropped.
		val deadlineMs = timeoutMs.coerceAtLeast(0) + probeGraceMs.coerceIn(0, MAX_PROBE_GRACE_MS)
		// The trusted set may come from a blocking call (AuthServerClient.devices) and each host-key read blocks on the
		// network, so both run off the caller's dispatcher.
		return withContext(Dispatchers.IO) {
			val trusted = trustedDeviceFps()
			if (trusted.isEmpty()) return@withContext emptyList()
			val found = mutableListOf<FoundPi>()
			withTimeoutOrNull(deadlineMs) {
				for (host in hosts) {
					// runInterruptible interrupts the blocking read when the deadline cancels this scope.
					val fp = try {
						runInterruptible { readOrNull(host) }
					} catch (e: CancellationException) {
						// runInterruptible turns an InterruptedException into a CancellationException. If this scope is
						// still active (deadline not hit, caller not cancelled) the interrupt came from the reader: stop
						// probing and keep what was found. Otherwise ensureActive rethrows the real cancellation.
						ensureActive()
						break
					}
					if (fp != null && fp in trusted) found += FoundPi(host, classify(host), fp)
				}
			}
			found.toList()
		}
	}

	private fun readOrNull(host: String): String? =
		try {
			hostKeyReader.fingerprint(host)
		} catch (e: CancellationException) {
			throw e
		} catch (e: InterruptedException) {
			throw e
		} catch (_: Exception) {
			null
		} catch (_: LinkageError) {
			// Includes NoClassDefFoundError when a crypto provider class is missing.
			null
		}

	private companion object {
		const val MAX_PROBE_HOSTS = 8
		const val MAX_PROBE_GRACE_MS = 5_000L
	}
}

/**
 * Maps a Pi's address to how the phone reaches it: 192.168.4.x is the Pi's own MIA Wi-Fi, 192.168.42.x is the USB
 * tether, and everything else (10.15.60.x, Android hotspots, iOS hotspot 172.20.10.x, any other range) is
 * [Transport.Hotspot].
 */
fun classify(host: String): Transport {
	val parts = host.split('.')
	if (parts.size != 4 || parts.any { it.toIntOrNull() == null }) return Transport.Hotspot
	val (a, b, c) = parts.map { it.toInt() }
	return when {
		a == 192 && b == 168 && c == 4 -> Transport.MiaWifi
		a == 192 && b == 168 && c == 42 -> Transport.Usb
		else -> Transport.Hotspot
	}
}

/** The OpenSSH fingerprint of a public key: `SHA256:` plus SHA-256 of the SSH wire blob, base64 without padding. */
internal fun fingerprintOf(wireBlob: ByteArray): String =
	"SHA256:" + base64NoPadding(MessageDigest.getInstance("SHA-256").digest(wireBlob))

private const val BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

/** The fingerprint of an SSH wire blob only when it is an `ssh-ed25519` key, else null (REQ-ONB-008: ed25519 only). */
internal fun ed25519FingerprintOrNull(wireBlob: ByteArray): String? {
	if (wireBlob.size < 4) return null
	val len = ((wireBlob[0].toInt() and 0xff) shl 24) or ((wireBlob[1].toInt() and 0xff) shl 16) or
		((wireBlob[2].toInt() and 0xff) shl 8) or (wireBlob[3].toInt() and 0xff)
	if (len != ED25519_TYPE.length || wireBlob.size < 4 + len) return null
	if (String(wireBlob, 4, len, Charsets.US_ASCII) != ED25519_TYPE) return null
	return fingerprintOf(wireBlob)
}

private const val ED25519_TYPE = "ssh-ed25519"

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
 *
 * Time bound: one call takes at most connectTimeout + timeout of sshj, i.e. 2 * [timeoutMs] (10 s by default). Thread
 * interrupt does not unblock the plain socket connect/read underneath, so cancelling [PiDiscovery.find] does not shorten
 * a call already in flight; that remainder is the extra on top of find's deadline.
 */
class SshHostKeyReader(private val timeoutMs: Int = 5_000) : HostKeyReader {
	override fun fingerprint(host: String): String? {
		try {
			val seen = AtomicReference<String?>(null) // written on sshj's reader thread, read here
			// Only ssh-ed25519 is offered as host-key algorithm: a Pi without that key fails negotiation, which is null.
			val client = newEd25519SshClient()
			client.addHostKeyVerifier(object : HostKeyVerifier {
				override fun verify(hostname: String, port: Int, key: PublicKey): Boolean {
					seen.set(ed25519FingerprintOrNull(Buffer.PlainBuffer().putPublicKey(key).compactData))
					return false
				}

				override fun findExistingAlgorithms(hostname: String, port: Int): List<String> = emptyList()
			})
			client.connectTimeout = timeoutMs
			client.timeout = timeoutMs
			try {
				client.connect(host, 22)
			} catch (e: InterruptedException) {
				throw e
			} catch (_: Exception) {
				// Expected: the verifier refuses every key, so connect always fails right after the host key.
			} finally {
				runCatching { client.disconnect() }
			}
			return seen.get()
		} catch (e: InterruptedException) {
			throw e
		} catch (e: CancellationException) {
			throw e
		} catch (_: Exception) {
			return null
		} catch (_: LinkageError) {
			return null
		}
	}
}

/** Production [MdnsSource]: the MIA API scan the app already runs. */
class MdnsApiSource(private val mdns: MdnsDiscovery) : MdnsSource {
	override suspend fun discoverApi(timeoutMs: Long): List<String> = mdns.discoverApi(timeoutMs)
}
