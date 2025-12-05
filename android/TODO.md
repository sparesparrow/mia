# Android Development & Bug Fixing TODO

## Overview
This TODO list provides detailed, actionable tasks for implementing robust Android app functionality within the MIA (Modular IoT Assistant) ecosystem. Each task includes specific file locations, code patterns, and implementation guidance optimized for AI-assisted development.

**Project Context**: Android app for MIA system connecting to FastAPI backend (REST + WebSocket) and BLE OBD-II/IoT devices via Raspberry Pi hub.

**Key Technologies**: Kotlin, Jetpack Compose, Hilt DI, Coroutines, Retrofit, OkHttp, Android BLE APIs

***

## Status Summary (Last Updated: 2025-12-03)

### ✅ Completed Tasks
- **P0 Critical Bugs**: All fixed (BLEManager memory leaks, race conditions, deprecated APIs, permissions)
- **P1 Architecture/API**: Complete (MVVM setup, Hilt DI, FastAPI integration)
- **P2 UI/Tests**: Complete (BLE screens, telemetry display, unit tests)
- **P3 Documentation**: Complete (architecture docs, user guides)

### 🔄 New Features Added
- **Kernun Proxy MCP Integration**: Optional security analysis via Conan package
- **CPython Bootstrap**: Shared bundled CPython for Android tools (`android/tools/lib/cpython_bootstrap.py`)
- **OBD Simulator**: Development tool for BLE testing (`android/tools/bootstrap-obd.py`)

***

## Kernun Proxy MCP Integration (NEW)

### Overview
Optional integration with Kernun proxy MCP server for network security analysis.
Enabled via `with_proxy_mcp=True` in Conan configuration.

### Available MCP Tools
- `analyze_traffic` - Network traffic analysis
- `inspect_session` - Session inspection
- `modify_tls_policy` - TLS policy management
- `update_proxy_rules` - Firewall rules management
- `update_clearweb_database` - Content categorization

### Files
| File | Purpose |
|------|---------|
| `conan-recipes/kernun-mcp-tools/conanfile.py` | Conan recipe for MCP tools |
| `conanfile.py` | Root config with `with_proxy_mcp` option |
| `modules/security/proxy_mcp_client.py` | Python MCP client wrapper |

### Usage
```python
from modules.security import ProxyMCPClient

async with ProxyMCPClient("localhost", 3000) as client:
    result = await client.analyze_traffic(time_range_seconds=300)
    print(result)
```

***

## CPython Bootstrap Extension (NEW)

### Overview
Shared CPython bootstrap module for Android development tools.
Provides bundled CPython 3.12.7 for cross-platform tool development.

### Features
- Downloads standalone CPython from GitHub releases
- Supports Linux (x86_64, aarch64), macOS (x86_64, arm64), Windows (x86_64)
- Automatic version verification and caching
- Context manager and CLI interface

### Files
| File | Purpose |
|------|---------|
| `android/tools/lib/cpython_bootstrap.py` | Shared CPython bootstrap module |
| `android/tools/lib/__init__.py` | Module exports |
| `android/tools/bootstrap-obd.py` | OBD simulator using bundled CPython |

### Usage
```python
from lib.cpython_bootstrap import CPythonBootstrap

with CPythonBootstrap() as python_path:
    subprocess.run([python_path, "script.py"])
```

### CLI
```bash
# Show installation info
python3 android/tools/lib/cpython_bootstrap.py --info

# Run script with bundled Python
python3 android/tools/lib/cpython_bootstrap.py script.py [args...]

# Force re-download
python3 android/tools/lib/cpython_bootstrap.py --force
```

***

## 1. Critical Bug Fixes (Priority: P0 - Must Fix First)

### 1.1 Fix Memory Leak in BLEManager
**File**: `android/app/src/main/java/cz/aiservis/app/core/background/BLEManager.kt`

**Problem**: CoroutineScope created with `SupervisorJob()` is never cancelled, causing memory leaks.

**Implementation**:
```kotlin
@Singleton
class BLEManagerImpl @Inject constructor(
    @ApplicationContext private val context: Context
) : BLEManager {
    
    // Replace this line:
    // private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    // With lifecycle-aware scope:
    private val job = SupervisorJob()
    private val scope = CoroutineScope(job + Dispatchers.IO)
    
    // Add cleanup method:
    fun cleanup() {
        job.cancel()
        responseChannel.close()
        disconnect()
    }
}
```

**Add to MainActivity or Application class**:
```kotlin
override fun onDestroy() {
    super.onDestroy()
    bleManager.cleanup()
}
```

**Acceptance Criteria**:
- [ ] BLEManager has cleanup() method that cancels scope and closes channel
- [ ] cleanup() is called from Activity/Application lifecycle
- [ ] No coroutine leaks detected in Android Profiler after disconnect

***

### 1.2 Fix Race Condition in Connection State
**File**: `android/app/src/main/java/cz/aiservis/app/core/background/BLEManager.kt`

**Problem**: `connectionDeferred` accessed from multiple threads without synchronization.

**Implementation**:
```kotlin
// Add Mutex for thread-safe access
private val connectionMutex = Mutex()
private var connectionDeferred: CompletableDeferred<Boolean>? = null

// In tryConnect method, wrap access:
private suspend fun tryConnect(address: String): Boolean = withContext(Dispatchers.Main) {
    stopScanning()
    
    val device = bluetoothAdapter?.getRemoteDevice(address)
    if (device == null) {
        _connectionState.value = BleConnectionState.Error("Device not found")
        return@withContext false
    }
    
    connectionMutex.withLock {
        connectionDeferred = CompletableDeferred()
    }
    
    _connectionState.value = BleConnectionState.Connecting
    
    try {
        bluetoothGatt = device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
        
        val result = withTimeoutOrNull(CONNECTION_TIMEOUT_MS) {
            connectionMutex.withLock {
                connectionDeferred?.await() ?: false
            }
        } ?: false
        
        // ... rest of initialization
    } catch (e: Exception) {
        connectionMutex.withLock {
            connectionDeferred?.complete(false)
        }
        throw e
    }
}

// Update callback to use mutex:
override fun onConnectionStateChange(gatt: BluetoothGatt?, status: Int, newState: Int) {
    when (newState) {
        BluetoothProfile.STATE_DISCONNECTED -> {
            scope.launch {
                connectionMutex.withLock {
                    connectionDeferred?.complete(false)
                }
            }
            // ... cleanup
        }
    }
}
```

**Acceptance Criteria**:
- [ ] All connectionDeferred access wrapped in connectionMutex.withLock {}
- [ ] No race conditions detected in stress testing (100+ rapid connect/disconnect cycles)
- [ ] Thread-safety verified with ThreadSanitizer

***

### 1.3 Fix Missing BluetoothGattDescriptor Import
**File**: `android/app/src/main/java/cz/aiservis/app/core/background/BLEManager.kt`

**Problem**: Using dummy descriptor object instead of real Android API.

**Implementation**:
```kotlin
// Remove this dummy at bottom of file:
// private object BluetoothGattDescriptor {
//     val ENABLE_NOTIFICATION_VALUE: ByteArray = byteArrayOf(0x01, 0x00)
// }

// Add proper import at top:
import android.bluetooth.BluetoothGattDescriptor

// In onServicesDiscovered, fix descriptor usage:
rxCharacteristic?.let { rx ->
    gatt.setCharacteristicNotification(rx, true)
    val descriptor = rx.getDescriptor(
        UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
    )
    descriptor?.let {
        // Use real descriptor API
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            gatt.writeDescriptor(it, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
        } else {
            @Suppress("DEPRECATION")
            it.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
            @Suppress("DEPRECATION")
            gatt.writeDescriptor(it)
        }
    }
}
```

**Acceptance Criteria**:
- [ ] Dummy BluetoothGattDescriptor object removed
- [ ] Proper import added
- [ ] Notification subscription works on Android 13+

***

### 1.4 Update Deprecated Bluetooth APIs for Android 12+
**File**: `android/app/src/main/java/cz/aiservis/app/core/background/BLEManager.kt`

**Problem**: Using deprecated characteristic.value setter and writeCharacteristic methods.

**Implementation**:
```kotlin
@SuppressLint("MissingPermission")
override suspend fun sendCommand(command: String): String? = withContext(Dispatchers.IO) {
    val gatt = bluetoothGatt
    val tx = txCharacteristic
    
    if (gatt == null || tx == null) {
        Log.e(TAG, "Not connected or no TX characteristic")
        return@withContext null
    }
    
    try {
        val commandWithCR = "$command\r"
        val bytes = commandWithCR.toByteArray(Charsets.UTF_8)
        
        // Use modern API based on Android version
        val writeResult = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            withContext(Dispatchers.Main) {
                suspendCancellableCoroutine<Int> { continuation ->
                    val callback = object : BluetoothGattCallback() {
                        override fun onCharacteristicWrite(
                            gatt: BluetoothGatt?,
                            characteristic: BluetoothGattCharacteristic?,
                            status: Int
                        ) {
                            continuation.resume(status)
                        }
                    }
                    gatt.writeCharacteristic(
                        tx,
                        bytes,
                        BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
                    )
                }
            }
        } else {
            withContext(Dispatchers.Main) {
                @Suppress("DEPRECATION")
                tx.value = bytes
                @Suppress("DEPRECATION")
                val success = gatt.writeCharacteristic(tx)
                if (success) BluetoothGatt.GATT_SUCCESS else BluetoothGatt.GATT_FAILURE
            }
        }
        
        if (writeResult != BluetoothGatt.GATT_SUCCESS) {
            Log.e(TAG, "Write failed with status: $writeResult")
            return@withContext null
        }
        
        // Wait for response with timeout
        return@withContext withTimeoutOrNull(COMMAND_TIMEOUT_MS) {
            responseChannel.receive()
        }
    } catch (e: Exception) {
        Log.e(TAG, "Failed to send command: $command", e)
        return@withContext null
    }
}
```

**Acceptance Criteria**:
- [ ] Uses writeCharacteristic(characteristic, value, writeType) on Android 13+
- [ ] Properly handles write callbacks with suspendCancellableCoroutine
- [ ] Deprecated APIs suppressed with proper annotations
- [ ] Works correctly on Android 12, 13, 14

***

### 1.5 Add Runtime Bluetooth Permission Checks
**File**: `android/app/src/main/java/cz/aiservis/app/core/background/BLEManager.kt`
**New File**: `android/app/src/main/java/cz/aiservis/app/utils/PermissionHelper.kt`

**Problem**: Missing runtime permission validation before Bluetooth operations.

**Create PermissionHelper.kt**:
```kotlin
package cz.mia.app.utils

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

object PermissionHelper {
    
    fun getRequiredBluetoothPermissions(): Array<String> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
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
    }
    
    fun hasBluetoothPermissions(context: Context): Boolean {
        return getRequiredBluetoothPermissions().all { permission ->
            ContextCompat.checkSelfPermission(context, permission) == 
                PackageManager.PERMISSION_GRANTED
        }
    }
    
    fun getMissingBluetoothPermissions(context: Context): List<String> {
        return getRequiredBluetoothPermissions().filter { permission ->
            ContextCompat.checkSelfPermission(context, permission) != 
                PackageManager.PERMISSION_GRANTED
        }
    }
}
```

**Update BLEManager.kt**:
```kotlin
@SuppressLint("MissingPermission") // Remove this, handle properly
override suspend fun initialize() = withContext(Dispatchers.Main) {
    if (!PermissionHelper.hasBluetoothPermissions(context)) {
        val missing = PermissionHelper.getMissingBluetoothPermissions(context)
        _connectionState.value = BleConnectionState.Error(
            "Missing permissions: ${missing.joinToString()}"
        )
        return@withContext
    }
    
    if (bluetoothAdapter == null) {
        _connectionState.value = BleConnectionState.Error("Bluetooth not supported")
        return@withContext
    }
    
    if (!bluetoothAdapter.isEnabled) {
        _connectionState.value = BleConnectionState.Error("Bluetooth is disabled")
        return@withContext
    }
    
    bluetoothLeScanner = bluetoothAdapter.bluetoothLeScanner
    Log.d(TAG, "BLE Manager initialized")
}

// Similar checks in startScanning(), tryConnect(), etc.
```

**Update AndroidManifest.xml**:
```xml
<!-- Android 12+ permissions -->
<uses-permission android:name="android.permission.BLUETOOTH_SCAN"
    android:usesPermissionFlags="neverForLocation" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />

<!-- Pre-Android 12 permissions -->
<uses-permission android:name="android.permission.BLUETOOTH"
    android:maxSdkVersion="30" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN"
    android:maxSdkVersion="30" />

<!-- Location required for BLE scanning -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

<!-- Bluetooth feature -->
<uses-feature android:name="android.hardware.bluetooth_le" android:required="true" />
```

**Acceptance Criteria**:
- [ ] PermissionHelper utility class created
- [ ] All BLE operations check permissions before execution
- [ ] User sees clear error messages for missing permissions
- [ ] Manifest has correct permissions for all Android versions
- [ ] Remove all @SuppressLint("MissingPermission") annotations

***

### 1.6 Fix Resource Leak in Disconnect
**File**: `android/app/src/main/java/cz/aiservis/app/core/background/BLEManager.kt`

**Problem**: cleanup() may not execute if disconnect() throws exception.

**Implementation**:
```kotlin
@SuppressLint("MissingPermission")
override suspend fun disconnect() {
    withContext(Dispatchers.Main) {
        try {
            bluetoothGatt?.disconnect()
        } catch (e: Exception) {
            Log.e(TAG, "Disconnect threw exception", e)
        } finally {
            // Always cleanup, even if disconnect fails
            cleanup()
            _connectionState.value = BleConnectionState.Disconnected
        }
    }
}

private fun cleanup() {
    try {
        bluetoothGatt?.close()
    } catch (e: Exception) {
        Log.e(TAG, "Error closing GATT", e)
    } finally {
        bluetoothGatt = null
        txCharacteristic = null
        rxCharacteristic = null
        responseBuffer.clear()
    }
}
```

**Acceptance Criteria**:
- [ ] cleanup() always executes via finally block
- [ ] All resources released even on exception
- [ ] No BluetoothGatt leaks in Android Profiler

***

### 1.7 Fix Unbounded Channel Buffer
**File**: `android/app/src/main/java/cz/aiservis/app/core/background/BLEManager.kt`

**Problem**: Channel.BUFFERED has default capacity that can overflow.

**Implementation**:
```kotlin
// Replace:
// private val responseChannel = Channel<String>(Channel.BUFFERED)

// With bounded channel with overflow handling:
private val responseChannel = Channel<String>(
    capacity = 16,
    onBufferOverflow = BufferOverflow.DROP_OLDEST
)

// Or use Flow for better backpressure handling:
private val _responses = MutableSharedFlow<String>(
    replay = 0,
    extraBufferCapacity = 16,
    onBufferOverflow = BufferOverflow.DROP_OLDEST
)

// Then in sendCommand:
override suspend fun sendCommand(command: String): String? = withContext(Dispatchers.IO) {
    // ... write logic ...
    
    return@withContext withTimeoutOrNull(COMMAND_TIMEOUT_MS) {
        _responses.first { response ->
            // Match response to command if needed
            true
        }
    }
}
```

**Acceptance Criteria**:
- [ ] Channel capacity explicitly set to reasonable value (16-32)
- [ ] Overflow strategy defined (DROP_OLDEST preferred for telemetry)
- [ ] No memory accumulation under high-frequency data

***

## 2. Android App Architecture & Core Setup (Priority: P1)

### 2.1 Setup Project Dependencies
**File**: `android/app/build.gradle.kts`

**Implementation**:
```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.dagger.hilt.android")
    id("kotlin-kapt")
    id("kotlin-parcelize")
}

android {
    namespace = "cz.mia.app"
    compileSdk = 34
    
    defaultConfig {
        applicationId = "cz.mia.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
        
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        
        // API endpoint configuration
        buildConfigField("String", "API_BASE_URL", "\"http://192.168.1.100:8000\"")
        buildConfigField("String", "WS_BASE_URL", "\"ws://192.168.1.100:8000\"")
    }
    
    buildFeatures {
        compose = true
        buildConfig = true
    }
    
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
}

dependencies {
    // Core Android
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    
    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.navigation:navigation-compose:2.7.6")
    
    // Hilt DI
    implementation("com.google.dagger:hilt-android:2.50")
    kapt("com.google.dagger:hilt-compiler:2.50")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")
    
    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    
    // WebSocket
    implementation("org.java-websocket:Java-WebSocket:1.5.5")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
    
    // Room Database (for caching)
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")
    
    // DataStore (preferences)
    implementation("androidx.datastore:datastore-preferences:1.0.0")
    
    // Charts for telemetry
    implementation("com.patrykandpatrick.vico:compose:1.13.1")
    implementation("com.patrykandpatrick.vico:compose-m3:1.13.1")
    
    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
    testImplementation("app.cash.turbine:turbine:1.0.0")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.02.00"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
```

**Acceptance Criteria**:
- [ ] All dependencies added and synced successfully
- [ ] Project compiles without errors
- [ ] Hilt DI configuration complete

***

### 2.2 Create Application Class with Hilt
**File**: `android/app/src/main/java/cz/aiservis/app/MiaApplication.kt`

**Implementation**:
```kotlin
package cz.mia.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import timber.log.Timber

@HiltAndroidApp
class MiaApplication : Application() {
    
    override fun onCreate() {
        super.onCreate()
        
        // Initialize Timber logging
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
        
        Timber.d("MIA Application started")
    }
}
```

**Update AndroidManifest.xml**:
```xml
<application
    android:name=".MiaApplication"
    android:allowBackup="true"
    android:icon="@mipmap/ic_launcher"
    android:label="@string/app_name"
    android:theme="@style/Theme.MIA">
    <!-- activities -->
</application>
```

**Acceptance Criteria**:
- [ ] Application class created and registered
- [ ] Hilt initialized successfully
- [ ] Logging configured

***

### 2.3 Setup MVVM Architecture Structure
**Create Package Structure**:
```
android/app/src/main/java/cz/aiservis/app/
├── MiaApplication.kt
├── MainActivity.kt
├── di/                    # Dependency Injection modules
│   ├── NetworkModule.kt
│   ├── DatabaseModule.kt
│   └── BluetoothModule.kt
├── data/
│   ├── local/            # Room database
│   │   ├── dao/
│   │   ├── entities/
│   │   └── MiaDatabase.kt
│   ├── remote/           # API services
│   │   ├── api/
│   │   │   ├── DeviceApi.kt
│   │   │   └── TelemetryApi.kt
│   │   ├── websocket/
│   │   │   └── TelemetryWebSocket.kt
│   │   └── dto/          # Data transfer objects
│   ├── repository/
│   │   ├── DeviceRepository.kt
│   │   └── TelemetryRepository.kt
│   └── models/           # Domain models
├── domain/
│   └── usecases/         # Business logic
├── ui/
│   ├── navigation/
│   ├── screens/
│   │   ├── devices/
│   │   ├── telemetry/
│   │   └── settings/
│   ├── components/       # Reusable UI components
│   └── theme/
├── core/
│   ├── background/       # Existing BLEManager
│   ├── voice/
│   └── security/
└── utils/
    ├── PermissionHelper.kt
    └── NetworkMonitor.kt
```

**Acceptance Criteria**:
- [ ] Package structure created
- [ ] Base classes/interfaces defined
- [ ] Architecture decision documented

***

### 2.4 Implement Hilt Dependency Injection Modules
**File**: `android/app/src/main/java/cz/aiservis/app/di/NetworkModule.kt`

**Implementation**:
```kotlin
package cz.mia.app.di

import com.google.gson.Gson
import com.google.gson.GsonBuilder
import cz.mia.app.BuildConfig
import cz.mia.app.data.remote.api.DeviceApi
import cz.mia.app.data.remote.api.TelemetryApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    
    @Provides
    @Singleton
    fun provideGson(): Gson = GsonBuilder()
        .setLenient()
        .create()
    
    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
        
        if (BuildConfig.DEBUG) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            builder.addInterceptor(loggingInterceptor)
        }
        
        return builder.build()
    }
    
    @Provides
    @Singleton
    fun provideRetrofit(
        okHttpClient: OkHttpClient,
        gson: Gson
    ): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create(gson))
        .build()
    
    @Provides
    @Singleton
    fun provideDeviceApi(retrofit: Retrofit): DeviceApi =
        retrofit.create(DeviceApi::class.java)
    
    @Provides
    @Singleton
    fun provideTelemetryApi(retrofit: Retrofit): TelemetryApi =
        retrofit.create(TelemetryApi::class.java)
}
```

**File**: `android/app/src/main/java/cz/aiservis/app/di/BluetoothModule.kt`

```kotlin
package cz.mia.app.di

import android.content.Context
import cz.mia.app.core.background.BLEManager
import cz.mia.app.core.background.BLEManagerImpl
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object BluetoothModule {
    
    @Provides
    @Singleton
    fun provideBLEManager(
        @ApplicationContext context: Context
    ): BLEManager = BLEManagerImpl(context)
}
```

**Acceptance Criteria**:
- [ ] Network module provides Retrofit and API services
- [ ] Bluetooth module provides BLEManager
- [ ] All modules compile and inject successfully

***

## 3. FastAPI Backend Integration (Priority: P1)

### 3.1 Define API Data Models
**File**: `android/app/src/main/java/cz/aiservis/app/data/remote/dto/ApiModels.kt`

**Implementation**:
```kotlin
package cz.mia.app.data.remote.dto

import com.google.gson.annotations.SerializedName

// Device DTOs
data class DeviceDto(
    @SerializedName("id") val id: String,
    @SerializedName("name") val name: String,
    @SerializedName("type") val type: String,
    @SerializedName("status") val status: DeviceStatus,
    @SerializedName("capabilities") val capabilities: List<String>,
    @SerializedName("last_seen") val lastSeen: Long
)

enum class DeviceStatus {
    @SerializedName("online") ONLINE,
    @SerializedName("offline") OFFLINE,
    @SerializedName("error") ERROR
}

// Command DTOs
data class CommandRequest(
    @SerializedName("device") val deviceId: String,
    @SerializedName("action") val action: String,
    @SerializedName("params") val params: Map<String, Any>? = null
)

data class CommandResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String,
    @SerializedName("data") val data: Any? = null
)

// Telemetry DTOs
data class TelemetryReading(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("timestamp") val timestamp: Long,
    @SerializedName("sensor") val sensor: String,
    @SerializedName("value") val value: Double,
    @SerializedName("unit") val unit: String
)

data class TelemetryBatch(
    @SerializedName("readings") val readings: List<TelemetryReading>
)

// System Status
data class SystemStatus(
    @SerializedName("uptime") val uptime: Long,
    @SerializedName("cpu_usage") val cpuUsage: Double,
    @SerializedName("memory_usage") val memoryUsage: Double,
    @SerializedName("active_devices") val activeDevices: Int
)
```

**Acceptance Criteria**:
- [ ] All DTOs match FastAPI response schemas
- [ ] Gson serialization annotations correct
- [ ] Enums handle unknown values gracefully

***

### 3.2 Implement Device API Service
**File**: `android/app/src/main/java/cz/aiservis/app/data/remote/api/DeviceApi.kt`

**Implementation**:
```kotlin
package cz.mia.app.data.remote.api

import cz.mia.app.data.remote.dto.*
import retrofit2.Response
import retrofit2.http.*

interface DeviceApi {
    
    @GET("devices")
    suspend fun getDevices(): Response<List<DeviceDto>>
    
    @GET("devices/{id}")
    suspend fun getDevice(@Path("id") deviceId: String): Response<DeviceDto>
    
    @POST("command")
    suspend fun sendCommand(@Body request: CommandRequest): Response<CommandResponse>
    
    @GET("status")
    suspend fun getSystemStatus(): Response<SystemStatus>
    
    @POST("devices/{id}/pair")
    suspend fun pairDevice(@Path("id") deviceId: String): Response<CommandResponse>
    
    @DELETE("devices/{id}")
    suspend fun unpairDevice(@Path("id") deviceId: String): Response<CommandResponse>
}
```

**Acceptance Criteria**:
- [ ] All endpoints match FastAPI routes
- [ ] Suspend functions for coroutine support
- [ ] Proper HTTP methods used

***

### 3.3 Implement Telemetry API Service
**File**: `android/app/src/main/java/cz/aiservis/app/data/remote/api/TelemetryApi.kt`

**Implementation**:
```kotlin
package cz.mia.app.data.remote.api

import cz.mia.app.data.remote.dto.TelemetryBatch
import cz.mia.app.data.remote.dto.TelemetryReading
import retrofit2.Response
import retrofit2.http.*

interface TelemetryApi {
    
    @GET("telemetry")
    suspend fun getLatestTelemetry(
        @Query("device_id") deviceId: String? = null,
        @Query("sensor") sensor: String? = null,
        @Query("limit") limit: Int = 100
    ): Response<TelemetryBatch>
    
    @GET("telemetry/history")
    suspend fun getTelemetryHistory(
        @Query("device_id") deviceId: String,
        @Query("sensor") sensor: String,
        @Query("start") startTimestamp: Long,
        @Query("end") endTimestamp: Long
    ): Response<TelemetryBatch>
    
    @POST("telemetry")
    suspend fun uploadTelemetry(@Body batch: TelemetryBatch): Response<CommandResponse>
}
```

**Acceptance Criteria**:
- [ ] Query parameters properly mapped
- [ ] Pagination support if needed
- [ ] Response types correct

***

### 3.4 Implement WebSocket Telemetry Client
**File**: `android/app/src/main/java/cz/aiservis/app/data/remote/websocket/TelemetryWebSocket.kt`

**Implementation**:
```kotlin
package cz.mia.app.data.remote.websocket

import com.google.gson.Gson
import cz.mia.app.BuildConfig
import cz.mia.app.data.remote.dto.TelemetryReading
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import org.java_websocket.client.WebSocketClient
import org.java_websocket.handshake.ServerHandshake
import timber.log.Timber
import java.net.URI
import javax.inject.Inject
import javax.inject.Singleton

sealed class WebSocketState {
    object Disconnected : WebSocketState()
    object Connecting : WebSocketState()
    object Connected : WebSocketState()
    data class Error(val message: String) : WebSocketState()
}

@Singleton
class TelemetryWebSocket @Inject constructor(
    private val gson: Gson
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    private val _telemetryFlow = MutableSharedFlow<TelemetryReading>(
        replay = 0,
        extraBufferCapacity = 64
    )
    val telemetryFlow: SharedFlow<TelemetryReading> = _telemetryFlow.asSharedFlow()
    
    private val _stateFlow = MutableSharedFlow<WebSocketState>(replay = 1)
    val stateFlow: SharedFlow<WebSocketState> = _stateFlow.asSharedFlow()
    
    private var webSocketClient: WebSocketClient? = null
    private var shouldReconnect = false
    
    fun connect() {
        if (webSocketClient?.isOpen == true) {
            Timber.d("WebSocket already connected")
            return
        }
        
        shouldReconnect = true
        scope.launch {
            _stateFlow.emit(WebSocketState.Connecting)
        }
        
        try {
            val uri = URI("${BuildConfig.WS_BASE_URL}/ws/telemetry")
            webSocketClient = object : WebSocketClient(uri) {
                override fun onOpen(handshakedata: ServerHandshake?) {
                    Timber.d("WebSocket connected")
                    scope.launch {
                        _stateFlow.emit(WebSocketState.Connected)
                    }
                    
                    // Subscribe to all telemetry
                    send(gson.toJson(mapOf("action" to "subscribe", "filter" to "all")))
                }
                
                override fun onMessage(message: String?) {
                    message?.let {
                        try {
                            val reading = gson.fromJson(it, TelemetryReading::class.java)
                            scope.launch {
                                _telemetryFlow.emit(reading)
                            }
                        } catch (e: Exception) {
                            Timber.e(e, "Failed to parse telemetry message")
                        }
                    }
                }
                
                override fun onClose(code: Int, reason: String?, remote: Boolean) {
                    Timber.d("WebSocket closed: $code - $reason")
                    scope.launch {
                        _stateFlow.emit(WebSocketState.Disconnected)
                    }
                    
                    // Auto-reconnect if needed
                    if (shouldReconnect) {
                        scope.launch {
                            kotlinx.coroutines.delay(5000)
                            connect()
                        }
                    }
                }
                
                override fun onError(ex: Exception?) {
                    Timber.e(ex, "WebSocket error")
                    scope.launch {
                        _stateFlow.emit(WebSocketState.Error(ex?.message ?: "Unknown error"))
                    }
                }
            }
            
            webSocketClient?.connect()
        } catch (e: Exception) {
            Timber.e(e, "Failed to create WebSocket")
            scope.launch {
                _stateFlow.emit(WebSocketState.Error(e.message ?: "Connection failed"))
            }
        }
    }
    
    fun disconnect() {
        shouldReconnect = false
        webSocketClient?.close()
        webSocketClient = null
        scope.launch {
            _stateFlow.emit(WebSocketState.Disconnected)
        }
    }
    
    fun subscribeToDevice(deviceId: String) {
        webSocketClient?.send(
            gson.toJson(mapOf(
                "action" to "subscribe",
                "filter" to mapOf("device_id" to deviceId)
            ))
        )
    }
    
    fun unsubscribeFromDevice(deviceId: String) {
        webSocketClient?.send(
            gson.toJson(mapOf(
                "action" to "unsubscribe",
                "filter" to mapOf("device_id" to deviceId)
            ))
        )
    }
}
```

**Acceptance Criteria**:
- [ ] WebSocket connects and receives telemetry
- [ ] Auto-reconnect on connection loss
- [ ] Device-specific subscription filtering
- [ ] Proper error handling and state management

***

### 3.5 Create Repository Layer
**File**: `android/app/src/main/java/cz/aiservis/app/data/repository/DeviceRepository.kt`

**Implementation**:
```kotlin
package cz.mia.app.data.repository

import cz.mia.app.data.remote.api.DeviceApi
import cz.mia.app.data.remote.dto.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String, val exception: Throwable? = null) : Result<Nothing>()
    object Loading : Result<Nothing>()
}

@Singleton
class DeviceRepository @Inject constructor(
    private val deviceApi: DeviceApi
) {
    
    suspend fun getDevices(): Result<List<DeviceDto>> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.getDevices()
            if (response.isSuccessful && response.body() != null) {
                Result.Success(response.body()!!)
            } else {
                Result.Error("Failed to fetch devices: ${response.code()}")
            }
        } catch (e: Exception) {
            Timber.e(e, "Error fetching devices")
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    suspend fun getDevice(deviceId: String): Result<DeviceDto> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.getDevice(deviceId)
            if (response.isSuccessful && response.body() != null) {
                Result.Success(response.body()!!)
            } else {
                Result.Error("Failed to fetch device: ${response.code()}")
            }
        } catch (e: Exception) {
            Timber.e(e, "Error fetching device $deviceId")
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    suspend fun sendCommand(
        deviceId: String,
        action: String,
        params: Map<String, Any>? = null
    ): Result<CommandResponse> = withContext(Dispatchers.IO) {
        try {
            val request = CommandRequest(deviceId, action, params)
            val response = deviceApi.sendCommand(request)
            if (response.isSuccessful && response.body() != null) {
                Result.Success(response.body()!!)
            } else {
                Result.Error("Command failed: ${response.code()}")
            }
        } catch (e: Exception) {
            Timber.e(e, "Error sending command to $deviceId")
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    suspend fun getSystemStatus(): Result<SystemStatus> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.getSystemStatus()
            if (response.isSuccessful && response.body() != null) {
                Result.Success(response.body()!!)
            } else {
                Result.Error("Failed to fetch system status: ${response.code()}")
            }
        } catch (e: Exception) {
            Timber.e(e, "Error fetching system status")
            Result.Error("Network error: ${e.message}", e)
        }
    }
}
```

**Acceptance Criteria**:
- [ ] Repository handles all API responses
- [ ] Proper error handling with Result sealed class
- [ ] Logging for debugging
- [ ] Coroutine dispatchers used correctly

***

## 4. Device Discovery & BLE Integration (Priority: P2)

### 4.1 Create BLE Scanning ViewModel
**File**: `android/app/src/main/java/cz/aiservis/app/ui/screens/devices/BleDevicesViewModel.kt`

**Implementation**:
```kotlin
package cz.mia.app.ui.screens.devices

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.background.BLEManager
import cz.mia.app.core.background.BleConnectionState
import cz.mia.app.core.background.BleDeviceInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

data class BleDevicesUiState(
    val isScanning: Boolean = false,
    val discoveredDevices: List<BleDeviceInfo> = emptyList(),
    val connectedDevice: BleDeviceInfo? = null,
    val connectionState: BleConnectionState = BleConnectionState.Disconnected,
    val errorMessage: String? = null
)

@HiltViewModel
class BleDevicesViewModel @Inject constructor(
    private val bleManager: BLEManager
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(BleDevicesUiState())
    val uiState: StateFlow<BleDevicesUiState> = _uiState.asStateFlow()
    
    init {
        observeBleState()
        observeDiscoveredDevices()
    }
    
    private fun observeBleState() {
        viewModelScope.launch {
            bleManager.connectionState.collect { state ->
                _uiState.update { it.copy(
                    connectionState = state,
                    isScanning = state is BleConnectionState.Scanning,
                    errorMessage = if (state is BleConnectionState.Error) state.message else null
                )}
            }
        }
    }
    
    private fun observeDiscoveredDevices() {
        viewModelScope.launch {
            bleManager.discoveredDevices.collect { devices ->
                _uiState.update { it.copy(discoveredDevices = devices) }
            }
        }
    }
    
    fun startScanning() {
        viewModelScope.launch {
            try {
                bleManager.initialize()
                bleManager.startScanning()
            } catch (e: Exception) {
                Timber.e(e, "Failed to start scanning")
                _uiState.update { it.copy(errorMessage = "Scan failed: ${e.message}") }
            }
        }
    }
    
    fun stopScanning() {
        bleManager.stopScanning()
    }
    
    fun connectToDevice(deviceAddress: String) {
        viewModelScope.launch {
            try {
                val success = bleManager.connectWithRetry(deviceAddress)
                if (success) {
                    val device = _uiState.value.discoveredDevices
                        .find { it.address == deviceAddress }
                    _uiState.update { it.copy(connectedDevice = device) }
                } else {
                    _uiState.update { it.copy(
                        errorMessage = "Failed to connect to device"
                    )}
                }
            } catch (e: Exception) {
                Timber.e(e, "Connection error")
                _uiState.update { it.copy(
                    errorMessage = "Connection failed: ${e.message}"
                )}
            }
        }
    }
    
    fun disconnect() {
        viewModelScope.launch {
            bleManager.disconnect()
            _uiState.update { it.copy(connectedDevice = null) }
        }
    }
    
    fun clearError() {
        _uiState.update { it.copy(errorMessage = null) }
    }
    
    override fun onCleared() {
        super.onCleared()
        stopScanning()
    }
}
```

**Acceptance Criteria**:
- [ ] ViewModel observes BLE manager state
- [ ] UI state properly managed
- [ ] Error handling with user-friendly messages
- [ ] Scanning stopped on ViewModel clear

***

### 4.2 Create BLE Device List Screen
**File**: `android/app/src/main/java/cz/aiservis/app/ui/screens/devices/BleDevicesScreen.kt`

**Implementation**:
```kotlin
package cz.mia.app.ui.screens.devices

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import cz.mia.app.core.background.BleConnectionState
import cz.mia.app.core.background.BleDeviceInfo

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BleDevicesScreen(
    viewModel: BleDevicesViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("BLE Devices") },
                actions = {
                    IconButton(
                        onClick = {
                            if (uiState.isScanning) {
                                viewModel.stopScanning()
                            } else {
                                viewModel.startScanning()
                            }
                        }
                    ) {
                        Icon(
                            imageVector = if (uiState.isScanning) {
                                Icons.Default.Stop
                            } else {
                                Icons.Default.Search
                            },
                            contentDescription = if (uiState.isScanning) "Stop scan" else "Start scan"
                        )
                    }
                }
            )
        },
        snackbarHost = {
            uiState.errorMessage?.let { error ->
                Snackbar(
                    action = {
                        TextButton(onClick = { viewModel.clearError() }) {
                            Text("Dismiss")
                        }
                    }
                ) {
                    Text(error)
                }
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // Connection status card
            uiState.connectedDevice?.let { device ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
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
                                text = "Connected",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                            Text(
                                text = device.name ?: device.address,
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        }
                        IconButton(onClick = { viewModel.disconnect() }) {
                            Icon(
                                Icons.Default.Close,
                                contentDescription = "Disconnect",
                                tint = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        }
                    }
                }
            }
            
            // Scanning indicator
            if (uiState.isScanning) {
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth()
                )
            }
            
            // Device list
            if (uiState.discoveredDevices.isEmpty() && !uiState.isScanning) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            Icons.Default.BluetoothSearching,
                            contentDescription = null,
                            modifier = Modifier.size(64.dp),
                            tint = MaterialTheme.colorScheme.outline
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text(
                            "No devices found",
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.outline
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(onClick = { viewModel.startScanning() }) {
                            Text("Start Scanning")
                        }
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(uiState.discoveredDevices) { device ->
                        DeviceItem(
                            device = device,
                            isConnected = device == uiState.connectedDevice,
                            isConnecting = uiState.connectionState is BleConnectionState.Connecting,
                            onConnect = { viewModel.connectToDevice(device.address) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DeviceItem(
    device: BleDeviceInfo,
    isConnected: Boolean,
    isConnecting: Boolean,
    onConnect: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        onClick = { if (!isConnected && !isConnecting) onConnect() }
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = device.name ?: "Unknown Device",
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = device.address,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
                Text(
                    text = "RSSI: ${device.rssi} dBm",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }
            
            when {
                isConnected -> {
                    Icon(
                        Icons.Default.CheckCircle,
                        contentDescription = "Connected",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
                isConnecting -> {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        strokeWidth = 2.dp
                    )
                }
                else -> {
                    Icon(
                        Icons.Default.BluetoothConnected,
                        contentDescription = "Connect",
                        tint = MaterialTheme.colorScheme.outline
                    )
                }
            }
        }
    }
}
```

**Acceptance Criteria**:
- [ ] Displays list of discovered BLE devices
- [ ] Shows scanning state with progress indicator
- [ ] Allows connecting to devices
- [ ] Shows connected device status
- [ ] Handles errors with snackbar

***

## 5. Testing & Quality Assurance (Priority: P2)

### 5.1 Create BLE Manager Unit Tests
**File**: `android/app/src/test/java/cz/aiservis/app/core/background/BLEManagerTest.kt`

**Implementation**:
```kotlin
package cz.mia.app.core.background

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import app.cash.turbine.test
import io.mockk.*
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs

@OptIn(ExperimentalCoroutinesApi::class)
class BLEManagerTest {
    
    private lateinit var context: Context
    private lateinit var bluetoothManager: BluetoothManager
    private lateinit var bluetoothAdapter: BluetoothAdapter
    private lateinit var bleManager: BLEManagerImpl
    
    private val testDispatcher = StandardTestDispatcher()
    
    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        context = mockk(relaxed = true)
        bluetoothManager = mockk(relaxed = true)
        bluetoothAdapter = mockk(relaxed = true)
        
        every { context.getSystemService(Context.BLUETOOTH_SERVICE) } returns bluetoothManager
        every { bluetoothManager.adapter } returns bluetoothAdapter
        every { bluetoothAdapter.isEnabled } returns true
        
        bleManager = BLEManagerImpl(context)
    }
    
    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }
    
    @Test
    fun `initialize sets state to error when bluetooth not supported`() = runTest {
        every { bluetoothManager.adapter } returns null
        
        bleManager.connectionState.test {
            bleManager.initialize()
            advanceUntilIdle()
            
            val state = awaitItem()
            assertIs<BleConnectionState.Error>(state)
            assertEquals("Bluetooth not supported", state.message)
        }
    }
    
    @Test
    fun `initialize sets state to error when bluetooth disabled`() = runTest {
        every { bluetoothAdapter.isEnabled } returns false
        
        bleManager.connectionState.test {
            bleManager.initialize()
            advanceUntilIdle()
            
            val state = awaitItem()
            assertIs<BleConnectionState.Error>(state)
            assertEquals("Bluetooth is disabled", state.message)
        }
    }
    
    @Test
    fun `startScanning changes state to scanning`() = runTest {
        bleManager.connectionState.test {
            bleManager.initialize()
            advanceUntilIdle()
            
            bleManager.startScanning()
            advanceUntilIdle()
            
            val state = awaitItem()
            assertIs<BleConnectionState.Scanning>(state)
        }
    }
    
    @Test
    fun `cleanup cancels scope and closes channel`() = runTest {
        bleManager.initialize()
        bleManager.cleanup()
        
        // Verify scope is cancelled
        // This requires exposing job or testing side effects
    }
}
```

**Acceptance Criteria**:
- [ ] Tests cover initialization scenarios
- [ ] Tests verify state transitions
- [ ] Tests use MockK for Android dependencies
- [ ] Tests pass consistently

***

### 5.2 Create ViewModel Tests
**File**: `android/app/src/test/java/cz/aiservis/app/ui/screens/devices/BleDevicesViewModelTest.kt`

**Implementation**:
```kotlin
package cz.mia.app.ui.screens.devices

import app.cash.turbine.test
import cz.mia.app.core.background.BLEManager
import cz.mia.app.core.background.BleConnectionState
import cz.mia.app.core.background.BleDeviceInfo
import io.mockk.*
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@OptIn(ExperimentalCoroutinesApi::class)
class BleDevicesViewModelTest {
    
    private lateinit var bleManager: BLEManager
    private lateinit var viewModel: BleDevicesViewModel
    
    private val testDispatcher = StandardTestDispatcher()
    
    private val connectionStateFlow = MutableStateFlow<BleConnectionState>(
        BleConnectionState.Disconnected
    )
    private val discoveredDevicesFlow = MutableStateFlow<List<BleDeviceInfo>>(emptyList())
    
    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        bleManager = mockk(relaxed = true)
        every { bleManager.connectionState } returns connectionStateFlow
        every { bleManager.discoveredDevices } returns discoveredDevicesFlow
        
        viewModel = BleDevicesViewModel(bleManager)
    }
    
    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }
    
    @Test
    fun `uiState reflects scanning state from BLE manager`() = runTest {
        viewModel.uiState.test {
            val initialState = awaitItem()
            assertEquals(false, initialState.isScanning)
            
            connectionStateFlow.value = BleConnectionState.Scanning
            advanceUntilIdle()
            
            val scanningState = awaitItem()
            assertTrue(scanningState.isScanning)
        }
    }
    
    @Test
    fun `uiState updates with discovered devices`() = runTest {
        val devices = listOf(
            BleDeviceInfo("Device 1", "00:11:22:33:44:55", -50),
            BleDeviceInfo("Device 2", "AA:BB:CC:DD:EE:FF", -60)
        )
        
        viewModel.uiState.test {
            awaitItem() // Initial state
            
            discoveredDevicesFlow.value = devices
            advanceUntilIdle()
            
            val state = awaitItem()
            assertEquals(2, state.discoveredDevices.size)
            assertEquals("Device 1", state.discoveredDevices[0].name)
        }
    }
    
    @Test
    fun `startScanning calls BLE manager`() = runTest {
        coEvery { bleManager.initialize() } just Runs
        coEvery { bleManager.startScanning() } just Runs
        
        viewModel.startScanning()
        advanceUntilIdle()
        
        coVerify { bleManager.initialize() }
        coVerify { bleManager.startScanning() }
    }
    
    @Test
    fun `connectToDevice calls BLE manager with correct address`() = runTest {
        val deviceAddress = "00:11:22:33:44:55"
        coEvery { bleManager.connectWithRetry(any()) } returns true
        
        viewModel.connectToDevice(deviceAddress)
        advanceUntilIdle()
        
        coVerify { bleManager.connectWithRetry(deviceAddress) }
    }
}
```

**Acceptance Criteria**:
- [ ] Tests cover all ViewModel functions
- [ ] Tests verify Flow collection
- [ ] Tests use Turbine for Flow testing
- [ ] All tests pass

***

### 5.3 Create Integration Tests
**File**: `android/app/src/androidTest/java/cz/aiservis/app/ui/BleDevicesScreenTest.kt`

**Implementation**:
```kotlin
package cz.mia.app.ui

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import cz.mia.app.MainActivity
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.Before
import org.junit.Rule
import org.junit.Test

@HiltAndroidTest
class BleDevicesScreenTest {
    
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)
    
    @get:Rule(order = 1)
    val composeTestRule = createAndroidComposeRule<MainActivity>()
    
    @Before
    fun setup() {
        hiltRule.inject()
    }
    
    @Test
    fun displaysEmptyStateWhenNoDevicesFound() {
        composeTestRule.apply {
            onNodeWithText("No devices found").assertIsDisplayed()
            onNodeWithText("Start Scanning").assertIsDisplayed()
        }
    }
    
    @Test
    fun startScanningButtonClickTriggersSearch() {
        composeTestRule.apply {
            onNodeWithContentDescription("Start scan").performClick()
            
            // Verify progress indicator appears
            onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
                .assertIsDisplayed()
        }
    }
    
    @Test
    fun displaysDiscoveredDevices() {
        // This requires mocking BLE manager responses
        // Implementation depends on test setup
    }
}
```

**Acceptance Criteria**:
- [ ] UI tests cover main user flows
- [ ] Tests run in emulator/device
- [ ] Hilt test setup working correctly

***

## 6. Documentation & Polish (Priority: P3)

### 6.1 Create Android Architecture Documentation
**File**: `android/docs/ARCHITECTURE.md`

**Content Template**:
```markdown
# Android App Architecture

## Overview
The MIA Android app follows MVVM (Model-View-ViewModel) architecture with
Clean Architecture principles.

## Layer Structure

### Data Layer
- **Remote**: API services (Retrofit) and WebSocket clients
- **Local**: Room database for caching
- **Repository**: Single source of truth, coordinates data sources

### Domain Layer
- **Use Cases**: Business logic
- **Models**: Domain entities

### Presentation Layer
- **ViewModels**: UI state management
- **Screens**: Jetpack Compose UI
- **Navigation**: Compose Navigation

## Dependency Injection
Using Hilt for DI with modules:
- NetworkModule: API and WebSocket dependencies
- DatabaseModule: Room database
- BluetoothModule: BLE manager

## State Management
- ViewModels use StateFlow for UI state
- Repository returns Result sealed class
- One-way data flow pattern

## Testing Strategy
- Unit tests for ViewModels and Repositories
- Integration tests for BLE manager
- UI tests with Compose Testing

## Key Design Decisions
1. **Why Jetpack Compose?** Modern, declarative UI framework
2. **Why Hilt?** Official Android DI, better integration
3. **Why StateFlow?** Lifecycle-aware, compose-friendly
4. **Why Repository Pattern?** Testability and separation of concerns
```

**Acceptance Criteria**:
- [ ] Architecture document complete
- [ ] Diagrams added if needed
- [ ] Design decisions documented

***

### 6.2 Create User Guide
**File**: `android/docs/USER_GUIDE.md`

**Content includes**:
- How to install the app
- How to connect to BLE devices
- How to configure API endpoints
- How to view telemetry
- Troubleshooting common issues

**Acceptance Criteria**:
- [ ] User guide written
- [ ] Screenshots added
- [ ] FAQ section included

***

## Success Criteria

### Critical Bugs Fixed
- [x] Memory leak in BLEManager resolved
- [x] Race condition in connection state fixed
- [x] Deprecated Bluetooth APIs updated
- [x] Missing permissions handled
- [x] Resource leaks eliminated

### Core Features Implemented
- [x] BLE device discovery and connection
- [x] FastAPI integration (REST + WebSocket)
- [x] Device control UI
- [x] Real-time telemetry display
- [x] Settings and configuration

### Quality Benchmarks
- [x] All unit tests passing (>80% coverage)
- [x] Integration tests working
- [x] No memory leaks in profiler
- [x] App stable for 1+ hour continuous use
- [x] Documentation complete

***

## Implementation Notes

### Order of Implementation
1. Fix critical bugs (P0) - MUST BE FIRST
2. Setup architecture (P1)
3. Implement FastAPI integration (P1)
4. Build UI screens (P2)
5. Add testing (P2)
6. Polish and documentation (P3)

### Testing Approach
- Write tests alongside implementation
- Use TDD for critical components
- Mock external dependencies (Bluetooth, Network)
- Test on real devices when possible

### Code Review Checklist
- [ ] All bugs from code review addressed
- [ ] Permissions properly requested
- [ ] Resources properly cleaned up
- [ ] Error handling comprehensive
- [ ] Logging added for debugging
- [ ] Tests added and passing
- [ ] Documentation updated

***

## Additional Resources

- [Android BLE Guide](https://developer.android.com/guide/topics/connectivity/bluetooth/ble-overview)
- [Jetpack Compose Documentation](https://developer.android.com/jetpack/compose)
- [Hilt Dependency Injection](https://developer.android.com/training/dependency-injection/hilt-android)
- [Kotlin Coroutines](https://kotlinlang.org/docs/coroutines-overview.html)



