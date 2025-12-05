package cz.mia.app.core.camera

import kotlin.math.max
import kotlin.math.min

object AnprPostprocessor {
	private val czPattern = Regex("^[0-9][A-Z]{1,2}[0-9]{3,4}")
	private val euLoosePattern = Regex("^[A-Z0-9]{5,8}$")

	fun normalize(raw: String): String {
		return raw.trim()
			.uppercase()
			.replace(" ", "")
			.replace('O', '0')
			.replace('B', '8')
	}

	private fun altLettersForPositions(s: String, positions: IntRange): String {
		val chars = s.toCharArray()
		for (i in positions) {
			if (i in chars.indices) {
				when (chars[i]) {
					'0' -> chars[i] = 'O'
					'8' -> chars[i] = 'B'
				}
			}
		}
		return String(chars)
	}

	fun applyRegionHeuristics(raw: String, region: String = "CZ"): Pair<String, Float> {
		val base = normalize(raw)
		return when (region) {
			"CZ" -> {
				val candidate = base
				val alt = if (base.length >= 3) altLettersForPositions(base, 1..2) else base
				val (best, bonus) = when {
					czPattern.matches(candidate) -> candidate to 0.08f
					czPattern.matches(alt) -> alt to 0.05f
					euLoosePattern.matches(candidate) -> candidate to 0.03f
					else -> candidate to -0.10f
				}
				best to bonus
			}
			else -> {
				if (euLoosePattern.matches(base)) base to 0.03f else base to -0.10f
			}
		}
	}

	fun tuneConfidence(baseConfidence: Float, bonus: Float): Float {
		return min(1.0f, max(0.0f, baseConfidence + bonus))
	}
}
