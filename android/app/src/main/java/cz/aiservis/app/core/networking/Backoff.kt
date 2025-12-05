package cz.aiservis.app.core.networking

object Backoff {
	fun linearDelays(vararg delaysMs: Long): List<Long> = delaysMs.toList()
	fun exponential(baseMs: Long = 500, maxMs: Long = 15000, attempts: Int = 5): List<Long> {
		val list = mutableListOf<Long>()
		var v = baseMs.coerceAtMost(maxMs)  // Cap initial value too
		repeat(attempts) {
			list.add(v)
			v = (v * 2).coerceAtMost(maxMs)
		}
		return list
	}
}
