package cz.mia.app.core.terminal

// @req REQ-AND-029

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TerminalKeysTest {
	@Test
	fun cursorKeys_followTheApplicationCursorMode() {
		assertEquals("\u001b[A", TerminalKeys.sequence(TerminalKey.UP, applicationCursorKeys = false))
		assertEquals("\u001bOA", TerminalKeys.sequence(TerminalKey.UP, applicationCursorKeys = true))
		assertEquals("\u001b[D", TerminalKeys.sequence(TerminalKey.LEFT, false))
		assertEquals("\u001bOH", TerminalKeys.sequence(TerminalKey.HOME, true))
	}

	@Test
	fun editingKeys() {
		assertEquals("\u007f", TerminalKeys.sequence(TerminalKey.BACKSPACE, false))
		assertEquals("\r", TerminalKeys.sequence(TerminalKey.ENTER, false))
		assertEquals("\u001b[3~", TerminalKeys.sequence(TerminalKey.DELETE, false))
		assertEquals("\u001b[5~", TerminalKeys.sequence(TerminalKey.PAGE_UP, true))
		assertEquals("\t", TerminalKeys.sequence(TerminalKey.TAB, false))
		assertEquals("\u001b", TerminalKeys.sequence(TerminalKey.ESCAPE, false))
	}

	@Test
	fun control_mapsLettersAndPunctuation() {
		assertEquals('\u0003', TerminalKeys.control('c'))
		assertEquals('\u0003', TerminalKeys.control('C'))
		assertEquals('\u001a', TerminalKeys.control('z'))
		assertEquals('\u001b', TerminalKeys.control('['))
		assertEquals('\u0000', TerminalKeys.control(' '))
		assertNull(TerminalKeys.control('é'))
	}

	@Test
	fun typed_turnsNewlinesIntoEnter_andAppliesCtrlAndAltToTheFirstCharacter() {
		assertEquals("ls -l\r", TerminalKeys.typed("ls -l\n"))
		assertEquals("a\rb", TerminalKeys.typed("a\r\nb"))
		assertEquals("\u0003", TerminalKeys.typed("c", ctrl = true))
		assertEquals("\u0004x", TerminalKeys.typed("dx", ctrl = true))
		assertEquals("\u001bb", TerminalKeys.typed("b", alt = true))
		assertEquals("", TerminalKeys.typed("", ctrl = true))
	}

	@Test
	fun paste_isBracketedOnlyWhenTheHostAskedForIt_andCannotCloseTheBracketEarly() {
		assertEquals("a\rb", TerminalKeys.paste("a\nb", bracketed = false))
		assertEquals("\u001b[200~ab\u001b[201~", TerminalKeys.paste("a\u001b[201~b", bracketed = true))
	}

	@Test
	fun palette_coversSystemCubeGreyAndRgb() {
		assertEquals(0xFF0000FF.toInt() or 0, TerminalPalette.argb(21, 0)) // cube 0,0,5
		assertEquals(0xFFFF0000.toInt(), TerminalPalette.argb(196, 0)) // cube 5,0,0
		assertEquals(0xFF080808.toInt(), TerminalPalette.argb(232, 0))
		assertEquals(0xFFEEEEEE.toInt(), TerminalPalette.argb(255, 0))
		assertEquals(0xFF010203.toInt(), TerminalPalette.argb(CellStyle.rgb(1, 2, 3), 0))
		assertEquals(7, TerminalPalette.argb(CellStyle.DEFAULT_COLOR, 7))
		assertEquals(0xFFCD3131.toInt(), TerminalPalette.argb(1, 0))
	}
}
