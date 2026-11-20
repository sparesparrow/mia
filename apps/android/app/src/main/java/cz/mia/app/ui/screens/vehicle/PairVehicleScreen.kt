package cz.mia.app.ui.screens.vehicle

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import cz.mia.app.ui.components.ScreenTitle

/**
 * The "Pair vehicle" step of the wizard, used for PairingPhone and PairAdapter, so the flow reads
 * "Install MIA on a car" then "Pair vehicle". [issue] is why the last system dialog did not finish; [notes] are steps
 * skipped with a reason. Both are plain text; nothing secret reaches them.
 */
@Composable
fun PairVehicleStep(
	ui: VehicleUi,
	issue: String?,
	notes: List<String>,
	onPrimary: () -> Unit,
	onSecondary: () -> Unit,
	modifier: Modifier = Modifier,
) {
	Column(
		modifier = modifier.verticalScroll(rememberScrollState()),
		verticalArrangement = Arrangement.spacedBy(12.dp),
	) {
		ScreenTitle(PAIR_TITLE, subtitle = INSTALL_TITLE)
		Text(ui.body)
		issue?.let { Text(it, color = MaterialTheme.colorScheme.error) }
		notes.forEach { Text(it) }
		ui.primaryLabel?.let { Button(onClick = onPrimary, modifier = Modifier.fillMaxWidth()) { Text(it) } }
		ui.secondaryLabel?.let { OutlinedButton(onClick = onSecondary, modifier = Modifier.fillMaxWidth()) { Text(it) } }
	}
}
