package cz.mia.app.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.terminal.Cell
import cz.mia.app.core.terminal.CellStyle
import cz.mia.app.core.terminal.TerminalKey
import cz.mia.app.core.terminal.TerminalPalette
import cz.mia.app.core.terminal.TerminalSnapshot
import cz.mia.app.features.terminal.TerminalStatus
import cz.mia.app.features.terminal.TerminalUiState
import cz.mia.app.features.terminal.TerminalViewModel
import cz.mia.app.ui.components.ScreenTitle
import cz.mia.app.ui.components.TerminalInputView

/**
 * More > Terminal (REQ-AND-029, ADR-0028): an SSH shell on the Pi. The form signs in with a password or the phone's
 * terminal key; once connected the screen is the terminal, with a row of keys the soft keyboard lacks.
 */
@Composable
fun TerminalScreen(modifier: Modifier = Modifier, vm: TerminalViewModel = hiltViewModel()) {
	val state by vm.state.collectAsState()
	val showTerminal = state.status == TerminalStatus.Connected || state.status is TerminalStatus.Closed
	if (showTerminal) TerminalSession(state, vm, modifier) else ConnectForm(state, vm, modifier)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ConnectForm(state: TerminalUiState, vm: TerminalViewModel, modifier: Modifier) {
	var password by remember { mutableStateOf("") }
	val connecting = state.status == TerminalStatus.Connecting
	val context = LocalContext.current
	Column(
		modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
		verticalArrangement = Arrangement.spacedBy(12.dp),
	) {
		ScreenTitle("Terminal")
		Text(
			"An SSH shell on the Pi as one of its login users. Anything you run there runs on the car's computer.",
			style = MaterialTheme.typography.bodyMedium,
			color = MaterialTheme.colorScheme.onSurfaceVariant,
		)
		OutlinedTextField(
			value = state.host, onValueChange = vm::setHost, label = { Text("Pi address") },
			singleLine = true, modifier = Modifier.fillMaxWidth().testTag("terminal_host"),
		)
		Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
			OutlinedTextField(
				value = state.user, onValueChange = vm::setUser, label = { Text("User") }, singleLine = true,
				modifier = Modifier.weight(2f).testTag("terminal_user"),
			)
			OutlinedTextField(
				value = state.port.toString(), onValueChange = vm::setPort, label = { Text("Port") }, singleLine = true,
				keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f),
			)
		}
		Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
			FilterChip(selected = !state.useKey, onClick = { vm.setUseKey(false) }, label = { Text("Password") })
			FilterChip(selected = state.useKey, onClick = { vm.setUseKey(true) }, label = { Text("Phone key") })
		}
		if (state.useKey) {
			Text(
				"The phone's own terminal key, kept in the Android Keystore. Add it once: sign in with the password and " +
					"tap \"Add phone key\", or put this line in ~/.ssh/authorized_keys on the Pi.",
				style = MaterialTheme.typography.bodySmall,
			)
			state.publicKeyLine?.let { line ->
				SelectionContainer { Text(line, style = MaterialTheme.typography.bodySmall, fontFamily = FontFamily.Monospace) }
				OutlinedButton(onClick = { copy(context, "MIA phone key", line) }) { Text("Copy public key") }
			}
		} else {
			OutlinedTextField(
				value = password, onValueChange = { password = it }, label = { Text("Password") }, singleLine = true,
				visualTransformation = PasswordVisualTransformation(),
				keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
				modifier = Modifier.fillMaxWidth().testTag("terminal_password"),
			)
		}
		Button(
			onClick = { vm.connect(password); password = "" },
			enabled = !connecting,
			modifier = Modifier.heightIn(min = 48.dp).testTag("terminal_connect"),
		) {
			if (connecting) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
			Text(if (connecting) "  Connecting..." else "Connect")
		}
		(state.status as? TerminalStatus.Failed)?.let { failed ->
			Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
				Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
					Text(failed.message, color = MaterialTheme.colorScheme.onErrorContainer)
					if (failed.changedKey != null) {
						OutlinedButton(onClick = vm::forgetHostKey) { Text("Forget the pinned key") }
					}
				}
			}
		}
		state.message?.let { Text(it, color = MaterialTheme.colorScheme.secondary) }
	}
}

@Composable
private fun TerminalSession(state: TerminalUiState, vm: TerminalViewModel, modifier: Modifier) {
	val snapshot by vm.screen.collectAsState()
	val context = LocalContext.current
	var input by remember { mutableStateOf<TerminalInputView?>(null) }
	val connected = state.status == TerminalStatus.Connected

	Column(modifier = modifier.fillMaxSize().background(Color(TerminalPalette.BACKGROUND))) {
		Row(
			modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surface).padding(horizontal = 8.dp),
			verticalAlignment = Alignment.CenterVertically,
		) {
			Text(
				snapshot.title.ifBlank { "${state.user}@${state.host}" },
				style = MaterialTheme.typography.titleSmall, maxLines = 1, modifier = Modifier.weight(1f),
			)
			TextButton(onClick = { vm.changeFont(-1) }) { Text("A-") }
			TextButton(onClick = { vm.changeFont(+1) }) { Text("A+") }
			if (connected) {
				TextButton(onClick = { clip(context)?.let(vm::paste) }) { Text("Paste") }
				TextButton(onClick = { copy(context, "Terminal", screenText(snapshot)) }) { Text("Copy") }
				if (state.passwordSession && state.publicKeyLine != null) {
					TextButton(onClick = vm::installPhoneKey) { Text("Add phone key") }
				}
				TextButton(onClick = vm::disconnect, modifier = Modifier.testTag("terminal_disconnect")) { Text("Disconnect") }
			} else {
				TextButton(onClick = vm::showForm, modifier = Modifier.testTag("terminal_reconnect")) { Text("Reconnect") }
			}
		}
		state.message?.let {
			Text(
				it, color = MaterialTheme.colorScheme.onSecondaryContainer,
				modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.secondaryContainer)
					.clickable { vm.dismissMessage() }.padding(8.dp),
			)
		}
		TerminalSurface(
			snapshot = snapshot,
			fontSize = state.fontSize,
			onSize = vm::resize,
			onTap = { input?.showKeyboard() },
			modifier = Modifier.weight(1f).fillMaxWidth(),
		)
		AndroidView(
			factory = { ctx ->
				TerminalInputView(ctx).also { view ->
					view.onText = vm::send
					view.onKey = vm::key
					view.onRaw = vm::sendRaw
					input = view
				}
			},
			modifier = Modifier.size(1.dp),
		)
		if (connected) ExtraKeys(state, vm)
	}
	LaunchedEffect(connected) { if (connected) input?.showKeyboard() }
	DisposableEffect(Unit) { onDispose { input = null } }
}

@Composable
private fun TerminalSurface(
	snapshot: TerminalSnapshot,
	fontSize: Int,
	onSize: (Int, Int) -> Unit,
	onTap: () -> Unit,
	modifier: Modifier,
) {
	val measurer = rememberTextMeasurer()
	val style = remember(fontSize) {
		TextStyle(fontFamily = FontFamily.Monospace, fontSize = fontSize.sp, lineHeight = (fontSize * 1.25f).sp,
			color = Color(TerminalPalette.FOREGROUND))
	}
	val cell = remember(style) { measurer.measure(AnnotatedString("M"), style).size }
	val density = LocalDensity.current
	val lineHeight = with(density) { cell.height.toDp() }
	BoxWithConstraints(
		modifier = modifier
			.padding(horizontal = 2.dp)
			.pointerInput(Unit) { detectTapGestures(onTap = { onTap() }) }
			.semantics { contentDescription = "Terminal screen" },
	) {
		val cols = (constraints.maxWidth / cell.width.coerceAtLeast(1))
		val rows = (constraints.maxHeight / cell.height.coerceAtLeast(1))
		LaunchedEffect(cols, rows) { onSize(cols, rows) }

		val list = rememberLazyListState()
		var follow by remember { mutableStateOf(true) }
		LaunchedEffect(list) {
			snapshotFlow { list.isScrollInProgress to list.canScrollForward }.collect { (moving, more) ->
				if (moving) follow = !more
			}
		}
		LaunchedEffect(snapshot) { if (follow) list.scrollToItem(snapshot.screenStart) }
		LazyColumn(state = list, modifier = Modifier.fillMaxSize().testTag("terminal_screen")) {
			items(snapshot.lines.size) { i ->
				val cursorX = if (snapshot.cursorVisible && i == snapshot.screenStart + snapshot.cursorY) snapshot.cursorX else -1
				Text(
					line(snapshot.lines[i], cursorX), style = style, maxLines = 1, softWrap = false,
					modifier = Modifier.height(lineHeight),
				)
			}
		}
		if (!follow) {
			Surface(
				shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.secondaryContainer,
				modifier = Modifier.align(Alignment.BottomEnd).padding(8.dp)
					.clickable { follow = true },
			) { Text("Back to live", Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
		}
	}
}

/** One terminal line as styled text; [cursorX] (or -1) is drawn inverted. Trailing blanks are dropped. */
private fun line(cells: Array<Cell>, cursorX: Int): AnnotatedString {
	var end = cells.size
	while (end > 0 && cells[end - 1] == Cell.BLANK && end - 1 != cursorX) end--
	return buildAnnotatedString {
		var i = 0
		while (i < end) {
			val s = cells[i].style
			val cur = i == cursorX
			var j = i + 1
			if (!cur) while (j < end && j != cursorX && cells[j].style == s) j++
			val start = length
			for (k in i until j) append(cells[k].ch)
			addStyle(span(s, cur), start, length)
			i = j
		}
	}
}

private fun span(s: CellStyle, cursor: Boolean): SpanStyle {
	var fg = TerminalPalette.argb(if (s.bold && s.fg in 0..7) s.fg + 8 else s.fg, TerminalPalette.FOREGROUND)
	var bg = TerminalPalette.argb(s.bg, TerminalPalette.BACKGROUND)
	if (s.inverse != cursor) { val t = fg; fg = bg; bg = t }
	return SpanStyle(
		color = Color(fg).let { if (s.dim) it.copy(alpha = 0.6f) else it },
		background = if (bg == TerminalPalette.BACKGROUND) Color.Unspecified else Color(bg),
		fontWeight = if (s.bold) FontWeight.Bold else null,
		fontStyle = if (s.italic) FontStyle.Italic else null,
		textDecoration = if (s.underline) TextDecoration.Underline else null,
	)
}

@Composable
private fun ExtraKeys(state: TerminalUiState, vm: TerminalViewModel) {
	Row(
		modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surface)
			.horizontalScroll(rememberScrollState()).padding(4.dp),
		horizontalArrangement = Arrangement.spacedBy(4.dp),
	) {
		KeyButton("Esc") { vm.key(TerminalKey.ESCAPE) }
		KeyButton("Ctrl", active = state.ctrl) { vm.toggleCtrl() }
		KeyButton("Alt", active = state.alt) { vm.toggleAlt() }
		KeyButton("Tab") { vm.key(TerminalKey.TAB) }
		KeyButton("←") { vm.key(TerminalKey.LEFT) }
		KeyButton("↑") { vm.key(TerminalKey.UP) }
		KeyButton("↓") { vm.key(TerminalKey.DOWN) }
		KeyButton("→") { vm.key(TerminalKey.RIGHT) }
		KeyButton("^C") { vm.sendRaw("\u0003") }
		KeyButton("Home") { vm.key(TerminalKey.HOME) }
		KeyButton("End") { vm.key(TerminalKey.END) }
		KeyButton("PgUp") { vm.key(TerminalKey.PAGE_UP) }
		KeyButton("PgDn") { vm.key(TerminalKey.PAGE_DOWN) }
		listOf("|", "/", "-", "~", "*", "$").forEach { c -> KeyButton(c) { vm.send(c) } }
	}
}

@Composable
private fun KeyButton(label: String, active: Boolean = false, onClick: () -> Unit) {
	Surface(
		shape = RoundedCornerShape(6.dp),
		color = if (active) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
		contentColor = if (active) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
		modifier = Modifier.heightIn(min = 40.dp).widthIn(min = 44.dp).clickable(onClick = onClick),
	) {
		Box(contentAlignment = Alignment.Center, modifier = Modifier.padding(horizontal = 10.dp, vertical = 10.dp)) {
			Text(label, fontFamily = FontFamily.Monospace)
		}
	}
}

private fun screenText(s: TerminalSnapshot): String =
	s.lines.subList(s.screenStart, s.lines.size).joinToString("\n") { l -> String(CharArray(l.size) { l[it].ch }).trimEnd() }.trimEnd()

private fun copy(context: Context, label: String, text: String) {
	(context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText(label, text))
}

private fun clip(context: Context): String? =
	(context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).primaryClip
		?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(context)?.toString()?.takeIf { it.isNotEmpty() }
