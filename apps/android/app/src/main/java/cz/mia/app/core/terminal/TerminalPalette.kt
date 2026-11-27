package cz.mia.app.core.terminal

/** xterm colours as ARGB: the 16 system colours, the 6x6x6 cube and the grey ramp. */
object TerminalPalette {
	const val FOREGROUND = 0xFFE6E6E6.toInt()
	const val BACKGROUND = 0xFF111417.toInt()

	private val SYSTEM = intArrayOf(
		0x000000, 0xCD3131, 0x0DBC79, 0xE5E510, 0x2472C8, 0xBC3FBC, 0x11A8CD, 0xE5E5E5,
		0x666666, 0xF14C4C, 0x23D18B, 0xF5F543, 0x3B8EEA, 0xD670D6, 0x29B8DB, 0xFFFFFF,
	)

	/** [color] as a [CellStyle] holds it; [fallback] for [CellStyle.DEFAULT_COLOR]. */
	fun argb(color: Int, fallback: Int): Int {
		if (color == CellStyle.DEFAULT_COLOR) return fallback
		if (CellStyle.isRgb(color)) return 0xFF000000.toInt() or (color and 0xFFFFFF)
		val rgb = when (color) {
			in 0..15 -> SYSTEM[color]
			in 16..231 -> {
				val i = color - 16
				fun level(v: Int) = if (v == 0) 0 else 55 + v * 40
				(level(i / 36) shl 16) or (level(i / 6 % 6) shl 8) or level(i % 6)
			}
			in 232..255 -> (8 + (color - 232) * 10).let { (it shl 16) or (it shl 8) or it }
			else -> return fallback
		}
		return 0xFF000000.toInt() or rgb
	}
}
