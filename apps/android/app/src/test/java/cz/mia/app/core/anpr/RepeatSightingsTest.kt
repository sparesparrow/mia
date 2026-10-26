package cz.mia.app.core.anpr

// @req REQ-AND-021

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

private const val MIN = 60_000L

class RepeatSightingsTest {
	@Test
	fun `reads close together are one episode`() {
		assertEquals(listOf(0L), RepeatSightings.episodeStarts(listOf(0L, 10_000L, 2 * MIN, 4 * MIN)))
	}

	@Test
	fun `five minutes after the last read starts a new episode, whatever the order of the times`() {
		assertEquals(listOf(0L, 6 * MIN, 20 * MIN), RepeatSightings.episodeStarts(listOf(20 * MIN, 6 * MIN, 0L, MIN)))
		assertEquals(listOf(0L), RepeatSightings.episodeStarts(listOf(0L, 4 * MIN, 8 * MIN, 12 * MIN)))
	}

	@Test
	fun `three episodes over fifteen minutes count as repeated`() {
		assertTrue(RepeatSightings.isRepeated(listOf(0L, 7 * MIN, 15 * MIN)))
	}

	@Test
	fun `two episodes, or three within fifteen minutes, do not`() {
		assertFalse(RepeatSightings.isRepeated(listOf(0L, 30 * MIN)))
		assertFalse(RepeatSightings.isRepeated(listOf(0L, 5 * MIN, 10 * MIN, 14 * MIN)))
		assertFalse(RepeatSightings.isRepeated((0L..20L).map { it * 30_000L }))
		assertFalse(RepeatSightings.isRepeated(emptyList()))
	}
}
