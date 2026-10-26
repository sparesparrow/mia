package cz.mia.app.core.rules

import cz.mia.app.core.background.AlertSeverity

/** What an [AlertThrottle] update decided for one condition. */
sealed class ThrottleEvent {
	abstract val condition: CarCondition

	/** The condition has been past its limit for its dwell time: warn. */
	data class Activated(override val condition: CarCondition, val value: Double) : ThrottleEvent()

	/** The warned condition is still past its limit after its repeat interval: remind. */
	data class Reminder(override val condition: CarCondition, val value: Double) : ThrottleEvent()

	/** The condition cleared (or its data went away): withdraw the warning. */
	data class Cleared(override val condition: CarCondition) : ThrottleEvent()
}

/**
 * Decides when a reading becomes a warning, so one overheating engine is one warning and not one per reading.
 *
 * - A condition must stay past its limit for its dwell time before it fires; a dip back below the limit restarts
 *   the wait.
 * - A fired condition does not fire again until it has been back past its clear value for [rearmMs].
 *   Values between the limit and the clear value keep the current state.
 * - While a fired condition stays past its limit it is repeated as a reminder, every [criticalRepeatMs] for a
 *   critical one and every [warningRepeatMs] otherwise. In the band or while clearing there is no reminder.
 * - Unknown readings change nothing, but a condition with no known reading for [unknownResetMs] resets
 *   silently (a fired one is withdrawn).
 * - Readings for the same condition from two sources (Pi and BLE adapter) feed one state: the latest known
 *   reading wins.
 *
 * Not thread-safe; callers serialise updates.
 */
class AlertThrottle(
	private val now: () -> Long,
	private val rearmMs: Long = 5_000,
	private val unknownResetMs: Long = 60_000,
	private val criticalRepeatMs: Long = 60_000,
	private val warningRepeatMs: Long = 300_000,
) {
	private enum class Phase { IDLE, PENDING, ACTIVE, CLEARING }

	private data class Track(
		var phase: Phase = Phase.IDLE,
		var since: Long = 0,
		var lastKnown: Long = 0,
		var announcedAt: Long = 0,
	)

	private val tracks = mutableMapOf<CarCondition, Track>()

	fun isActive(condition: CarCondition): Boolean =
		tracks[condition]?.phase.let { it == Phase.ACTIVE || it == Phase.CLEARING }

	fun update(readings: List<ConditionReading>): List<ThrottleEvent> {
		val time = now()
		val events = mutableListOf<ThrottleEvent>()
		for (reading in readings) {
			val track = tracks.getOrPut(reading.condition) { Track(lastKnown = time) }
			step(reading, track, time)?.let { events += it }
		}
		return events
	}

	private fun step(reading: ConditionReading, track: Track, time: Long): ThrottleEvent? {
		val condition = reading.condition
		if (reading.level == ReadingLevel.UNKNOWN) {
			if (track.phase != Phase.IDLE && time - track.lastKnown >= unknownResetMs) {
				val wasFired = track.phase == Phase.ACTIVE || track.phase == Phase.CLEARING
				track.phase = Phase.IDLE
				return if (wasFired) ThrottleEvent.Cleared(condition) else null
			}
			return null
		}
		track.lastKnown = time
		val level = reading.level
		when (track.phase) {
			Phase.IDLE -> if (level == ReadingLevel.TRIGGERED) {
				track.phase = Phase.PENDING
				track.since = time
				return fireIfDwelled(reading, track, time)
			}
			Phase.PENDING -> return if (level == ReadingLevel.TRIGGERED) {
				fireIfDwelled(reading, track, time)
			} else {
				track.phase = Phase.IDLE
				null
			}
			Phase.ACTIVE -> when (level) {
				ReadingLevel.CLEAR -> {
					track.phase = Phase.CLEARING
					track.since = time
					return clearIfRearmed(condition, track, time)
				}
				ReadingLevel.TRIGGERED -> return remindIfDue(reading, track, time)
				else -> Unit
			}
			Phase.CLEARING -> return when (level) {
				ReadingLevel.CLEAR -> clearIfRearmed(condition, track, time)
				ReadingLevel.TRIGGERED -> {
					track.phase = Phase.ACTIVE
					remindIfDue(reading, track, time)
				}
				else -> {
					track.phase = Phase.ACTIVE
					null
				}
			}
		}
		return null
	}

	private fun fireIfDwelled(reading: ConditionReading, track: Track, time: Long): ThrottleEvent? {
		if (time - track.since < reading.condition.dwellMs) return null
		track.phase = Phase.ACTIVE
		track.announcedAt = time
		return ThrottleEvent.Activated(reading.condition, reading.value ?: return null)
	}

	private fun remindIfDue(reading: ConditionReading, track: Track, time: Long): ThrottleEvent? {
		val repeatMs = if (reading.condition.severity == AlertSeverity.CRITICAL) criticalRepeatMs else warningRepeatMs
		if (time - track.announcedAt < repeatMs) return null
		track.announcedAt = time
		return ThrottleEvent.Reminder(reading.condition, reading.value ?: return null)
	}

	private fun clearIfRearmed(condition: CarCondition, track: Track, time: Long): ThrottleEvent? {
		if (time - track.since < rearmMs) return null
		track.phase = Phase.IDLE
		return ThrottleEvent.Cleared(condition)
	}
}
