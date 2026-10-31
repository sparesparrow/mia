package cz.mia.app.ui.components

/** Brightness shown when the Pi has not reported an LED state yet. */
const val DEFAULT_LED_BRIGHTNESS = 0.7f

/**
 * The Pi reports LED brightness as 0..255 (`/led/state` brightness 128), while the slider and the
 * strip colour work with 0..1. Anything above 1 is taken as 0..255; the result is always within 0..1.
 */
fun normalizeLedBrightness(raw: Float?): Float {
	val value = raw ?: return DEFAULT_LED_BRIGHTNESS
	if (value.isNaN()) return DEFAULT_LED_BRIGHTNESS
	val scaled = if (value > 1f) value / 255f else value
	return scaled.coerceIn(0f, 1f)
}
