package cz.mia.app.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import cz.mia.app.data.db.TelemetryEntity

/**
 * The Citroën C4 values the Pi reports, shown as text.
 *
 * Read-only on purpose (ADR-0006): the app never starts a DPF regeneration or any other
 * actuation. Nothing is drawn when the telemetry carries no Citroën field.
 */
@Composable
fun CitroenReadings(latest: TelemetryEntity?, modifier: Modifier = Modifier) {
    val rows = citroenReadingRows(latest)
    if (rows.isEmpty()) return

    Column(modifier = modifier.fillMaxWidth()) {
        Text("Citroën C4 readings", style = MaterialTheme.typography.titleMedium)
        rows.forEach { (label, value) -> Text("$label: $value") }
        Spacer(Modifier.height(16.dp))
    }
}

/** Label and value for each Citroën field the telemetry actually carries, in display order. */
internal fun citroenReadingRows(latest: TelemetryEntity?): List<Pair<String, String>> {
    if (latest == null) return emptyList()
    return listOfNotNull(
        latest.dpfSootMass?.let { "DPF soot" to "${it}g" },
        latest.dpfStatus?.let { "DPF status" to it },
        latest.particulateFilterEfficiency?.let { "Filter efficiency" to "${it}%" },
        latest.adBlueLevel?.let { "AdBlue level" to "${it}%" },
    )
}
