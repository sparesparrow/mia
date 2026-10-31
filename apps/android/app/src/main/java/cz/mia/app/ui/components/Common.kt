package cz.mia.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import cz.mia.app.ui.theme.mia

/** The title every screen starts with: Bebas Neue, with an optional line of context under it. */
@Composable
fun ScreenTitle(text: String, modifier: Modifier = Modifier, subtitle: String? = null) {
    Column(modifier = modifier.fillMaxWidth().padding(bottom = 8.dp)) {
        Text(
            text = text,
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
        )
        if (subtitle != null) {
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** A bordered card with an optional heading, so every screen groups its content the same way. */
@Composable
fun SectionCard(
    modifier: Modifier = Modifier,
    title: String? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (title != null) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.secondary,
                )
            }
            content()
        }
    }
}

/** What a severity looks like: a word and an icon as well as a colour, because red alone is not enough. */
private data class SeverityLook(val label: String, val icon: ImageVector, val color: Color)

@Composable
private fun severityLook(severity: String): SeverityLook {
    val key = severity.trim().uppercase()
    return when {
        key == "CRITICAL" || key == "ERROR" ->
            SeverityLook(key, Icons.Default.Error, MaterialTheme.colorScheme.error)
        key == "WARNING" || key == "WARN" ->
            SeverityLook(key, Icons.Default.Warning, MaterialTheme.mia.warning)
        else ->
            SeverityLook(key.ifEmpty { "INFO" }, Icons.Default.Info, MaterialTheme.mia.info)
    }
}

/** A small pill with the severity as a word, an icon and a colour. */
@Composable
fun SeverityChip(severity: String, modifier: Modifier = Modifier) {
    val look = severityLook(severity)
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(50),
        color = look.color.copy(alpha = 0.15f),
        border = BorderStroke(1.dp, look.color),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(look.icon, contentDescription = null, tint = look.color, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(4.dp))
            Text(
                text = look.label,
                style = MaterialTheme.typography.labelMedium,
                color = look.color,
                maxLines = 1,
                softWrap = false,
            )
        }
    }
}

/** One alert in a list: the severity chip, then the message. */
@Composable
fun AlertRow(severity: String, message: String, modifier: Modifier = Modifier) {
    SectionCard(modifier = modifier) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            SeverityChip(severity)
            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

/** An error in words with an icon, never a colour alone. */
@Composable
fun ErrorLabel(text: String, modifier: Modifier = Modifier) {
    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        Icon(
            Icons.Default.Error,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.error,
            modifier = Modifier.size(16.dp),
        )
        Spacer(Modifier.width(6.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.error)
    }
}
