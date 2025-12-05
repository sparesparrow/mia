package cz.mia.app.ui.screens

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.BluetoothConnected
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SignalCellular4Bar
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.background.BLEManager
import cz.mia.app.core.background.BleConnectionState
import cz.mia.app.core.background.BleDeviceInfo
import cz.mia.app.core.background.OBDConnectionStatus
import cz.mia.app.core.background.OBDManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for OBD Pairing screen.
 */
@HiltViewModel
class OBDPairingViewModel @Inject constructor(
    private val bleManager: BLEManager,
    private val obdManager: OBDManager
) : ViewModel() {
    
    val connectionState: StateFlow<BleConnectionState> = bleManager.connectionState
    val discoveredDevices: StateFlow<List<BleDeviceInfo>> = bleManager.discoveredDevices
    val obdConnectionStatus: StateFlow<OBDConnectionStatus> = obdManager.connectionStatus
    
    fun initialize() {
        viewModelScope.launch {
            bleManager.initialize()
        }
    }
    
    fun startScanning() {
        viewModelScope.launch {
            bleManager.startScanning()
        }
    }
    
    fun stopScanning() {
        bleManager.stopScanning()
    }
    
    fun connectToDevice(address: String) {
        viewModelScope.launch {
            val success = bleManager.connectWithRetry(address)
            if (success) {
                obdManager.startMonitoring()
            }
        }
    }
    
    fun disconnect() {
        viewModelScope.launch {
            obdManager.stopMonitoring()
            bleManager.disconnect()
        }
    }
    
    fun isConnected(): Boolean = bleManager.isConnected()
}

/**
 * OBD Pairing Screen for Bluetooth device scanning and connection.
 */
@Composable
fun OBDPairingScreen(
    modifier: Modifier = Modifier,
    viewModel: OBDPairingViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    
    val connectionState by viewModel.connectionState.collectAsState()
    val discoveredDevices by viewModel.discoveredDevices.collectAsState()
    val obdStatus by viewModel.obdConnectionStatus.collectAsState()
    
    var hasPermissions by remember { mutableStateOf(false) }
    
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        hasPermissions = permissions.values.all { it }
    }
    
    LaunchedEffect(Unit) {
        val requiredPermissions = mutableListOf<String>()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            requiredPermissions.add(Manifest.permission.BLUETOOTH_SCAN)
            requiredPermissions.add(Manifest.permission.BLUETOOTH_CONNECT)
        } else {
            requiredPermissions.add(Manifest.permission.BLUETOOTH)
            requiredPermissions.add(Manifest.permission.BLUETOOTH_ADMIN)
        }
        requiredPermissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        
        hasPermissions = requiredPermissions.all { permission ->
            ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
        }
        
        if (!hasPermissions) {
            permissionLauncher.launch(requiredPermissions.toTypedArray())
        } else {
            viewModel.initialize()
        }
    }
    
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Header
        Text(
            text = "OBD-II Connection",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        
        Spacer(Modifier.height(8.dp))
        
        // Connection Status Card
        ConnectionStatusCard(
            connectionState = connectionState,
            obdStatus = obdStatus,
            onDisconnect = { viewModel.disconnect() }
        )
        
        Spacer(Modifier.height(16.dp))
        
        if (!hasPermissions) {
            PermissionRequestCard(
                onRequestPermission = {
                    val permissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                        arrayOf(
                            Manifest.permission.BLUETOOTH_SCAN,
                            Manifest.permission.BLUETOOTH_CONNECT,
                            Manifest.permission.ACCESS_FINE_LOCATION
                        )
                    } else {
                        arrayOf(
                            Manifest.permission.BLUETOOTH,
                            Manifest.permission.BLUETOOTH_ADMIN,
                            Manifest.permission.ACCESS_FINE_LOCATION
                        )
                    }
                    permissionLauncher.launch(permissions)
                }
            )
        } else {
            // Scan Controls
            ScanControlsCard(
                isScanning = connectionState is BleConnectionState.Scanning,
                isConnecting = connectionState is BleConnectionState.Connecting,
                isConnected = connectionState is BleConnectionState.Connected,
                onStartScan = { viewModel.startScanning() },
                onStopScan = { viewModel.stopScanning() }
            )
            
            Spacer(Modifier.height(16.dp))
            
            // Device List
            DeviceListCard(
                devices = discoveredDevices,
                connectionState = connectionState,
                onDeviceSelected = { device ->
                    viewModel.stopScanning()
                    viewModel.connectToDevice(device.address)
                }
            )
        }
    }
}

@Composable
private fun ConnectionStatusCard(
    connectionState: BleConnectionState,
    obdStatus: OBDConnectionStatus,
    onDisconnect: () -> Unit
) {
    val statusColor by animateColorAsState(
        targetValue = when (connectionState) {
            is BleConnectionState.Connected -> Color(0xFF4CAF50)
            is BleConnectionState.Connecting -> Color(0xFFFFC107)
            is BleConnectionState.Scanning -> Color(0xFF2196F3)
            is BleConnectionState.Error -> Color(0xFFF44336)
            else -> Color.Gray
        },
        label = "statusColor"
    )
    
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .clip(CircleShape)
                            .background(statusColor)
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = when (connectionState) {
                            is BleConnectionState.Connected -> "Connected"
                            is BleConnectionState.Connecting -> "Connecting..."
                            is BleConnectionState.Scanning -> "Scanning..."
                            is BleConnectionState.Error -> "Error"
                            else -> "Disconnected"
                        },
                        fontWeight = FontWeight.Medium
                    )
                }
                
                Icon(
                    imageVector = when (connectionState) {
                        is BleConnectionState.Connected -> Icons.Default.BluetoothConnected
                        is BleConnectionState.Scanning -> Icons.Default.BluetoothSearching
                        else -> Icons.Default.Bluetooth
                    },
                    contentDescription = null,
                    tint = statusColor
                )
            }
            
            if (connectionState is BleConnectionState.Connected) {
                Spacer(Modifier.height(8.dp))
                
                HorizontalDivider()
                
                Spacer(Modifier.height(8.dp))
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "OBD Status",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = when (obdStatus) {
                                is OBDConnectionStatus.Ready -> "Ready"
                                is OBDConnectionStatus.Initializing -> "Initializing..."
                                is OBDConnectionStatus.Connected -> "Connected"
                                is OBDConnectionStatus.Error -> "Error"
                                else -> "Disconnected"
                            },
                            fontWeight = FontWeight.Medium
                        )
                    }
                    
                    OutlinedButton(
                        onClick = onDisconnect,
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = Color.Red
                        )
                    ) {
                        Icon(Icons.Default.Close, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Disconnect")
                    }
                }
            }
            
            if (connectionState is BleConnectionState.Error) {
                Spacer(Modifier.height(8.dp))
                Text(
                    text = connectionState.message,
                    color = Color.Red,
                    fontSize = 12.sp
                )
            }
        }
    }
}

@Composable
private fun ScanControlsCard(
    isScanning: Boolean,
    isConnecting: Boolean,
    isConnected: Boolean,
    onStartScan: () -> Unit,
    onStopScan: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Find OBD Adapters",
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = "Scan for ELM327/OBD-II devices",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            if (isScanning) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        strokeWidth = 2.dp
                    )
                    Spacer(Modifier.width(8.dp))
                    IconButton(onClick = onStopScan) {
                        Icon(Icons.Default.Close, contentDescription = "Stop")
                    }
                }
            } else {
                Button(
                    onClick = onStartScan,
                    enabled = !isConnecting && !isConnected
                ) {
                    Icon(Icons.Default.BluetoothSearching, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Scan")
                }
            }
        }
        
        if (isScanning) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun DeviceListCard(
    devices: List<BleDeviceInfo>,
    connectionState: BleConnectionState,
    onDeviceSelected: (BleDeviceInfo) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Available Devices",
                fontWeight = FontWeight.Medium
            )
            
            Spacer(Modifier.height(8.dp))
            
            if (devices.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(100.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            imageVector = Icons.Default.BluetoothSearching,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(32.dp)
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            text = "No devices found. Start scanning.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 14.sp
                        )
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.height((devices.size * 72).coerceAtMost(288).dp)
                ) {
                    items(devices) { device ->
                        DeviceListItem(
                            device = device,
                            isConnecting = connectionState is BleConnectionState.Connecting,
                            onSelect = { onDeviceSelected(device) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DeviceListItem(
    device: BleDeviceInfo,
    isConnecting: Boolean,
    onSelect: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clickable(enabled = !isConnecting) { onSelect() },
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.DirectionsCar,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                
                Spacer(Modifier.width(12.dp))
                
                Column {
                    Text(
                        text = device.name ?: "Unknown Device",
                        fontWeight = FontWeight.Medium
                    )
                    Text(
                        text = device.address,
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            
            Row(verticalAlignment = Alignment.CenterVertically) {
                // Signal strength indicator
                SignalStrengthIndicator(rssi = device.rssi)
                
                Spacer(Modifier.width(8.dp))
                
                if (isConnecting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp
                    )
                } else {
                    Icon(
                        imageVector = Icons.Default.Bluetooth,
                        contentDescription = "Connect",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
    }
}

@Composable
private fun SignalStrengthIndicator(rssi: Int) {
    val strength = when {
        rssi >= -50 -> 4
        rssi >= -60 -> 3
        rssi >= -70 -> 2
        else -> 1
    }
    
    Row(
        verticalAlignment = Alignment.Bottom,
        horizontalArrangement = Arrangement.spacedBy(1.dp)
    ) {
        repeat(4) { index ->
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height((8 + index * 4).dp)
                    .clip(RoundedCornerShape(1.dp))
                    .background(
                        if (index < strength) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.surfaceVariant
                    )
            )
        }
    }
}

@Composable
private fun PermissionRequestCard(onRequestPermission: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Default.Error,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.error,
                modifier = Modifier.size(48.dp)
            )
            
            Spacer(Modifier.height(8.dp))
            
            Text(
                text = "Bluetooth Permissions Required",
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onErrorContainer
            )
            
            Spacer(Modifier.height(4.dp))
            
            Text(
                text = "Bluetooth and location permissions are needed to scan for and connect to OBD adapters.",
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onErrorContainer.copy(alpha = 0.8f)
            )
            
            Spacer(Modifier.height(16.dp))
            
            Button(onClick = onRequestPermission) {
                Text("Grant Permissions")
            }
        }
    }
}
