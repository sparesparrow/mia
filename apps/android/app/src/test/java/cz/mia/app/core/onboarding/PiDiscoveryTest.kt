package cz.mia.app.core.onboarding

// @req REQ-ONB-008

import java.util.Base64
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PiDiscoveryTest {
	/** Host-key fingerprints the auth server "returned": the ed25519 and ecdsa vectors below, from ssh-keygen -lf. */
	private val serverFp = "SHA256:BV5sCSaH1iH/isrgeu9HT1AbcE//5ZfENw2cH1swC2M"
	private val otherFp = "SHA256:W/v6ihpJBgYEEE4tsm2nTy32F8Ahbd/kb5u/lh/B5q8"

	private class FakeMdns(private val results: List<String>) : MdnsSource {
		val timeouts = mutableListOf<Long>()

		override suspend fun discoverApi(timeoutMs: Long): List<String> {
			timeouts += timeoutMs
			return results
		}
	}

	private class FakeReader(private val fps: Map<String, String?>) : HostKeyReader {
		/** Hosts the reader was asked about, in order: checks that the port was stripped before the probe. */
		val asked = mutableListOf<String>()

		override fun fingerprint(host: String): String? {
			asked += host
			return fps[host]
		}
	}

	private fun discovery(
		mdns: MdnsSource,
		reader: HostKeyReader,
		trusted: Set<String> = setOf(serverFp),
		graceMs: Long = 5_000,
	) = PiDiscovery(mdns, reader, graceMs) { trusted }

	@Test
	fun findsPiByMdnsOnHotspot() = runTest {
		val reader = FakeReader(mapOf("10.15.60.23" to serverFp))
		val found = discovery(FakeMdns(listOf("10.15.60.23:8000")), reader).find(2_000)
		assertEquals(listOf(FoundPi("10.15.60.23", Transport.Hotspot, serverFp)), found)
		assertEquals(listOf("10.15.60.23"), reader.asked)
	}

	@Test
	fun rejectsPiWhoseFingerprintDiffersFromServer() = runTest {
		val reader = FakeReader(mapOf("192.168.4.10" to otherFp))
		val found = discovery(FakeMdns(listOf("192.168.4.10:8000")), reader).find(2_000)
		assertTrue(found.isEmpty())
	}

	@Test
	fun returnsEmptyListOnTimeout() = runTest {
		val mdns = FakeMdns(emptyList())
		val reader = FakeReader(emptyMap())
		assertTrue(discovery(mdns, reader).find(1_500).isEmpty())
		assertEquals(listOf(1_500L), mdns.timeouts)
		assertTrue(reader.asked.isEmpty())
	}

	@Test
	fun ignoresPiWithUnreadableFingerprint() = runTest {
		val reader = FakeReader(mapOf("192.168.4.10" to null, "192.168.4.11" to serverFp))
		val found = discovery(FakeMdns(listOf("192.168.4.10:8000", "192.168.4.11:8000")), reader).find(2_000)
		assertEquals(listOf(FoundPi("192.168.4.11", Transport.MiaWifi, serverFp)), found)
	}

	@Test
	fun noTrustedKeysMeansNothingIsProbedAsTrusted() = runTest {
		val reader = FakeReader(mapOf("192.168.4.10" to serverFp))
		val found = discovery(FakeMdns(listOf("192.168.4.10:8000")), reader, trusted = emptySet()).find(2_000)
		assertTrue(found.isEmpty())
		assertTrue(reader.asked.isEmpty())
	}

	@Test
	fun nonEd25519FingerprintIsNeverTheDeviceFingerprint() {
		val ed25519 = "AAAAC3NzaC1lZDI1NTE5AAAAIDJKjSr5pRN7/1whkiT/EK19tRzb8EU0hEng4Ghz87/p"
		val ecdsa = "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBGE5ONQtgU1d1qxMMoYihyI7lqoayGhnOKJNeeQr489I+M1XaJ8oDbVqWwCg9MP/RLxKd+CwtnYGfPh6Z3KPXg8="
		assertEquals(serverFp, ed25519FingerprintOrNull(Base64.getDecoder().decode(ed25519)))
		assertNull(ed25519FingerprintOrNull(Base64.getDecoder().decode(ecdsa)))
		assertNull(ed25519FingerprintOrNull(ByteArray(0)))
	}

	@Test
	fun readerThatFailsOrIsMissingClassesCountsAsUnreadable() = runTest {
		val reader = HostKeyReader { host ->
			if (host == "192.168.4.10") throw NoClassDefFoundError("x") else throw IllegalStateException("boom")
		}
		val found = discovery(FakeMdns(listOf("192.168.4.10:8000", "192.168.4.11:8000")), reader).find(2_000)
		assertTrue(found.isEmpty())
	}

	@Test
	fun probesAtMostEightHosts() = runTest {
		val hosts = (1..12).map { "10.0.0.$it" }
		val reader = FakeReader(hosts.associateWith { serverFp })
		discovery(FakeMdns(hosts.map { "$it:8000" }), reader).find(2_000)
		assertEquals(hosts.take(8), reader.asked)
	}

	// The slow probe is an interruptible fake (Thread.sleep): this proves the loop stops at the deadline, not that a
	// thread blocked in a plain socket connect/read is interrupted (it is not; see PiDiscovery.find KDoc).
	@Test
	fun slowInterruptibleProbesAreCutOffAtTheDeadline() = runTest {
		val asked = java.util.Collections.synchronizedList(mutableListOf<String>())
		val reader = HostKeyReader { host ->
			asked += host
			if (host == "10.0.0.2") Thread.sleep(30_000)
			serverFp
		}
		val mdns = FakeMdns(listOf("10.0.0.1:8000", "10.0.0.2:8000", "10.0.0.3:8000"))
		val start = System.nanoTime()
		val found = discovery(mdns, reader, graceMs = 0).find(300)
		val elapsedMs = (System.nanoTime() - start) / 1_000_000
		assertEquals(listOf(FoundPi("10.0.0.1", Transport.Hotspot, serverFp)), found)
		assertEquals(listOf("10.0.0.1", "10.0.0.2"), asked.toList())
		assertTrue("probe was interrupted, took $elapsedMs ms", elapsedMs < 10_000)
	}

	@Test
	fun readerThrowingInterruptedExceptionStopsProbingAndKeepsFoundHosts() = runTest {
		val asked = java.util.Collections.synchronizedList(mutableListOf<String>())
		val reader = HostKeyReader { host ->
			asked += host
			if (host == "10.0.0.2") throw InterruptedException("simulated")
			serverFp
		}
		val mdns = FakeMdns(listOf("10.0.0.1:8000", "10.0.0.2:8000", "10.0.0.3:8000"))
		val found = discovery(mdns, reader).find(5_000)
		assertEquals(listOf(FoundPi("10.0.0.1", Transport.Hotspot, serverFp)), found)
		assertEquals(listOf("10.0.0.1", "10.0.0.2"), asked.toList())
	}

	@Test
	fun classifyUsesAddressRanges() {
		assertEquals(Transport.MiaWifi, classify("192.168.4.1"))
		assertEquals(Transport.MiaWifi, classify("192.168.4.254"))
		assertEquals(Transport.Usb, classify("192.168.42.129"))
		assertEquals(Transport.Hotspot, classify("172.20.10.2"))
		assertEquals(Transport.Hotspot, classify("172.16.0.9"))
		assertEquals(Transport.Hotspot, classify("10.15.60.23"))
		assertEquals(Transport.Hotspot, classify("192.168.43.5"))
		assertEquals(Transport.Hotspot, classify("192.168.1.20"))
		assertEquals(Transport.Hotspot, classify("mia.local"))
	}

	@Test
	fun fingerprintMatchesOpenSshKeygen() {
		// Public key blobs from `ssh-keygen -t ed25519` and `ssh-keygen -t ecdsa -b 256`; expected values are `ssh-keygen -lf`.
		val ed25519 = "AAAAC3NzaC1lZDI1NTE5AAAAIDJKjSr5pRN7/1whkiT/EK19tRzb8EU0hEng4Ghz87/p"
		val ecdsa = "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBGE5ONQtgU1d1qxMMoYihyI7lqoayGhnOKJNeeQr489I+M1XaJ8oDbVqWwCg9MP/RLxKd+CwtnYGfPh6Z3KPXg8="
		assertEquals(serverFp, fingerprintOf(Base64.getDecoder().decode(ed25519)))
		assertEquals(otherFp, fingerprintOf(Base64.getDecoder().decode(ecdsa)))
	}
}
