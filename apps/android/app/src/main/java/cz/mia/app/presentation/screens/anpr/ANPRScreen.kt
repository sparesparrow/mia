package cz.mia.app.presentation.screens.anpr

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Camera
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale


@Composable
fun ANPRScreen(
    viewModel: ANPRViewModel = hiltViewModel()
) {
    val uiState = viewModel.uiState.collectAsState().value

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
    ) {
        // Header
        ANPRHeader(
            isWebsocketConnected = uiState.websocketConnected
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Capture Control
        CaptureControlSection(
            isCapturing = uiState.isCapturing,
            onStartCapture = { viewModel.startCapture() },
            onStopCapture = { viewModel.stopCapture() }
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Statistics
        StatsSection(stats = uiState.captureStats)

        Spacer(modifier = Modifier.height(16.dp))

        // Error Message
        if (uiState.error != null) {
            ErrorBanner(
                error = uiState.error,
                onDismiss = { viewModel.clearError() }
            )
            Spacer(modifier = Modifier.height(12.dp))
        }

        // Last Detection Alert
        if (uiState.lastDetection != null) {
            LastDetectionCard(
                detection = uiState.lastDetection,
                onDismiss = { viewModel.clearDetections() }
            )
            Spacer(modifier = Modifier.height(12.dp))
        }

        // Detection History
        Text(
            text = "Plate Detection History",
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )

        Spacer(modifier = Modifier.height(8.dp))

        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .background(
                    MaterialTheme.colorScheme.surfaceVariant,
                    shape = RoundedCornerShape(8.dp)
                )
                .padding(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            if (uiState.detectedPlates.isEmpty()) {
                item {
                    Text(
                        text = "No plates detected yet",
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                items(uiState.detectedPlates) { detection ->
                    PlateDetectionItem(detection = detection)
                }
            }
        }
    }
}


@Composable
private fun ANPRHeader(
    isWebsocketConnected: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                MaterialTheme.colorScheme.primaryContainer,
                shape = RoundedCornerShape(8.dp)
            )
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "ANPR Camera",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            Text(
                text = if (isWebsocketConnected) "Connected" else "Disconnected",
                fontSize = 12.sp,
                color = if (isWebsocketConnected)
                    Color(0xFF4CAF50)
                else
                    Color(0xFFF44336)
            )
        }

        Icon(
            imageVector = Icons.Default.Camera,
            contentDescription = "ANPR",
            modifier = Modifier.size(32.dp),
            tint = MaterialTheme.colorScheme.primary
        )
    }
}


@Composable
private fun CaptureControlSection(
    isCapturing: Boolean,
    onStartCapture: () -> Unit,
    onStopCapture: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Camera Control",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(12.dp))

            Button(
                onClick = if (isCapturing) onStopCapture else onStartCapture,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isCapturing)
                        Color(0xFFF44336)
                    else
                        Color(0xFF2196F3)
                )
            ) {
                Icon(
                    imageVector = if (isCapturing)
                        Icons.Default.Close
                    else
                        Icons.Default.CameraAlt,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp),
                    tint = Color.White
                )

                Spacer(modifier = Modifier.width(8.dp))

                Text(
                    text = if (isCapturing) "Stop Capture" else "Start Capture",
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
            }

            if (isCapturing) {
                Spacer(modifier = Modifier.height(8.dp))
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }
        }
    }
}


@Composable
private fun StatsSection(stats: CaptureStats) {
    Row(
        modifier = Modifier
            .fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        StatCard(
            title = "Total Scans",
            value = stats.totalScans.toString(),
            modifier = Modifier.weight(1f)
        )
        StatCard(
            title = "Exempted",
            value = stats.exemptedVehicles.toString(),
            modifier = Modifier.weight(1f),
            backgroundColor = Color(0xFFFF9800)
        )
        StatCard(
            title = "Normal",
            value = (stats.totalVehicles - stats.exemptedVehicles).toString(),
            modifier = Modifier.weight(1f),
            backgroundColor = Color(0xFF4CAF50)
        )
    }
}


@Composable
private fun StatCard(
    title: String,
    value: String,
    modifier: Modifier = Modifier,
    backgroundColor: Color = Color(0xFF2196F3)
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = backgroundColor.copy(alpha = 0.2f)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(12.dp)
                .fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = value,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = backgroundColor
            )
            Text(
                text = title,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}


@Composable
private fun ErrorBanner(
    error: String,
    onDismiss: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Color(0xFFEF5350),
                shape = RoundedCornerShape(8.dp)
            ),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                modifier = Modifier.weight(1f),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = "Error",
                    tint = Color.White,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = error,
                    color = Color.White,
                    fontSize = 12.sp
                )
            }
            IconButton(onClick = onDismiss, modifier = Modifier.size(24.dp)) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "Dismiss",
                    tint = Color.White
                )
            }
        }
    }
}


@Composable
private fun LastDetectionCard(
    detection: PlateDetection,
    onDismiss: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (detection.isExempted)
                Color(0xFFFFE082).copy(alpha = 0.2f)
            else
                Color(0xFF4CAF50).copy(alpha = 0.2f)
        ),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Last Detection",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = detection.plate,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1976D2)
                    )
                }
                IconButton(onClick = onDismiss) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Dismiss"
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            if (detection.isExempted) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(
                            Color(0xFFFFC107),
                            shape = RoundedCornerShape(4.dp)
                        )
                        .padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = "Alert",
                        tint = Color(0xFFF57F17),
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(
                            text = "Vozidlo osvobozeno",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFF57F17)
                        )
                        if (detection.exemptionReason != null) {
                            Text(
                                text = detection.exemptionReason,
                                fontSize = 10.sp,
                                color = Color(0xFFF57F17)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(4.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "Confidence: ${(detection.confidence * 100).toInt()}%",
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(detection.timestamp)),
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}


@Composable
private fun PlateDetectionItem(detection: PlateDetection) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        shape = RoundedCornerShape(6.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = detection.plate,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (detection.isExempted)
                        Color(0xFFFFC107)
                    else
                        Color(0xFF1976D2)
                )
                Text(
                    text = "${(detection.confidence * 100).toInt()}% confidence",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            if (detection.isExempted) {
                Surface(
                    modifier = Modifier.height(28.dp),
                    color = Color(0xFFFFC107),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Box(
                        modifier = Modifier.padding(horizontal = 10.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Exempted",
                            fontSize = 10.sp,
                            color = Color(0xFFF57F17)
                        )
                    }
                }
            }
        }
    }
}
