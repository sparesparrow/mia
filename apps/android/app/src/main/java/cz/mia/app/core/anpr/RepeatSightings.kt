package cz.mia.app.core.anpr

/**
 * Whether one plate keeps turning up (REQ-AND-021). Sightings less than [episodeGapMs] apart are one episode, since a
 * car in the next lane is read many times a minute. A plate counts as repeated once it has [minEpisodes] episodes and
 * its sightings span [minSpanMs] or more.
 *
 * Starting values, not tuned in a car: 5 min, 3 episodes, 15 min.
 */
object RepeatSightings {
	const val EPISODE_GAP_MS = 5 * 60_000L
	const val MIN_EPISODES = 3
	const val MIN_SPAN_MS = 15 * 60_000L

	/** The start of each episode, given sighting times in any order. */
	fun episodeStarts(times: List<Long>, episodeGapMs: Long = EPISODE_GAP_MS): List<Long> {
		val sorted = times.sorted()
		val starts = mutableListOf<Long>()
		var last: Long? = null
		for (t in sorted) {
			if (last == null || t - last >= episodeGapMs) starts += t
			last = t
		}
		return starts
	}

	fun isRepeated(
		times: List<Long>,
		episodeGapMs: Long = EPISODE_GAP_MS,
		minEpisodes: Int = MIN_EPISODES,
		minSpanMs: Long = MIN_SPAN_MS,
	): Boolean {
		if (times.isEmpty()) return false
		if (episodeStarts(times, episodeGapMs).size < minEpisodes) return false
		return times.max() - times.min() >= minSpanMs
	}
}
