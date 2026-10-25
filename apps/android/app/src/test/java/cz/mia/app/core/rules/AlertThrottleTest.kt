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
	fun `a fired condition is not raised again while it holds or hovers between limit and clear value`() {
		at(0, 110.0)
		at(10_000, 110.0)
		assertTrue(at(20_000, 115.0).isEmpty())
		assertTrue(at(30_000, 102.0).isEmpty())
		assertTrue(at(40_000, 110.0).isEmpty())
		assertTrue(throttle.isActive(CarCondition.ENGINE_OVERHEAT))
	}

	@Test
	fun `a critical condition is repeated every minute while it stays past its limit`() {
		at(0, 110.0)
		at(10_000, 110.0)
		assertTrue(at(69_999, 111.0).isEmpty())
		assertEquals(listOf(ThrottleEvent.Reminder(CarCondition.ENGINE_OVERHEAT, 112.0)), at(70_000, 112.0))
		assertTrue(at(129_999, 112.0).isEmpty())
		assertEquals(listOf(ThrottleEvent.Reminder(CarCondition.ENGINE_OVERHEAT, 113.0)), at(130_000, 113.0))
	}

	@Test
	fun `a warning is repeated every five minutes while it stays past its limit`() {
		fun rpm(ms: Long, value: Double): List<ThrottleEvent> {
			time = ms
			return throttle.update(listOf(ConditionReading.of(CarCondition.RPM_HIGH, value)))
		}
		rpm(0, 6400.0)
		assertEquals(listOf(ThrottleEvent.Activated(CarCondition.RPM_HIGH, 6400.0)), rpm(3_000, 6400.0))
		assertTrue(rpm(302_999, 6400.0).isEmpty())
		assertEquals(listOf(ThrottleEvent.Reminder(CarCondition.RPM_HIGH, 6300.0)), rpm(303_000, 6300.0))
	}

	@Test
	fun `there is no reminder in the band, while clearing or without data, but one is due on the way back up`() {
		at(0, 110.0)
		at(10_000, 110.0)
		assertTrue(at(70_000, 102.0).isEmpty())
		assertTrue(at(71_000, 95.0).isEmpty())
		assertTrue(at(72_000, null).isEmpty())
		assertEquals(listOf(ThrottleEvent.Reminder(CarCondition.ENGINE_OVERHEAT, 108.0)), at(73_000, 108.0))
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
		assertEquals(listOf(ThrottleEvent.Activated(CarCondition.ENGINE_OVERHEAT, 110.0)), at(30_000, 110.0))
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
