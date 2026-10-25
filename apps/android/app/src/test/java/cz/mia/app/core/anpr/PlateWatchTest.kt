package cz.mia.app.core.anpr

// @req REQ-AND-020 REQ-AND-021

import cz.mia.app.data.db.FakeAnprEventDao
import cz.mia.app.data.db.FakeWatchlistDao
import cz.mia.app.data.db.WatchlistEntity
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private const val MIN = 60_000L
private const val HOUR = 60 * MIN

class PlateWatchTest {
	private var time = 0L
	private val watchlist = FakeWatchlistDao()
	private val sightings = FakeAnprEventDao()
	private val watch = PlateWatch(watchlist, sightings, now = { time })

	private fun at(ms: Long, plateHash: String): PlateAlert? = runBlocking {
		time = ms
		sightings.seen(plateHash, ms)
		watch.check(plateHash)
	}

	private fun list(plateHash: String, label: String) = runBlocking {
		watchlist.upsert(WatchlistEntity(plateHash, label, 0))
	}

	@Test
	fun `a black-book plate is announced with its label, then not again for ten minutes`() {
		list("h1", "soused")
		assertEquals(PlateAlert.Listed("h1", "soused"), at(0, "h1"))
		assertNull(at(2 * MIN, "h1"))
		assertNull(at(9 * MIN, "h1"))
		assertEquals(PlateAlert.Listed("h1", "soused"), at(10 * MIN, "h1"))
	}

	@Test
	fun `a black-book plate is never announced as repeated`() {
		list("h1", "")
		at(0, "h1")
		val later = listOf(10 * MIN, 20 * MIN, 30 * MIN).map { at(it, "h1") }
		assertTrue(later.all { it == null || it is PlateAlert.Listed })
	}

	@Test
	fun `another plate is announced once it has three episodes over fifteen minutes`() {
		assertNull(at(0, "h2"))
		assertNull(at(MIN, "h2"))
		assertNull(at(8 * MIN, "h2"))
		assertEquals(PlateAlert.Repeated("h2", episodes = 3, spanMs = 16 * MIN), at(16 * MIN, "h2"))
	}

	@Test
	fun `a repeated plate is announced at most once a day`() {
		at(0, "h2")
		at(7 * MIN, "h2")
		assertTrue(at(15 * MIN, "h2") is PlateAlert.Repeated)
		assertNull(at(30 * MIN, "h2"))
		assertNull(at(23 * HOUR, "h2"))

		// A day after the alert the plate still has three episodes in the last 24 h: 15 min, 30 min and 23 h.
		assertEquals(PlateAlert.Repeated("h2", episodes = 4, spanMs = 24 * HOUR), at(24 * HOUR + 15 * MIN, "h2"))
	}

	@Test
	fun `sightings older than a day do not count`() {
		at(0, "h3")
		at(10 * MIN, "h3")
		assertNull(at(25 * HOUR, "h3"))
	}

	@Test
	fun `the words name the label and the count, never the plate`() {
		assertEquals("Auto z černé knihy: soused.", PlateAlertText.render(PlateAlert.Listed("h", " soused "), "cs"))
		assertEquals("Black-book car.", PlateAlertText.render(PlateAlert.Listed("h", ""), "en"))
		assertEquals(
			"Stejné auto vidím už 3krát za 16 minut.",
			PlateAlertText.render(PlateAlert.Repeated("h", 3, 16 * MIN), "cs"),
		)
		assertEquals(
			"Same car seen 4 times in 3 hours.",
			PlateAlertText.render(PlateAlert.Repeated("h", 4, 3 * HOUR + 5 * MIN), "en"),
		)
		assertEquals("Stejné auto vidím už 5krát za 6 hodin.", PlateAlertText.render(PlateAlert.Repeated("h", 5, 6 * HOUR), "cs"))
	}
}
