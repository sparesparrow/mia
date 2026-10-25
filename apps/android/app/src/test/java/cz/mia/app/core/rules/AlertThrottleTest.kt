package cz.mia.app.core.rules

// @req REQ-AND-019

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AlertThrottleTest {
	private var time = 0L
	private val throttle = AlertThrottle(now = { time })

	private fun coolant(value: Double?) = listOf(ConditionReading.of(CarCondition.ENGINE_OVERHEAT, value))

	private fun at(ms: Long, value: Double?): List<ThrottleEvent> {
		time = ms
		return throttle.update(coolant(value))
	}

	@Test
	fun `a condition fires only after it has held for its dwell time`() {
		assertTrue(at(0, 110.0).isEmpty())
		assertTrue(at(9_999, 110.0).isEmpty())
		assertEquals(listOf(ThrottleEvent.Activated(CarCondition.ENGINE_OVERHEAT, 112.0)), at(10_000, 112.0))
	}

	@Test
	fun `a dip below the limit restarts the dwell`() {
		at(0, 110.0)
		at(5_000, 103.0)
		assertTrue(at(10_000, 110.0).isEmpty())
		assertTrue(at(19_999, 110.0).isEmpty())
		assertEquals(1, at(20_000, 110.0).size)
	}

	@Test
	fun `a fired condition does not repeat while it holds or hovers between limit and clear value`() {
		at(0, 110.0)
		at(10_000, 110.0)
		assertTrue(at(20_000, 115.0).isEmpty())
		assertTrue(at(30_000, 102.0).isEmpty())
		assertTrue(at(40_000, 110.0).isEmpty())
		assertTrue(throttle.isActive(CarCondition.ENGINE_OVERHEAT))
	}

	@Test
	fun `it clears after five seconds back past the clear value, then can fire again`() {
		at(0, 110.0)
		at(10_000, 110.0)
		assertTrue(at(11_000, 95.0).isEmpty())
		assertTrue(at(15_999, 95.0).isEmpty())
		assertEquals(listOf(ThrottleEvent.Cleared(CarCondition.ENGINE_OVERHEAT)), at(16_000, 95.0))
		assertFalse(throttle.isActive(CarCondition.ENGINE_OVERHEAT))

		at(20_000, 110.0)
		assertEquals(1, at(30_000, 110.0).size)
	}

	@Test
	fun `a short clear does not re-arm it`() {
		at(0, 110.0)
		at(10_000, 110.0)
		at(11_000, 95.0)
		at(13_000, 110.0)
		assertTrue(at(30_000, 110.0).isEmpty())
	}

	@Test
	fun `unknown readings keep the state, and a minute without data withdraws a fired warning`() {
		at(0, 110.0)
		at(10_000, 110.0)
		assertTrue(at(40_000, null).isEmpty())
		assertTrue(throttle.isActive(CarCondition.ENGINE_OVERHEAT))
		assertEquals(listOf(ThrottleEvent.Cleared(CarCondition.ENGINE_OVERHEAT)), at(70_000, null))
		assertFalse(throttle.isActive(CarCondition.ENGINE_OVERHEAT))
	}

	@Test
	fun `two sources feed one state, so one overheating engine is one warning`() {
		time = 0
		throttle.update(coolant(110.0))
		throttle.update(coolant(111.0))
		time = 10_000
		val first = throttle.update(coolant(110.0))
		val second = throttle.update(coolant(111.0))
		assertEquals(1, first.size)
		assertTrue(second.isEmpty())
	}

	@Test
	fun `conditions are independent`() {
		time = 0
		throttle.update(listOf(ConditionReading.of(CarCondition.RPM_HIGH, 6500.0), ConditionReading.of(CarCondition.BATTERY_LOW, 11.0)))
		time = 3_000
		val events = throttle.update(listOf(ConditionReading.of(CarCondition.RPM_HIGH, 6500.0), ConditionReading.of(CarCondition.BATTERY_LOW, 11.0)))
		assertEquals(listOf(ThrottleEvent.Activated(CarCondition.RPM_HIGH, 6500.0)), events)
	}
}
