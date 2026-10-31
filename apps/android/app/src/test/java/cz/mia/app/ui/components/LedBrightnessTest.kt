package cz.mia.app.ui.components

// @req REQ-AND-025

import org.junit.Assert.assertEquals
import org.junit.Test

class LedBrightnessTest {
	@Test
	fun missingStateUsesTheDefault() {
		assertEquals(DEFAULT_LED_BRIGHTNESS, normalizeLedBrightness(null), 0f)
		assertEquals(DEFAULT_LED_BRIGHTNESS, normalizeLedBrightness(Float.NaN), 0f)
	}

	@Test
	fun piByteScaleIsConvertedToFraction() {
		assertEquals(128f / 255f, normalizeLedBrightness(128f), 0.0001f)
		assertEquals(1f, normalizeLedBrightness(255f), 0f)
		assertEquals(1f, normalizeLedBrightness(1000f), 0f)
	}

	@Test
	fun fractionsPassThroughAndAreClamped() {
		assertEquals(0.5f, normalizeLedBrightness(0.5f), 0f)
		assertEquals(1f, normalizeLedBrightness(1f), 0f)
		assertEquals(0f, normalizeLedBrightness(0f), 0f)
		assertEquals(0f, normalizeLedBrightness(-3f), 0f)
	}
}
