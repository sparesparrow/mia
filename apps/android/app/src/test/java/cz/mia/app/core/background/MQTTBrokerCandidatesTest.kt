package cz.mia.app.core.background

// @req REQ-AND-006

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MQTTBrokerCandidatesTest {
	@Test
	fun noCandidates_whenNothingIsConfiguredOrDiscovered() {
		assertTrue(buildBrokerCandidates(null, emptyList(), emptyList()).isEmpty())
	}

	@Test
	fun neverFallsBackToAPublicBroker() {
		val candidates = buildBrokerCandidates(null, listOf(":1883", ""), listOf(""))
		assertTrue(candidates.isEmpty())
		assertFalse(candidates.any { it.contains("mosquitto.org") })
	}

	@Test
	fun explicitUrlComesFirst_thenMdns_thenCache() {
		val candidates = buildBrokerCandidates("ssl://mia.local:8883", listOf("192.168.1.10:1884"), listOf("192.168.1.11"))
		assertEquals(
			listOf("ssl://mia.local:8883", "tcp://192.168.1.10:1884", "tcp://192.168.1.11:1883"),
			candidates
		)
	}

	@Test
	fun mdnsEntryWithoutPort_defaultsTo1883() {
		assertEquals(listOf("tcp://192.168.1.10:1883"), buildBrokerCandidates(null, listOf("192.168.1.10"), emptyList()))
	}

	@Test
	fun duplicates_areRemoved() {
		val candidates = buildBrokerCandidates(null, listOf("192.168.1.10:1883"), listOf("192.168.1.10"))
		assertEquals(listOf("tcp://192.168.1.10:1883"), candidates)
	}
}
