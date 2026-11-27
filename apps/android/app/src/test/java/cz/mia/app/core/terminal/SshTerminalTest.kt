package cz.mia.app.core.terminal

// @req REQ-AND-029

import cz.mia.app.core.onboarding.KnownPi
import cz.mia.app.core.onboarding.fingerprintOf
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class SshTerminalTest {
	private fun wire(type: String, body: ByteArray): ByteArray {
		val out = ByteArrayOutputStream()
		fun string(b: ByteArray) {
			out.write(byteArrayOf((b.size ushr 24).toByte(), (b.size ushr 16).toByte(), (b.size ushr 8).toByte(), b.size.toByte()))
			out.write(b)
		}
		string(type.toByteArray())
		string(body)
		return out.toByteArray()
	}

	private val keyA = wire("ssh-ed25519", ByteArray(32) { 1 })
	private val keyB = wire("ssh-ed25519", ByteArray(32) { 2 })
	private fun pins(): File = File(Files.createTempDirectory("pins").toFile(), "terminal_hosts")

	@Test
	fun firstConnection_pinsTheKey_andTheSameKeyIsKnownLater() {
		val file = pins()
		val keys = TerminalHostKeys(file)
		assertTrue(keys.check("10.0.0.5", 22, keyA))
		assertEquals(HostKeyCheck.New(fingerprintOf(keyA)), keys.lastCheck)
		assertTrue(TerminalHostKeys(file).let { it.check("10.0.0.5", 22, keyA) && it.lastCheck is HostKeyCheck.Known })
	}

	@Test
	fun aDifferentKey_isRefused_untilThePinIsForgotten() {
		val keys = TerminalHostKeys(pins())
		keys.check("pi", 22, keyA)
		assertFalse(keys.check("pi", 22, keyB))
		assertEquals(HostKeyCheck.Changed(fingerprintOf(keyA), fingerprintOf(keyB)), keys.lastCheck)
		keys.forget("pi", 22)
		assertTrue(keys.check("pi", 22, keyB))
		assertTrue(keys.lastCheck is HostKeyCheck.New)
	}

	@Test
	fun pinsArePerHostAndPort() {
		val keys = TerminalHostKeys(pins())
		keys.check("pi", 22, keyA)
		assertTrue(keys.check("pi", 2222, keyB))
		assertTrue(keys.check("other", 22, keyB))
		assertFalse(keys.check("pi", 22, keyB))
	}

	@Test
	fun aPiFromTheOnboardingWizard_isPinnedToItsVouchedFingerprint_fromTheFirstConnection() {
		val keys = TerminalHostKeys(pins()) { listOf(KnownPi(fingerprintOf(keyA), "192.168.4.1")) }
		assertFalse(keys.check("192.168.4.1", 22, keyB))
		assertTrue(keys.lastCheck is HostKeyCheck.Changed)
		assertTrue(keys.check("192.168.4.1", 22, keyA))
		assertTrue(keys.lastCheck is HostKeyCheck.Known)
	}

	@Test
	fun nonEd25519Keys_andUnreadableKeys_areRefused() {
		val keys = TerminalHostKeys(pins())
		assertFalse(keys.check("pi", 22, wire("ssh-rsa", ByteArray(64))))
		assertEquals(HostKeyCheck.Unsupported, keys.lastCheck)
		assertFalse(keys.check("pi", 22, null))
	}

	@Test
	fun utf8Chunker_keepsAMultiByteCharacterSplitAcrossReads() {
		val bytes = "é✓x".toByteArray(Charsets.UTF_8) // 2 + 3 + 1 bytes
		val chunker = Utf8Chunker()
		val parts = listOf(bytes.copyOfRange(0, 1), bytes.copyOfRange(1, 3), bytes.copyOfRange(3, 4), bytes.copyOfRange(4, 6))
		assertEquals("é✓x", parts.joinToString("") { chunker.decode(it) })
	}

	@Test
	fun utf8Chunker_handlesMoreThanItsBufferAtOnce() {
		val text = "ab✓".repeat(5000)
		assertEquals(text, Utf8Chunker().decode(text.toByteArray(Charsets.UTF_8)))
	}

	@Test
	fun target_acceptsLoginNames_andRefusesShellTricks() {
		assertEquals("mia", SshTarget("10.0.0.5").user)
		assertThrows(IllegalArgumentException::class.java) { SshTarget("pi", 22, "mia; reboot") }
		assertThrows(IllegalArgumentException::class.java) { SshTarget("pi", 0) }
		assertThrows(IllegalArgumentException::class.java) { SshTarget(" ") }
	}

	@Test
	fun passwordAuth_neverPrintsThePassword() {
		assertFalse(SshAuth.Password("hunter2").toString().contains("hunter2"))
	}

	@Test
	fun terminalClient_offersEd25519First_andCanSignWithTheEcPhoneKey() {
		// sshj signs the user's key only with an algorithm in this list: without ECDSA P-256 the phone key is never offered.
		val names = newTerminalSshClient().transport.config.keyAlgorithms.map { it.name }
		assertEquals(listOf("ssh-ed25519", "ecdsa-sha2-nistp256"), names)
	}
}
