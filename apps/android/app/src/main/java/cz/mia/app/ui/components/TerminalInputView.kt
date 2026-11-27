package cz.mia.app.ui.components

import android.annotation.SuppressLint
import android.content.Context
import android.text.InputType
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.BaseInputConnection
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputConnection
import android.view.inputmethod.InputMethodManager
import cz.mia.app.core.terminal.TerminalKey
import cz.mia.app.core.terminal.TerminalKeys

/**
 * Takes the keyboard for the terminal (REQ-AND-029). A plain EditText would keep its own text and swallow Backspace
 * on an empty field, so this view talks to the input method itself: committed text goes to [onText] at once,
 * deletes become Backspace, and hardware or injected key events are mapped to terminal keys. Suggestions and
 * autocorrect are off (visible-password input type), as a shell needs exactly what was typed.
 */
@SuppressLint("ViewConstructor")
class TerminalInputView(context: Context) : View(context) {
	/** Text the user typed; the screen applies its sticky Ctrl/Alt. */
	var onText: (String) -> Unit = {}
	var onKey: (TerminalKey) -> Unit = {}
	/** Bytes to send as they are (Ctrl or Alt held on a hardware keyboard). */
	var onRaw: (String) -> Unit = {}

	init {
		isFocusable = true
		isFocusableInTouchMode = true
		contentDescription = "Terminal keyboard input"
	}

	fun showKeyboard() {
		requestFocus()
		val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
		imm.showSoftInput(this, InputMethodManager.SHOW_IMPLICIT)
	}

	override fun onCheckIsTextEditor(): Boolean = true

	override fun onCreateInputConnection(outAttrs: EditorInfo): InputConnection {
		outAttrs.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD or
			InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
		outAttrs.imeOptions = EditorInfo.IME_FLAG_NO_FULLSCREEN or EditorInfo.IME_FLAG_NO_EXTRACT_UI or EditorInfo.IME_ACTION_NONE
		return object : BaseInputConnection(this, true) {
			override fun commitText(text: CharSequence?, newCursorPosition: Int): Boolean {
				super.commitText(text, newCursorPosition)
				flush()
				return true
			}

			override fun finishComposingText(): Boolean {
				super.finishComposingText()
				flush()
				return true
			}

			override fun deleteSurroundingText(beforeLength: Int, afterLength: Int): Boolean {
				val pending = editable
				if (pending != null && pending.isNotEmpty()) return super.deleteSurroundingText(beforeLength, afterLength)
				repeat(beforeLength) { onKey(TerminalKey.BACKSPACE) }
				repeat(afterLength) { onKey(TerminalKey.DELETE) }
				return true
			}

			override fun sendKeyEvent(event: KeyEvent): Boolean {
				if (event.action == KeyEvent.ACTION_DOWN) handleKey(event.keyCode, event)
				else if (event.action == KeyEvent.ACTION_MULTIPLE) event.characters?.let { onText(it) }
				return true
			}

			private fun flush() {
				val e = editable ?: return
				val text = e.toString()
				if (text.isNotEmpty()) {
					e.clear()
					onText(text)
				}
			}
		}
	}

	override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean = handleKey(keyCode, event) || super.onKeyDown(keyCode, event)

	override fun onKeyMultiple(keyCode: Int, repeatCount: Int, event: KeyEvent): Boolean {
		val chars = event.characters
		if (keyCode == KeyEvent.KEYCODE_UNKNOWN && chars != null) {
			onText(chars)
			return true
		}
		return super.onKeyMultiple(keyCode, repeatCount, event)
	}

	private fun handleKey(keyCode: Int, event: KeyEvent): Boolean {
		val key = when (keyCode) {
			KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_NUMPAD_ENTER -> TerminalKey.ENTER
			KeyEvent.KEYCODE_DEL -> TerminalKey.BACKSPACE
			KeyEvent.KEYCODE_FORWARD_DEL -> TerminalKey.DELETE
			KeyEvent.KEYCODE_DPAD_UP -> TerminalKey.UP
			KeyEvent.KEYCODE_DPAD_DOWN -> TerminalKey.DOWN
			KeyEvent.KEYCODE_DPAD_LEFT -> TerminalKey.LEFT
			KeyEvent.KEYCODE_DPAD_RIGHT -> TerminalKey.RIGHT
			KeyEvent.KEYCODE_MOVE_HOME -> TerminalKey.HOME
			KeyEvent.KEYCODE_MOVE_END -> TerminalKey.END
			KeyEvent.KEYCODE_PAGE_UP -> TerminalKey.PAGE_UP
			KeyEvent.KEYCODE_PAGE_DOWN -> TerminalKey.PAGE_DOWN
			KeyEvent.KEYCODE_INSERT -> TerminalKey.INSERT
			KeyEvent.KEYCODE_TAB -> TerminalKey.TAB
			KeyEvent.KEYCODE_ESCAPE -> TerminalKey.ESCAPE
			else -> null
		}
		if (key != null) {
			onKey(key)
			return true
		}
		if (keyCode == KeyEvent.KEYCODE_BACK) return false
		val unicode = event.getUnicodeChar(event.metaState and (KeyEvent.META_CTRL_MASK or KeyEvent.META_ALT_MASK).inv())
		if (unicode == 0 || (unicode and KeyCharacterMapCombining) != 0) return false
		val text = String(Character.toChars(unicode))
		if (event.isCtrlPressed || event.isAltPressed) {
			onRaw(TerminalKeys.typed(text, ctrl = event.isCtrlPressed, alt = event.isAltPressed))
		} else {
			onText(text)
		}
		return true
	}

	private companion object {
		/** KeyCharacterMap.COMBINING_ACCENT: a dead key, not a character. */
		const val KeyCharacterMapCombining = 0x80000000.toInt()
	}
}
