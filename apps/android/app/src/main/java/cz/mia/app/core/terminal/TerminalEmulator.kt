package cz.mia.app.core.terminal

/**
 * How one cell is drawn. Colours are [DEFAULT_COLOR], a palette index 0-255, or an [rgb] value.
 */
data class CellStyle(
	val fg: Int = DEFAULT_COLOR,
	val bg: Int = DEFAULT_COLOR,
	val bold: Boolean = false,
	val dim: Boolean = false,
	val italic: Boolean = false,
	val underline: Boolean = false,
	val inverse: Boolean = false,
) {
	companion object {
		const val DEFAULT_COLOR = -1
		const val RGB_FLAG = 1 shl 24
		val DEFAULT = CellStyle()
		fun rgb(r: Int, g: Int, b: Int) = RGB_FLAG or ((r and 0xff) shl 16) or ((g and 0xff) shl 8) or (b and 0xff)
		fun isRgb(color: Int) = color >= 0 && (color and RGB_FLAG) != 0
	}
}

data class Cell(val ch: Char, val style: CellStyle) {
	companion object { val BLANK = Cell(' ', CellStyle.DEFAULT) }
}

/** What the screen draws: scrollback lines followed by the screen lines, and where the cursor is among them. */
class TerminalSnapshot(
	val lines: List<Array<Cell>>,
	val screenStart: Int,
	val cursorX: Int,
	val cursorY: Int,
	val cursorVisible: Boolean,
	val title: String,
	val cols: Int,
)

/**
 * A VT100/xterm screen for an SSH session (REQ-AND-029): it keeps the cells, the cursor, the scroll region, the
 * alternate screen and the scrollback, and understands the control sequences that a shell, `top`, `less`, `nano`
 * and `vim` send. [answer] carries the terminal's replies (cursor position, device attributes) back to the host.
 * Thread-safe: the SSH reader feeds it while the UI takes snapshots.
 */
class TerminalEmulator(
	cols: Int,
	rows: Int,
	private val scrollbackLimit: Int = 2000,
	private val answer: (String) -> Unit,
) {
	var cols = cols.coerceAtLeast(1); private set
	var rows = rows.coerceAtLeast(1); private set

	private var main = blankScreen()
	private var alt = blankScreen()
	private val history = ArrayDeque<Array<Cell>>()
	private var screen = main

	private var x = 0
	private var y = 0
	private var wrapPending = false
	private var style = CellStyle.DEFAULT
	private var top = 0
	private var bottom = this.rows - 1
	private var g0 = 'B'
	private var g1 = 'B'
	private var useG1 = false
	private var autowrap = true

	private data class Saved(val x: Int, val y: Int, val style: CellStyle, val g0: Char, val g1: Char, val useG1: Boolean)
	private var saved: Saved? = null
	private var savedMain: Saved? = null

	var altScreen = false; private set
	var applicationCursorKeys = false; private set
	var bracketedPaste = false; private set
	var cursorVisible = true; private set
	var title = ""; private set

	val cursor: Pair<Int, Int> @Synchronized get() = Pair(x, y)

	// Parser state.
	private enum class State { GROUND, ESC, CSI, OSC, OSC_ESC, CHARSET, IGNORE_ONE }
	private var state = State.GROUND
	private val params = StringBuilder()
	private var prefix: Char? = null
	private val intermediates = StringBuilder()
	private val osc = StringBuilder()
	private var charsetTarget = '('

	private fun blankLine(s: CellStyle = CellStyle.DEFAULT): Array<Cell> {
		val blank = if (s.bg == CellStyle.DEFAULT_COLOR) Cell.BLANK else Cell(' ', CellStyle(bg = s.bg))
		return Array(cols) { blank }
	}

	private fun blankScreen() = MutableList(rows) { blankLine() }
	private fun blankCell() = if (style.bg == CellStyle.DEFAULT_COLOR) Cell.BLANK else Cell(' ', CellStyle(bg = style.bg))

	@Synchronized
	fun feed(text: CharSequence) {
		for (c in text) step(c)
	}

	@Synchronized
	fun cell(x: Int, y: Int): Cell = screen[y][x]

	@Synchronized
	fun screenLine(y: Int): String = String(CharArray(cols) { screen[y][it].ch })

	@Synchronized
	fun scrollback(): List<String> = history.map { line -> String(CharArray(line.size) { line[it].ch }) }

	@Synchronized
	fun snapshot(): TerminalSnapshot {
		val lines = ArrayList<Array<Cell>>(history.size + rows)
		lines.addAll(history) // never changed after they scroll off, so shared
		screen.forEach { lines.add(it.copyOf()) }
		return TerminalSnapshot(lines, history.size, x, y, cursorVisible, title, cols)
	}

	@Synchronized
	fun resize(newCols: Int, newRows: Int) {
		val c = newCols.coerceAtLeast(1)
		val r = newRows.coerceAtLeast(1)
		if (c == cols && r == rows) return
		fun fit(lines: MutableList<Array<Cell>>, keepCursorRow: Boolean, toHistory: Boolean): MutableList<Array<Cell>> {
			val out = lines.map { line -> Array(c) { i -> if (i < line.size) line[i] else Cell.BLANK } }.toMutableList()
			if (keepCursorRow && y >= r) {
				val drop = y - r + 1
				repeat(drop) { out.removeAt(0).let { if (toHistory) pushHistory(it) } }
			}
			while (out.size > r) out.removeAt(out.size - 1)
			while (out.size < r) out.add(Array(c) { Cell.BLANK })
			return out
		}
		val shift = if (y >= r) y - r + 1 else 0
		if (altScreen) {
			alt = fit(alt, keepCursorRow = true, toHistory = false)
			main = fit(main, keepCursorRow = false, toHistory = false)
		} else {
			main = fit(main, keepCursorRow = true, toHistory = true)
			alt = fit(alt, keepCursorRow = false, toHistory = false)
		}
		screen = if (altScreen) alt else main
		cols = c
		rows = r
		y = (y - shift).coerceIn(0, rows - 1)
		x = x.coerceIn(0, cols - 1)
		top = 0
		bottom = rows - 1
		wrapPending = false
	}

	private fun pushHistory(line: Array<Cell>) {
		if (scrollbackLimit <= 0) return
		history.addLast(line)
		while (history.size > scrollbackLimit) history.removeFirst()
	}

	// ---- parser -------------------------------------------------------------------------------------------

	private fun step(c: Char) {
		when (state) {
			State.GROUND -> if (c.code < 0x20 || c.code == 0x7f) control(c) else print(c)
			State.ESC -> escape(c)
			State.CSI -> csiChar(c)
			State.OSC -> when (c.code) {
				0x07 -> endOsc()
				0x1b -> state = State.OSC_ESC
				else -> if (osc.length < 1024) osc.append(c)
			}
			State.OSC_ESC -> if (c == '\\') endOsc() else { state = State.ESC; escape(c) }
			State.CHARSET -> {
				if (charsetTarget == '(') g0 = c else if (charsetTarget == ')') g1 = c
				state = State.GROUND
			}
			State.IGNORE_ONE -> state = State.GROUND
		}
	}

	private fun control(c: Char) {
		when (c.code) {
			0x07 -> Unit // bell
			0x08 -> { if (x > 0) x--; wrapPending = false }
			0x09 -> { x = minOf(cols - 1, (x / 8 + 1) * 8); wrapPending = false }
			0x0a, 0x0b, 0x0c -> index()
			0x0d -> { x = 0; wrapPending = false }
			0x0e -> useG1 = true
			0x0f -> useG1 = false
			0x1b -> state = State.ESC
			else -> Unit
		}
	}

	private fun escape(c: Char) {
		state = State.GROUND
		when (c) {
			'[' -> { params.setLength(0); intermediates.setLength(0); prefix = null; state = State.CSI }
			']' -> { osc.setLength(0); state = State.OSC }
			'(', ')', '*', '+' -> { charsetTarget = c; state = State.CHARSET }
			'#', '%', ' ' -> state = State.IGNORE_ONE
			'7' -> saveCursor()
			'8' -> restoreCursor()
			'D' -> index()
			'E' -> { x = 0; index() }
			'M' -> reverseIndex()
			'c' -> reset()
			'P', 'X', '^', '_' -> { osc.setLength(0); state = State.OSC } // DCS/SOS/PM/APC: swallow like OSC
			else -> Unit // '=', '>', and anything unknown
		}
	}

	private fun csiChar(c: Char) {
		when {
			c.code == 0x1b -> state = State.ESC
			c.code < 0x20 -> control(c)
			c in '0'..'9' || c == ';' || c == ':' -> params.append(c)
			c in "?><=" && params.isEmpty() && prefix == null -> prefix = c
			c.code in 0x20..0x2f -> intermediates.append(c)
			c.code in 0x40..0x7e -> { state = State.GROUND; csi(c) }
			else -> state = State.GROUND
		}
	}

	private fun args(): List<Int> =
		if (params.isEmpty()) emptyList()
		else params.split(';', ':').map { it.toIntOrNull()?.coerceAtMost(9999) ?: 0 }

	private fun arg(list: List<Int>, i: Int, default: Int): Int = list.getOrNull(i)?.takeIf { it != 0 } ?: default

	private fun csi(final: Char) {
		val a = args()
		if (intermediates.isNotEmpty()) return // DECSCUSR (" q") and friends
		when (prefix) {
			'?' -> { if (final == 'h' || final == 'l') a.forEach { decMode(it, final == 'h') }; return }
			'>' -> { if (final == 'c') answer("\u001b[>0;0;0c"); return }
			null -> Unit
			else -> return
		}
		val n = arg(a, 0, 1)
		when (final) {
			'A' -> moveTo(x, y - n)
			'B', 'e' -> moveTo(x, y + n)
			'C', 'a' -> moveTo(x + n, y)
			'D' -> moveTo(x - n, y)
			'E' -> moveTo(0, y + n)
			'F' -> moveTo(0, y - n)
			'G', '`' -> moveTo(n - 1, y)
			'd' -> moveTo(x, n - 1)
			'H', 'f' -> moveTo(arg(a, 1, 1) - 1, arg(a, 0, 1) - 1)
			'J' -> eraseDisplay(a.getOrNull(0) ?: 0)
			'K' -> eraseLine(a.getOrNull(0) ?: 0)
			'L' -> if (y in top..bottom) { repeat(minOf(n, bottom - y + 1)) { scrollDown(y, bottom) } }
			'M' -> if (y in top..bottom) { repeat(minOf(n, bottom - y + 1)) { scrollUp(y, bottom, keep = false) } }
			'P' -> deleteChars(n)
			'@' -> insertChars(n)
			'X' -> { val line = screen[y]; for (i in x until minOf(cols, x + n)) line[i] = blankCell(); wrapPending = false }
			'S' -> repeat(n) { scrollUp(top, bottom, keep = false) }
			'T' -> repeat(n) { scrollDown(top, bottom) }
			'r' -> {
				val t = arg(a, 0, 1) - 1
				val b = arg(a, 1, rows) - 1
				if (t < b && b < rows) { top = t; bottom = b } else { top = 0; bottom = rows - 1 }
				moveTo(0, 0)
			}
			'm' -> sgr(a)
			's' -> saveCursor()
			'u' -> restoreCursor()
			'n' -> when (a.getOrNull(0)) {
				5 -> answer("\u001b[0n")
				6 -> answer("\u001b[${y + 1};${x + 1}R")
			}
			'c' -> if ((a.getOrNull(0) ?: 0) == 0) answer("\u001b[?1;2c")
			else -> Unit // h/l without '?', t (window ops) and the rest
		}
	}

	private fun decMode(mode: Int, on: Boolean) {
		when (mode) {
			1 -> applicationCursorKeys = on
			7 -> autowrap = on
			25 -> cursorVisible = on
			2004 -> bracketedPaste = on
			47, 1047 -> switchScreen(on, saveCursor = false)
			1049 -> switchScreen(on, saveCursor = true)
		}
	}

	private fun switchScreen(toAlt: Boolean, saveCursor: Boolean) {
		if (toAlt == altScreen) return
		if (toAlt) {
			if (saveCursor) savedMain = Saved(x, y, style, g0, g1, useG1)
			alt = blankScreen()
			screen = alt
		} else {
			screen = main
			if (saveCursor) savedMain?.let { restore(it) }
		}
		altScreen = toAlt
		wrapPending = false
	}

	private fun sgr(a: List<Int>) {
		if (a.isEmpty()) { style = CellStyle.DEFAULT; return }
		var i = 0
		while (i < a.size) {
			when (val p = a[i]) {
				0 -> style = CellStyle.DEFAULT
				1 -> style = style.copy(bold = true)
				2 -> style = style.copy(dim = true)
				3 -> style = style.copy(italic = true)
				4 -> style = style.copy(underline = true)
				7 -> style = style.copy(inverse = true)
				22 -> style = style.copy(bold = false, dim = false)
				23 -> style = style.copy(italic = false)
				24 -> style = style.copy(underline = false)
				27 -> style = style.copy(inverse = false)
				in 30..37 -> style = style.copy(fg = p - 30)
				39 -> style = style.copy(fg = CellStyle.DEFAULT_COLOR)
				in 40..47 -> style = style.copy(bg = p - 40)
				49 -> style = style.copy(bg = CellStyle.DEFAULT_COLOR)
				in 90..97 -> style = style.copy(fg = p - 90 + 8)
				in 100..107 -> style = style.copy(bg = p - 100 + 8)
				38, 48 -> {
					val color = when (a.getOrNull(i + 1)) {
						5 -> a.getOrNull(i + 2)?.coerceIn(0, 255).also { i += 2 }
						2 -> if (i + 4 < a.size) CellStyle.rgb(a[i + 2], a[i + 3], a[i + 4]).also { i += 4 } else null
						else -> null
					}
					if (color != null) style = if (p == 38) style.copy(fg = color) else style.copy(bg = color)
				}
			}
			i++
		}
	}

	private fun endOsc() {
		state = State.GROUND
		val text = osc.toString()
		val code = text.substringBefore(';', "")
		if (code == "0" || code == "2") title = text.substringAfter(';').take(256)
	}

	// ---- screen operations --------------------------------------------------------------------------------

	private fun print(raw: Char) {
		val c = if ((if (useG1) g1 else g0) == '0') LINE_DRAWING[raw] ?: raw else raw
		if (wrapPending) {
			if (autowrap) { x = 0; index() }
			wrapPending = false
		}
		screen[y][x] = Cell(c, style)
		if (x == cols - 1) wrapPending = true else x++
	}

	private fun moveTo(nx: Int, ny: Int) {
		x = nx.coerceIn(0, cols - 1)
		y = ny.coerceIn(0, rows - 1)
		wrapPending = false
	}

	private fun index() {
		wrapPending = false
		if (y == bottom) scrollUp(top, bottom, keep = true) else if (y < rows - 1) y++
	}

	private fun reverseIndex() {
		wrapPending = false
		if (y == top) scrollDown(top, bottom) else if (y > 0) y--
	}

	/** Moves lines [from]+1..[to] up one; the top line goes to scrollback when it is the whole main screen. */
	private fun scrollUp(from: Int, to: Int, keep: Boolean) {
		val gone = screen.removeAt(from)
		screen.add(to, blankLine(style))
		if (keep && !altScreen && from == 0 && to == rows - 1) pushHistory(gone)
	}

	private fun scrollDown(from: Int, to: Int) {
		screen.removeAt(to)
		screen.add(from, blankLine(style))
	}

	private fun eraseLine(mode: Int) {
		val line = screen[y]
		val range = when (mode) {
			0 -> x until cols
			1 -> 0..x
			else -> 0 until cols
		}
		for (i in range) line[i] = blankCell()
		wrapPending = false
	}

	private fun eraseDisplay(mode: Int) {
		when (mode) {
			0 -> { eraseLine(0); for (r in y + 1 until rows) screen[r] = blankLine(style) }
			1 -> { eraseLine(1); for (r in 0 until y) screen[r] = blankLine(style) }
			2 -> for (r in 0 until rows) screen[r] = blankLine(style)
			3 -> { for (r in 0 until rows) screen[r] = blankLine(style); history.clear() }
		}
		wrapPending = false
	}

	private fun deleteChars(n: Int) {
		val line = screen[y]
		val k = minOf(n, cols - x)
		for (i in x until cols) line[i] = if (i + k < cols) line[i + k] else blankCell()
		wrapPending = false
	}

	private fun insertChars(n: Int) {
		val line = screen[y]
		val k = minOf(n, cols - x)
		for (i in cols - 1 downTo x) line[i] = if (i - k >= x) line[i - k] else blankCell()
		wrapPending = false
	}

	private fun saveCursor() { saved = Saved(x, y, style, g0, g1, useG1) }
	private fun restoreCursor() { saved?.let { restore(it) } ?: moveTo(0, 0) }

	private fun restore(s: Saved) {
		x = s.x.coerceIn(0, cols - 1)
		y = s.y.coerceIn(0, rows - 1)
		style = s.style
		g0 = s.g0; g1 = s.g1; useG1 = s.useG1
		wrapPending = false
	}

	private fun reset() {
		main = blankScreen(); alt = blankScreen(); screen = main
		history.clear()
		x = 0; y = 0; wrapPending = false; style = CellStyle.DEFAULT
		top = 0; bottom = rows - 1
		g0 = 'B'; g1 = 'B'; useG1 = false; autowrap = true
		saved = null; savedMain = null
		altScreen = false; applicationCursorKeys = false; bracketedPaste = false; cursorVisible = true
	}

	private companion object {
		/** DEC Special Graphics: the box-drawing set that `ESC ( 0` selects. */
		val LINE_DRAWING = mapOf(
			'`' to '◆', 'a' to '▒', 'f' to '°', 'g' to '±', 'j' to '┘', 'k' to '┐', 'l' to '┌', 'm' to '└',
			'n' to '┼', 'o' to '⎺', 'p' to '⎻', 'q' to '─', 'r' to '⎼', 's' to '⎽', 't' to '├', 'u' to '┤',
			'v' to '┴', 'w' to '┬', 'x' to '│', 'y' to '≤', 'z' to '≥', '{' to 'π', '|' to '≠', '}' to '£', '~' to '·',
		)
	}
}
