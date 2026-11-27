package cz.mia.app.core.terminal

// @req REQ-AND-029

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TerminalEmulatorTest {
	private val answers = StringBuilder()
	private fun term(cols: Int = 10, rows: Int = 4) = TerminalEmulator(cols, rows, scrollbackLimit = 50) { answers.append(it) }

	private fun TerminalEmulator.row(y: Int) = screenLine(y).trimEnd()

	@Test
	fun plainText_isWrittenAtTheCursor_andCrLfMovesToTheNextLine() {
		val t = term()
		t.feed("hello\r\nworld")
		assertEquals("hello", t.row(0))
		assertEquals("world", t.row(1))
		assertEquals(Pair(5, 1), t.cursor)
	}

	@Test
	fun aLongLine_wrapsAtTheLastColumn_onlyWhenTheNextCharacterArrives() {
		val t = term(cols = 4)
		t.feed("abcd")
		assertEquals(Pair(3, 0), t.cursor) // wrap pending, cursor stays on the last column
		t.feed("e")
		assertEquals("abcd", t.row(0))
		assertEquals("e", t.row(1))
	}

	@Test
	fun lineFeedOnTheLastRow_scrollsTheTopLineIntoScrollback() {
		val t = term(rows = 2)
		t.feed("one\r\ntwo\r\nthree")
		assertEquals("two", t.row(0))
		assertEquals("three", t.row(1))
		assertEquals(listOf("one"), t.scrollback().map { it.trimEnd() })
	}

	@Test
	fun backspaceAndCarriageReturn_moveTheCursorWithoutErasing() {
		val t = term()
		t.feed("abc\b\bX\rY")
		assertEquals("YXc", t.row(0))
	}

	@Test
	fun tab_movesToTheNextMultipleOfEight() {
		val t = term(cols = 20)
		t.feed("a\tb")
		assertEquals("a       b", t.row(0))
	}

	@Test
	fun cursorPosition_isOneBased_andClampedToTheScreen() {
		val t = term()
		t.feed("\u001b[2;3HX\u001b[99;99HZ")
		assertEquals("  X", t.row(1))
		assertEquals('Z', t.screenLine(3)[9])
	}

	@Test
	fun cursorMovement_upDownForwardBack() {
		val t = term()
		t.feed("\u001b[3;5H\u001b[2A\u001b[3D\u001b[BX\u001b[2CY")
		assertEquals(" X  Y", t.row(1))
	}

	@Test
	fun eraseInLine_variants() {
		val t = term()
		t.feed("abcdefgh\u001b[1;4H\u001b[K")
		assertEquals("abc", t.row(0))
		t.feed("\r\nabcdefgh\u001b[2;4H\u001b[1K")
		assertEquals("    efgh", t.row(1))
		t.feed("\u001b[2K")
		assertEquals("", t.row(1))
	}

	@Test
	fun eraseInDisplay_clearsTheScreen() {
		val t = term()
		t.feed("aaa\r\nbbb\r\nccc\u001b[2;2H\u001b[J")
		assertEquals("aaa", t.row(0))
		assertEquals("b", t.row(1))
		assertEquals("", t.row(2))
		t.feed("\u001b[2J")
		(0 until 4).forEach { assertEquals("", t.row(it)) }
	}

	@Test
	fun sgr_setsColoursAndAttributes_andResetClearsThem() {
		val t = term()
		t.feed("\u001b[1;31;44mR\u001b[0mN\u001b[38;5;208mO\u001b[38;2;1;2;3mT\u001b[7mI")
		val r = t.cell(0, 0)
		assertTrue(r.style.bold)
		assertEquals(1, r.style.fg)
		assertEquals(4, r.style.bg)
		assertEquals(CellStyle.DEFAULT, t.cell(1, 0).style)
		assertEquals(208, t.cell(2, 0).style.fg)
		assertEquals(CellStyle.rgb(1, 2, 3), t.cell(3, 0).style.fg)
		assertTrue(t.cell(4, 0).style.inverse)
	}

	@Test
	fun brightColours_mapToPaletteEightToFifteen() {
		val t = term()
		t.feed("\u001b[92;103mx")
		assertEquals(10, t.cell(0, 0).style.fg)
		assertEquals(11, t.cell(0, 0).style.bg)
	}

	@Test
	fun scrollRegion_scrollsOnlyInsideTheMargins() {
		val t = term(rows = 4)
		t.feed("top\r\na\r\nb\r\nbottom\u001b[2;3r\u001b[3;1H\nnew")
		assertEquals("top", t.row(0))
		assertEquals("b", t.row(1))
		assertEquals("new", t.row(2))
		assertEquals("bottom", t.row(3))
		assertTrue("a region scroll keeps no scrollback", t.scrollback().isEmpty())
	}

	@Test
	fun reverseIndex_atTheTop_scrollsDown() {
		val t = term(rows = 3)
		t.feed("a\r\nb\r\nc\u001b[H\u001bMz")
		assertEquals(listOf("z", "a", "b"), (0..2).map { t.row(it) })
	}

	@Test
	fun insertAndDeleteLinesAndCharacters() {
		val t = term(rows = 3)
		t.feed("1\r\n2\r\n3\u001b[2;1H\u001b[L")
		assertEquals(listOf("1", "", "2"), (0..2).map { t.row(it) })
		t.feed("\u001b[M")
		assertEquals(listOf("1", "2", ""), (0..2).map { t.row(it) })
		t.feed("\u001b[1;1Habcdef\u001b[1;2H\u001b[2P")
		assertEquals("adef", t.row(0))
		t.feed("\u001b[2@")
		assertEquals("a  def", t.row(0))
		t.feed("\u001b[3X")
		assertEquals("a   ef", t.row(0))
	}

	@Test
	fun alternateScreen_isSeparate_andLeavingItRestoresTheMainScreenAndCursor() {
		val t = term()
		t.feed("main\u001b[?1049h")
		assertTrue(t.altScreen)
		assertEquals("", t.row(0))
		t.feed("\u001b[Hvim")
		t.feed("\u001b[?1049l")
		assertFalse(t.altScreen)
		assertEquals("main", t.row(0))
		assertEquals(Pair(4, 0), t.cursor)
	}

	@Test
	fun saveAndRestoreCursor() {
		val t = term()
		t.feed("ab\u001b7\u001b[3;3Hx\u001b8c")
		assertEquals("abc", t.row(0))
		t.feed("\u001b[s\u001b[4;1H\u001b[uD")
		assertEquals("abcD", t.row(0))
	}

	@Test
	fun deviceStatusReport_answersTheCursorPosition_andDeviceAttributesAnswer() {
		val t = term()
		t.feed("\u001b[2;3H\u001b[6n")
		assertEquals("\u001b[2;3R", answers.toString())
		answers.clear()
		t.feed("\u001b[c")
		assertEquals("\u001b[?1;2c", answers.toString())
	}

	@Test
	fun applicationCursorKeys_andCursorVisibility_areTracked() {
		val t = term()
		t.feed("\u001b[?1h\u001b[?25l")
		assertTrue(t.applicationCursorKeys)
		assertFalse(t.cursorVisible)
		t.feed("\u001b[?1l\u001b[?25h")
		assertFalse(t.applicationCursorKeys)
		assertTrue(t.cursorVisible)
	}

	@Test
	fun osc_setsTheTitle_andIsNotPrinted() {
		val t = term(cols = 20)
		t.feed("\u001b]0;mia@pi: ~\u0007$ ")
		assertEquals("mia@pi: ~", t.title)
		assertEquals("$", t.row(0))
		t.feed("\u001b]2;other\u001b\\x")
		assertEquals("other", t.title)
		assertEquals("$ x", t.row(0))
	}

	@Test
	fun decLineDrawing_mapsToBoxCharacters() {
		val t = term()
		t.feed("\u001b(0lqk\u001b(Bq")
		assertEquals("┌─┐q", t.row(0))
	}

	@Test
	fun sequencesSplitAcrossFeeds_areStillParsed() {
		val t = term()
		t.feed("\u001b[")
		t.feed("2;")
		t.feed("2HX")
		assertEquals(" X", t.row(1))
	}

	@Test
	fun unknownSequences_areIgnoredWithoutPrintingTheirBytes() {
		val t = term(cols = 20)
		t.feed("a\u001b[>4;1m\u001b[?2004h\u001b=b\u001b[5 qc")
		assertEquals("abc", t.row(0))
	}

	@Test
	fun resize_keepsTheTextThatFits_andClampsTheCursor() {
		val t = term(cols = 10, rows = 4)
		t.feed("0123456789\r\nline2\u001b[2;10H")
		t.resize(5, 2)
		assertEquals("01234", t.row(0))
		assertEquals("line2", t.row(1))
		assertEquals(Pair(4, 1), t.cursor)
		t.resize(8, 3)
		assertEquals("01234", t.row(0))
		assertEquals(8, t.cols)
		assertEquals(3, t.rows)
	}

	@Test
	fun resize_shrinkingRows_pushesTopLinesToScrollback_soTheCursorRowStays() {
		val t = term(cols = 6, rows = 4)
		t.feed("a\r\nb\r\nc\r\nd")
		t.resize(6, 2)
		assertEquals("c", t.row(0))
		assertEquals("d", t.row(1))
		assertEquals(listOf("a", "b"), t.scrollback().map { it.trimEnd() })
	}

	@Test
	fun scrollback_isCappedAtItsLimit() {
		val t = TerminalEmulator(5, 1, scrollbackLimit = 3) {}
		repeat(10) { t.feed("$it\r\n") }
		assertEquals(listOf("7", "8", "9"), t.scrollback().map { it.trimEnd() })
	}

	@Test
	fun fullReset_clearsEverything() {
		val t = term()
		t.feed("\u001b[31mabc\u001b[?1049h\u001bc")
		assertFalse(t.altScreen)
		assertEquals("", t.row(0))
		assertEquals(Pair(0, 0), t.cursor)
		t.feed("x")
		assertEquals(CellStyle.DEFAULT, t.cell(0, 0).style)
	}
}
