package cz.mia.app.core.security

// @req REQ-AND-004 REQ-AND-020

import cz.mia.app.core.camera.AnprPostprocessor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PlateIdentityTest {
	private val key = ByteArray(32) { it.toByte() }
	private val identity = PlateIdentity { key }

	/** What ANPRManager hashes for a camera reading. */
	private fun fromCamera(ocr: String): String = identity.hash(AnprPostprocessor.applyRegionHeuristics(ocr, "CZ").first)

	@Test
	fun `a typed plate and the camera's reading of it give the same hash`() {
		val camera = fromCamera("2AB 1234")
		assertEquals(camera, identity.hash("2AB 1234"))
		assertEquals(camera, identity.hash("2ab-1234"))
		assertEquals(camera, identity.hash(" 2AB1234 "))
	}

	@Test
	fun `another install's key gives another hash`() {
		val other = PlateIdentity { ByteArray(32) { 7 } }
		assertNotEquals(identity.hash("2AB1234"), other.hash("2AB1234"))
	}

	@Test
	fun `the hash does not contain the plate`() {
		assertFalse(identity.hash("2AB1234").contains("2AB1234"))
		assertFalse(identity.hash("2AB1234").contains("2A81234"))
	}

	@Test
	fun `O and 0, B and 8 hash alike, as the camera confuses them`() {
		assertEquals(identity.hash("2AB1234"), identity.hash("2A81234"))
		assertEquals(identity.hash("1O01000"), identity.hash("1001000"))
	}

	@Test
	fun `only text that can be a plate is accepted`() {
		assertTrue(identity.isPlausible("2AB 1234"))
		assertTrue(identity.isPlausible("ab-123"))
		assertFalse(identity.isPlausible("2AB"))
		assertFalse(identity.isPlausible("2AB_1234"))
		assertFalse(identity.isPlausible("12345678901"))
		assertFalse(identity.isPlausible("   "))
	}
}
