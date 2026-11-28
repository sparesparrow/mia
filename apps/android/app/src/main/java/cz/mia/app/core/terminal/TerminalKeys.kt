package cz.mia.app.core.terminal

/** Keys that are not plain text. */
enum class TerminalKey { UP, DOWN, LEFT, RIGHT, HOME, END, PAGE_UP, PAGE_DOWN, INSERT, DELETE, TAB, ESCAPE, ENTER, BACKSPACE }

/** What the terminal sends to the host for a key press (xterm conventions, REQ-AND-029). */
object TerminalKeys {
	fun sequence(key: TerminalKey, applicationCursorKeys: Boolean): String {
		val cursor = if (applicationCursorKeys) "\u001bO" else "\u001b["
		return when (key) {
			TerminalKey.UP -> cursor + "A"
			TerminalKey.DOWN -> cursor + "B"
			TerminalKey.RIGHT -> cursor + "C"
			TerminalKey.LEFT -> cursor + "D"
			TerminalKey.HOME -> cursor + "H"
			TerminalKey.END -> cursor + "F"
			TerminalKey.PAGE_UP -> "\u001b[5~"
			TerminalKey.PAGE_DOWN -> "\u001b[6~"
			TerminalKey.INSERT -> "\u001b[2~"
			TerminalKey.DELETE -> "\u001b[3~"
			TerminalKey.TAB -> "\t"
			TerminalKey.ESCAPE -> "\u001b"
			TerminalKey.ENTER -> "\r"
			TerminalKey.BACKSPACE -> "\u007f"
		}
	}

	/** The control character for Ctrl+[c], or null when Ctrl does nothing to it. */
	fun control(c: Char): Char? = when (c) {
		in 'a'..'z' -> (c.code - 'a'.code + 1).toChar()
		in 'A'..'Z' -> (c.code - 'A'.code + 1).toChar()
		'@', ' ', '2' -> '\u0000'
		'[', '3' -> '\u001b'
		'\\', '4' -> '\u001c'
		']', '5' -> '\u001d'
		'^', '6' -> '\u001e'
		'_', '-', '7' -> '\u001f'
		'?', '8' -> '\u007f'
		else -> null
	}

	/**
	 * Text from the keyboard as the host should get it: a newline becomes Enter (CR); with [ctrl] the first
	 * character becomes its control character; with [alt] it is prefixed by ESC.
	 */
	fun typed(text: String, ctrl: Boolean = false, alt: Boolean = false): String {
		if (text.isEmpty()) return ""
		val normal = text.replace("\r\n", "\r").replace('\n', '\r')
		val first = normal[0]
		val head = if (ctrl) (control(first) ?: first).toString() else first.toString()
		return (if (alt) "\u001b" else "") + head + normal.substring(1)
	}

	/** Pasted text; with bracketed paste on, wrapped so a shell does not run it line by line. */
	fun paste(text: String, bracketed: Boolean): String {
		val body = text.replace("\r\n", "\r").replace('\n', '\r')
		return if (bracketed) "\u001b[200~" + body.replace("\u001b[201~", "") + "\u001b[201~" else body
	}
}
