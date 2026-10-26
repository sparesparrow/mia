package cz.mia.app.features.anpr

// @req REQ-AND-020

import cz.mia.app.core.security.PlateIdentity
import cz.mia.app.data.db.FakeAnprEventDao
import cz.mia.app.data.db.FakeWatchlistDao
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PlatesViewModelTest {
	private val dispatcher = UnconfinedTestDispatcher()
	private val watchlist = FakeWatchlistDao()
	private val sightings = FakeAnprEventDao()
	private val identity = PlateIdentity { ByteArray(32) { 3 } }
	private lateinit var vm: PlatesViewModel

	@Before
	fun setUp() {
		Dispatchers.setMain(dispatcher)
		vm = PlatesViewModel(watchlist, sightings, identity, now = { 1_000L }, io = dispatcher)
	}

	@After
	fun tearDown() {
		Dispatchers.resetMain()
	}

	@Test
	fun `a typed plate is stored only as the hash the camera would make`() = runTest(dispatcher) {
		assertEquals(AddPlateResult.Added, vm.addTyped("2ab 1234", "  the   neighbour "))

		val entry = vm.entries.value.single()
		assertEquals(identity.hash("2AB1234"), entry.plateHash)
		assertEquals("the neighbour", entry.label)
		assertEquals(1_000L, entry.addedAt)
		assertFalse(entry.toString().contains("1234"))
	}

	@Test
	fun `text that cannot be a plate is refused and nothing is stored`() = runTest(dispatcher) {
		assertTrue(vm.addTyped("2A", "x") is AddPlateResult.Refused)
		assertTrue(vm.entries.value.isEmpty())
	}

	@Test
	fun `adding a listed plate again replaces its label, and remove deletes it`() = runTest(dispatcher) {
		vm.addTyped("2AB1234", "old")
		vm.addTyped("2AB 1234", "new")
		assertEquals(listOf("new"), vm.entries.value.map { it.label })

		vm.remove(identity.hash("2AB1234"))
		assertTrue(vm.entries.value.isEmpty())
	}

	@Test
	fun `labels are capped`() = runTest(dispatcher) {
		vm.addTyped("2AB1234", "x".repeat(100))
		assertEquals(PlatesViewModel.MAX_LABEL, vm.entries.value.single().label.length)
	}

	@Test
	fun `recent sightings are grouped by plate, newest first, and marked once listed`() = runTest(dispatcher) {
		sightings.seen("a", 10, 30)
		sightings.seen("b", 20)
		assertEquals(listOf("a" to 2, "b" to 1), vm.recent.value.map { it.plateHash to it.sightings })
		assertFalse(vm.recent.value.first().listed)

		vm.addSighting("a", "picked")
		assertTrue(vm.recent.value.first { it.plateHash == "a" }.listed)
		assertEquals("picked", vm.entries.value.single().label)
	}
}
