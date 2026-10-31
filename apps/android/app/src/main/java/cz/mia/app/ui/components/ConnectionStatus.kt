package cz.mia.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.websocket.WebSocketState
import cz.mia.app.ui.theme.MiaMono
import cz.mia.app.ui.theme.mia

/** Live Cycle 1 data is on screen only while the Pi is connected and has sent an envelope. */
fun hasLiveCycle1(telemetry: Cycle1TelemetryEnvelope?, connection: WebSocketState): Boolean =
    telemetry != null && connection is WebSocketState.Connected

/** The text of the chip, in one place so it can be tested without drawing. */
fun cycle1StatusText(telemetry: Cycle1TelemetryEnvelope?, connection: WebSocketState): String = when {
    hasLiveCycle1(telemetry, connection) && telemetry != null -> {
        val confidence = telemetry.signals.values.minOfOrNull { it.confidence } ?: telemetry.confidence
        "Pi online • source " + telemetry.source + " • confidence %.2f".format(confidence)
    }
    connection is WebSocketState.Connected -> "Pi online • waiting for telemetry"
    connection is WebSocketState.Connecting -> "Pi connecting…"
    connection is WebSocketState.Error -> "Pi offline • " + connection.message
    else -> "Pi offline • no live telemetry"
}

/**
 * One chip that says whether the Pi is online, where the telemetry comes from and how sure it is. State is told
 * by an icon and words, not by colour alone.
 */
@Composable
fun Cycle1StatusChip(
    telemetry: Cycle1TelemetryEnvelope?,
    connection: WebSocketState,
    modifier: Modifier = Modifier,
) {
    val online = connection is WebSocketState.Connected
    val connecting = connection is WebSocketState.Connecting
    val color = when {
        online -> MaterialTheme.mia.success
        connecting -> MaterialTheme.mia.warning
        else -> MaterialTheme.colorScheme.error
    }
    val icon = when {
        online -> Icons.Default.CheckCircle
        connecting -> Icons.Default.Sync
        else -> Icons.Default.CloudOff
    }
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(50),
        color = color.copy(alpha = 0.12f),
        border = BorderStroke(1.dp, color),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                text = cycle1StatusText(telemetry, connection),
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = MiaMono),
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}

/**
 * The dashboard's top block: the status chip, then the gauges. [DashboardGauges] draws its "No telemetry data"
 * placeholder whenever it has no reading, so it is left out here while live Cycle 1 data exists; the Cycle 1
 * card below shows that data instead.
 */
@Composable
fun DashboardTelemetrySection(
    latest: TelemetryEntity?,
    cycle1Telemetry: Cycle1TelemetryEnvelope?,
    cycle1Connection: WebSocketState,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Cycle1StatusChip(cycle1Telemetry, cycle1Connection)
        Spacer(Modifier.height(12.dp))
        if (latest != null || !hasLiveCycle1(cycle1Telemetry, cycle1Connection)) {
            DashboardGauges(latest)
        }
    }
}
