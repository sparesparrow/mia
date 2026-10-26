package cz.mia.app.ui.screens.camera

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.data.db.WatchlistEntity
import cz.mia.app.features.anpr.AddPlateResult
import cz.mia.app.features.anpr.PlatesViewModel
import cz.mia.app.features.anpr.RecentPlate
import java.text.DateFormat
import java.util.Date
import kotlinx.coroutines.launch

/** The black book: add a plate by typing it or from a recent sighting, see the list, remove entries. */
@Composable
fun PlatesScreen(modifier: Modifier = Modifier, viewModel: PlatesViewModel = hiltViewModel()) {
	val entries by viewModel.entries.collectAsState()
	val recent by viewModel.recent.collectAsState()
	val scope = rememberCoroutineScope()
	var plate by remember { mutableStateOf("") }
	var label by remember { mutableStateOf("") }
	var error by remember { mutableStateOf<String?>(null) }
	var picked by remember { mutableStateOf<RecentPlate?>(null) }

	LazyColumn(modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
		item {
			Text("Black book", style = MaterialTheme.typography.titleLarge)
			Text(
				"MIA tells you when it sees a plate from this list. Only a hash of the plate is kept, made with " +
					"a key that never leaves this phone; the plate you type is cleared once it is added.",
				style = MaterialTheme.typography.bodySmall,
			)
		}
		item {
			OutlinedTextField(
				value = plate,
				onValueChange = { plate = it; error = null },
				label = { Text("Plate") },
				singleLine = true,
				isError = error != null,
				supportingText = error?.let { { Text(it) } },
				keyboardOptions = KeyboardOptions(
					capitalization = KeyboardCapitalization.Characters,
					autoCorrect = false,
					keyboardType = KeyboardType.Ascii,
				),
				modifier = Modifier.fillMaxWidth(),
			)
			OutlinedTextField(
				value = label,
				onValueChange = { label = it.take(PlatesViewModel.MAX_LABEL) },
				label = { Text("Label (optional)") },
				singleLine = true,
				modifier = Modifier.fillMaxWidth(),
			)
			Spacer(Modifier.height(8.dp))
			Button(onClick = {
				scope.launch {
					when (val result = viewModel.addTyped(plate, label)) {
						AddPlateResult.Added -> { plate = ""; label = "" }
						is AddPlateResult.Refused -> error = result.reason
					}
				}
			}) { Text("Add") }
		}
		item { HorizontalDivider() }
		if (entries.isEmpty()) {
			item { Text("No plates yet.") }
		}
		items(entries, key = { it.plateHash }) { entry ->
			ListedRow(entry, onRemove = { scope.launch { viewModel.remove(entry.plateHash) } })
		}
		item {
			HorizontalDivider()
			Text("Seen lately", style = MaterialTheme.typography.titleMedium)
			Text(
				"Plates the phone's camera read, by time. Pick one to add it.",
				style = MaterialTheme.typography.bodySmall,
			)
		}
		if (recent.isEmpty()) {
			item { Text("Nothing seen yet. Plates are read while Live is open and the driving service runs.") }
		}
		items(recent, key = { "recent-" + it.plateHash }) { seen ->
			RecentRow(seen, onAdd = { picked = seen })
		}
	}

	picked?.let { seen ->
		var pickedLabel by remember(seen) { mutableStateOf("") }
		AlertDialog(
			onDismissRequest = { picked = null },
			title = { Text("Add to black book") },
			text = {
				OutlinedTextField(
					value = pickedLabel,
					onValueChange = { pickedLabel = it.take(PlatesViewModel.MAX_LABEL) },
					label = { Text("Label (optional)") },
					singleLine = true,
				)
			},
			confirmButton = {
				TextButton(onClick = {
					scope.launch { viewModel.addSighting(seen.plateHash, pickedLabel) }
					picked = null
				}) { Text("Add") }
			},
			dismissButton = { TextButton(onClick = { picked = null }) { Text("Cancel") } },
		)
	}
}

@Composable
private fun ListedRow(entry: WatchlistEntity, onRemove: () -> Unit) {
	Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
		Column(Modifier.weight(1f)) {
			Text(entry.label.ifBlank { "(no label)" })
			Text(
				"added ${DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(entry.addedAt))}" +
					" · ${entry.plateHash.take(6)}",
				style = MaterialTheme.typography.bodySmall,
			)
		}
		IconButton(onClick = onRemove) { Icon(Icons.Default.Delete, contentDescription = "Remove") }
	}
}

@Composable
private fun RecentRow(seen: RecentPlate, onAdd: () -> Unit) {
	Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
		Column(Modifier.weight(1f)) {
			Text("${DateFormat.getTimeInstance(DateFormat.SHORT).format(Date(seen.lastSeen))} · ${seen.sightings}×")
			Text(seen.plateHash.take(6), style = MaterialTheme.typography.bodySmall)
		}
		if (seen.listed) {
			Text("in black book", style = MaterialTheme.typography.bodySmall)
		} else {
			TextButton(onClick = onAdd) { Text("Add") }
		}
	}
}
