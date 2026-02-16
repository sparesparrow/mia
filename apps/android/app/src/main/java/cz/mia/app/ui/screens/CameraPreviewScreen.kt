package cz.mia.app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.view.PreviewView
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.background.ANPRManager
import cz.mia.app.core.background.ANPRState
import cz.mia.app.core.background.DVRManager
import cz.mia.app.core.background.DVRState
import cz.mia.app.core.background.DetectedPlate
import cz.mia.app.core.background.DetectionStats
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for Camera Preview screen.
 */
@HiltViewModel
class CameraPreviewViewModel @Inject constructor(
    private val anprManager: ANPRManager,
    private val dvrManager: DVRManager
) : ViewModel() {
    
    val anprState: StateFlow<ANPRState> = anprManager.state
    val lastDetectedPlate: StateFlow<DetectedPlate?> = anprManager.lastDetectedPlate
    val detectionStats: StateFlow<DetectionStats> = anprManager.detectionStats
    
    val dvrState: StateFlow<DVRState> = dvrManager.state
    
    fun startAnpr() {
        viewModelScope.launch {
            anprManager.startDetection()
        }
    }
    
    fun stopAnpr() {
        viewModelScope.launch {
            anprManager.stopDetection()
        }
    }
    
    fun startRecording() {
        dvrManager.startRecording()
    }
    
    fun stopRecording() {
        dvrManager.stopRecording()
    }
    
    fun triggerClip(reason: String) {
        dvrManager.triggerEventClip(reason)
    }
    
    fun bindPreview(previewView: PreviewView, lifecycleOwner: androidx.lifecycle.LifecycleOwner) {
        anprManager.bindPreview(previewView, lifecycleOwner)
    }
    
    suspend fun bindDVRCamera(lifecycleOwner: androidx.lifecycle.LifecycleOwner) {
        dvrManager.bindCamera(lifecycleOwner)
    }
}

/**
 * Camera Preview Screen with ANPR detection and DVR recording.
 */
@Composable
fun CameraPreviewScreen(
    modifier: Modifier = Modifier,
    viewModel: CameraPreviewViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    
    val anprState by viewModel.anprState.collectAsState()
    val lastPlate by viewModel.lastDetectedPlate.collectAsState()
    val stats by viewModel.detectionStats.collectAsState()
    val dvrState by viewModel.dvrState.collectAsState()
    
    var hasPermission by remember { mutableStateOf(false) }
    var anprEnabled by remember { mutableStateOf(false) }
    var dvrEnabled by remember { mutableStateOf(false) }
    
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasPermission = granted
    }
    
    LaunchedEffect(Unit) {
        hasPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
        
        if (!hasPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }
    
    Box(modifier = modifier.fillMaxSize()) {
        if (hasPermission) {
            // Camera Preview
            AndroidView(
                factory = { ctx ->
                    PreviewView(ctx).apply {
                        implementationMode = PreviewView.ImplementationMode.COMPATIBLE
                        scaleType = PreviewView.ScaleType.FILL_CENTER
                    }
                },
                modifier = Modifier.fillMaxSize(),
                update = { previewView ->
                    viewModel.bindPreview(previewView, lifecycleOwner)
                }
            )
            
            // ANPR Detection Overlay
            AnimatedVisibility(
                visible = anprEnabled && lastPlate != null,
                enter = fadeIn(),
                exit = fadeOut(),
                modifier = Modifier.align(Alignment.TopCenter)
            ) {
                lastPlate?.let { plate ->
                    PlateDetectionOverlay(plate)
                }
            }
            
            // Controls Overlay
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                verticalArrangement = Arrangement.SpaceBetween
            ) {
                // Top bar with status
                StatusBar(
                    anprActive = anprState is ANPRState.Active,
                    dvrRecording = dvrState is DVRState.Recording,
                    stats = stats
                )
                
                Spacer(Modifier.weight(1f))
                
                // Bottom controls
                ControlsPanel(
                    anprEnabled = anprEnabled,
                    dvrEnabled = dvrEnabled,
                    onAnprToggle = { enabled ->
                        anprEnabled = enabled
                        if (enabled) viewModel.startAnpr() else viewModel.stopAnpr()
                    },
                    onDvrToggle = { enabled ->
                        dvrEnabled = enabled
                        if (enabled) viewModel.startRecording() else viewModel.stopRecording()
                    },
                    onTriggerClip = { viewModel.triggerClip("manual_trigger") }
                )
            }
        } else {
            // Permission request UI
            PermissionRequest(
                onRequestPermission = { permissionLauncher.launch(Manifest.permission.CAMERA) }
            )
        }
    }
}

@Composable
private fun StatusBar(
    anprActive: Boolean,
    dvrRecording: Boolean,
    stats: DetectionStats
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(Color.Black.copy(alpha = 0.6f))
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // ANPR Status
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusIndicator(active = anprActive, label = "ANPR")
            Spacer(Modifier.width(16.dp))
            StatusIndicator(active = dvrRecording, label = "REC", color = Color.Red)
        }
        
        // Stats
        Column(horizontalAlignment = Alignment.End) {
            Text(
                text = "Plates: ${stats.platesDetected}",
                color = Color.White,
                fontSize = 12.sp
            )
            Text(
                text = "Avg conf: ${String.format("%.0f%%", stats.averageConfidence * 100)}",
                color = Color.White.copy(alpha = 0.7f),
                fontSize = 10.sp
            )
        }
    }
}

@Composable
private fun StatusIndicator(
    active: Boolean,
    label: String,
    color: Color = Color.Green
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (active) color else Color.Gray)
        )
        Spacer(Modifier.width(4.dp))
        Text(
            text = label,
            color = Color.White,
            fontSize = 12.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Normal
        )
    }
}

@Composable
private fun PlateDetectionOverlay(plate: DetectedPlate) {
    Card(
        modifier = Modifier.padding(top = 80.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color.Black.copy(alpha = 0.8f)
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription = null,
                    tint = Color.Green,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = "PLATE DETECTED",
                    color = Color.Green,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
            }
            
            Spacer(Modifier.height(8.dp))
            
            Text(
                text = "${plate.normalizedText.take(3)}*****",
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 24.sp
            )
            
            Spacer(Modifier.height(4.dp))
            
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "Confidence: ",
                    color = Color.White.copy(alpha = 0.7f),
                    fontSize = 12.sp
                )
                LinearProgressIndicator(
                    progress = { plate.confidence },
                    modifier = Modifier
                        .width(80.dp)
                        .height(4.dp),
                    color = when {
                        plate.confidence >= 0.8f -> Color.Green
                        plate.confidence >= 0.6f -> Color.Yellow
                        else -> Color.Red
                    }
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    text = "${(plate.confidence * 100).toInt()}%",
                    color = Color.White,
                    fontSize = 12.sp
                )
            }
        }
    }
}

@Composable
private fun ControlsPanel(
    anprEnabled: Boolean,
    dvrEnabled: Boolean,
    onAnprToggle: (Boolean) -> Unit,
    onDvrToggle: (Boolean) -> Unit,
    onTriggerClip: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = Color.Black.copy(alpha = 0.7f)
        ),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            // ANPR Toggle
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.CameraAlt,
                        contentDescription = null,
                        tint = Color.White
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("ANPR Detection", color = Color.White)
                }
                Switch(
                    checked = anprEnabled,
                    onCheckedChange = onAnprToggle
                )
            }
            
            Spacer(Modifier.height(8.dp))
            
            // DVR Toggle
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Videocam,
                        contentDescription = null,
                        tint = if (dvrEnabled) Color.Red else Color.White
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("DVR Recording", color = Color.White)
                }
                Switch(
                    checked = dvrEnabled,
                    onCheckedChange = onDvrToggle
                )
            }
            
            Spacer(Modifier.height(12.dp))
            
            // Manual clip trigger button
            Button(
                onClick = onTriggerClip,
                modifier = Modifier.fillMaxWidth(),
                enabled = dvrEnabled,
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.Red.copy(alpha = 0.8f)
                )
            ) {
                Icon(Icons.Default.Videocam, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Save Event Clip")
            }
        }
    }
}

@Composable
private fun PermissionRequest(onRequestPermission: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.CameraAlt,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(Modifier.height(16.dp))
        
        Text(
            text = "Camera Permission Required",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )
        
        Spacer(Modifier.height(8.dp))
        
        Text(
            text = "ANPR detection and DVR recording require camera access.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(Modifier.height(24.dp))
        
        Button(onClick = onRequestPermission) {
            Text("Grant Permission")
        }
    }
}
