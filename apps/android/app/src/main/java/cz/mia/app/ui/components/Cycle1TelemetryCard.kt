package cz.mia.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.dto.Cycle1TelemetrySignals
import cz.mia.app.data.remote.websocket.WebSocketState

@Composable
fun Cycle1TelemetryCard(
    telemetry: Cycle1TelemetryEnvelope?,
    connection: WebSocketState,
    modifier: Modifier = Modifier,
) {
    Card(modifier = modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Cycle 1 telemetry", style = MaterialTheme.typography.titleMedium)
            when {
                telemetry == null && connection is WebSocketState.Disconnected ->
                    Text("Pi offline — no live telemetry")
                telemetry == null && connection is WebSocketState.Error ->
                    Text("Pi offline — " + connection.message)
                telemetry == null ->
                    Text("Waiting for passive Pi telemetry…")
                else -> {
                    val ignition = telemetry.boolean(Cycle1TelemetrySignals.IGNITION)
                    val voltage = telemetry.number(Cycle1TelemetrySignals.BATTERY_VOLTAGE)
                    val rpm = telemetry.number(Cycle1TelemetrySignals.ENGINE_RPM)
                    val coolant = telemetry.number(Cycle1TelemetrySignals.COOLANT_TEMP_C)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        TelemetryValue("Ignition", ignition?.let { if (it) "ON" else "OFF" } ?: "—")
                        TelemetryValue("Voltage", voltage?.let { "%.2f V".format(it) } ?: "—")
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        TelemetryValue("RPM", rpm?.let { "%.0f".format(it) } ?: "—")
                        TelemetryValue("Coolant", coolant?.let { "%.1f °C".format(it) } ?: "—")
                    }
                    val confidence = telemetry.signals.values.minOfOrNull { it.confidence } ?: 0.0
                    Text(
                        "Source: " + telemetry.source + " • confidence %.2f".format(confidence),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}

@Composable
private fun TelemetryValue(label: String, value: String) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Text(label, style = MaterialTheme.typography.labelSmall)
        Text(value, style = MaterialTheme.typography.titleSmall)
    }
}
