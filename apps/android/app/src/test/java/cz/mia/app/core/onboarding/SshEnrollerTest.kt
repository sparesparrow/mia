package cz.mia.app.core.onboarding

// @req REQ-ONB-008

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The parts of the SSH enroller that need no network: reading the answer and pinning the host key. */
class SshEnrollerTest {
	private fun wire(type: String, key: ByteArray): ByteArray {
		fun field(b: ByteArray) = byteArrayOf(0, 0, (b.size shr 8).toByte(), b.size.toByte()) + b
		return field(type.toByteArray(Charsets.US_ASCII)) + field(key)
	}

	private val ed = wire("ssh-ed25519", ByteArray(32) { it.toByte() })
	private val otherEd = wire("ssh-ed25519", ByteArray(32) { (it + 1).toByte() })
	private val rsa = wire("ssh-rsa", ByteArray(32) { it.toByte() })

	@Test
	fun parseTakesTheLastJsonLineAndIgnoresNoise() {
		val out = "Welcome to MIA\n{\"ok\": false, \"step\": \"early\", \"error\": \"old\"}\nwarning: x\n" +
			"{\"ok\": true, \"step\": \"enrolled\", \"error\": null, \"warning\": \"registry busy\"}\n\n"
		assertEquals(EnrollOutcome(true, "enrolled", null, "registry busy"), EnrollOutcome.parse(out, 0))
	}

	@Test
	fun parseReportsErrorsAndNeverTrustsAMissingOrBadLine() {
		assertEquals(
			EnrollOutcome(false, "grant", "grant expired", null),
			EnrollOutcome.parse("{\"ok\": false, \"step\": \"grant\", \"error\": \"grant expired\"}", 1),
		)
		assertFalse(EnrollOutcome.parse("{\"ok\": true, \"step\": \"enrolled\", \"error\": null}", 1).ok) // exit status wins
		assertEquals("no_result", EnrollOutcome.parse("banner only\n", 0).step)
		assertEquals("bad_result", EnrollOutcome.parse("{not json", 0).step)
		assertEquals("bad_result", EnrollOutcome.parse("{\"step\": \"x\"}", 0).step)
	}

	@Test
	fun verifierAcceptsOnlyTheExpectedEd25519Fingerprint() {
		val verifier = FingerprintPinVerifier(fingerprintOf(ed))
		assertTrue(verifier.accepts(ed))
		assertFalse(verifier.accepts(otherEd))
		assertFalse(verifier.accepts(rsa))
		assertFalse(verifier.accepts(ByteArray(0)))
		assertNull(ed25519FingerprintOrNull(rsa))
		assertFalse(FingerprintPinVerifier("SHA256:" + "A".repeat(43)).accepts(ed))
	}
}
