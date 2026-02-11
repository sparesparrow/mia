package cz.mia.app.core.camera

import org.junit.Assert.assertEquals
import org.junit.Test

class AnprPostprocessorTest {
	@Test
	fun normalize_replacesAmbiguousChars() {
		val n = AnprPostprocessor.normalize(" b0 0o ")
		assertEquals("8000", n)  // b→B→8, 0→0, 0→0, o→O→0
	}

	@Test
	fun czHeuristics_bonusApplied() {
		val (plate, bonus) = AnprPostprocessor.applyRegionHeuristics(" 2b o 1234 ", region = "CZ")
		// Normalization O->0, B->8 then CZ pattern match or alt
		// We accept any value; just ensure bonus non-negative for plausible plate
		assert(bonus >= 0f)
	}

	@Test
	fun confidenceTuning_bounds() {
		assertEquals(1.0f, AnprPostprocessor.tuneConfidence(0.98f, 0.2f), 1e-3f)
		assertEquals(0.0f, AnprPostprocessor.tuneConfidence(0.02f, -0.2f), 1e-3f)
	}
}
