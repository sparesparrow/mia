package cz.mia.app.ui.screens.camera

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.data.db.ClipEntity
import cz.mia.app.features.clips.ClipsViewModel
import cz.mia.app.presentation.screens.anpr.ANPRScreen
import cz.mia.app.presentation.screens.anpr.ANPRViewModel
import cz.mia.app.ui.screens.CameraPreviewScreen

private val TABS = listOf("Live", "Plates", "Clips", "Pi check")

/** The Camera tab: the phone's camera, the black book, saved clips and the Pi's plate check. */
@Composable
fun CameraScreen(modifier: Modifier = Modifier) {
	var tab by rememberSaveable { mutableStateOf(0) }
	Column(modifier.fillMaxSize()) {
		TabRow(selectedTabIndex = tab) {
			TABS.forEachIndexed { index, title ->
				Tab(selected = tab == index, onClick = { tab = index }, text = { Text(title) })
			}
		}
		when (tab) {
			0 -> CameraPreviewScreen(Modifier.fillMaxSize())
			1 -> PlatesScreen(Modifier.fillMaxSize())
			2 -> ClipsScreen(Modifier.fillMaxSize())
			else -> PiPlateCheck()
		}
	}
}

/** The Pi's camera and vignette check; its stream is open only while this is on screen. */
@Composable
private fun PiPlateCheck(viewModel: ANPRViewModel = hiltViewModel()) {
	DisposableEffect(viewModel) {
		viewModel.start()
		onDispose { viewModel.stop() }
	}
	ANPRScreen(viewModel)
}

@Composable
private fun ClipsScreen(modifier: Modifier = Modifier, viewModel: ClipsViewModel = hiltViewModel()) {
	val clips by viewModel.clips.collectAsState()
	Column(modifier.padding(16.dp)) {
		Card(
			modifier = Modifier.fillMaxWidth(),
			colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
		) {
			Text(
				"The dashcam does not record yet, so no clip here holds video (REQ-AND-005).",
				modifier = Modifier.padding(12.dp),
				color = MaterialTheme.colorScheme.onErrorContainer,
			)
		}
		LazyColumn(Modifier.padding(top = 12.dp)) {
			items(clips) { clip: ClipEntity ->
				Text("${clip.reason}  ${clip.filePath}  offloaded=${clip.offloaded}")
			}
		}
	}
}
