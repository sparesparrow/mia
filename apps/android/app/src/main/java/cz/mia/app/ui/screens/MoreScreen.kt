package cz.mia.app.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import cz.mia.app.ui.components.ScreenTitle

/** The screens behind the More tab. */
enum class MoreDestination(val title: String, val description: String, val icon: ImageVector) {
    Alerts("Alerts", "Warnings and errors the app has raised", Icons.Default.Warning),
    ObdPairing("OBD pairing", "Find and connect a Bluetooth OBD adapter", Icons.Default.Bluetooth),
    Settings("Settings", "Pi address, API key, privacy and voice", Icons.Default.Settings),
}

/**
 * The More tab (REQ-AND-023): a list of the less used screens. With [current] null the list shows; otherwise
 * [content] draws that screen under a back row, and the system back button returns to the list. The state is
 * held by the caller so that tapping the More tab again can also return to the list.
 */
@Composable
fun MoreScreen(
    current: MoreDestination?,
    onSelect: (MoreDestination?) -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable (MoreDestination, Modifier) -> Unit,
) {
    BackHandler(enabled = current != null) { onSelect(null) }
    if (current == null) {
        MoreMenu(onSelect = { onSelect(it) }, modifier = modifier)
    } else {
        Column(modifier = modifier.fillMaxSize()) {
            TextButton(
                onClick = { onSelect(null) },
                modifier = Modifier.heightIn(min = 48.dp).padding(start = 8.dp),
            ) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back to More", modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(6.dp))
                Text("More", maxLines = 1, softWrap = false)
            }
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                content(current, Modifier)
            }
        }
    }
}

@Composable
private fun MoreMenu(onSelect: (MoreDestination) -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        ScreenTitle("More")
        MoreDestination.values().forEach { destination ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 72.dp)
                    .clickable { onSelect(destination) },
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(destination.icon, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                    Spacer(Modifier.width(16.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(destination.title, style = MaterialTheme.typography.titleLarge)
                        Text(
                            destination.description,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Icon(Icons.Default.ChevronRight, contentDescription = null)
                }
            }
        }
    }
}
