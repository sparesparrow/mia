# Android Architecture Documentation

This document describes the architecture, design patterns, and implementation details of the AI-Servis Android application.

## Overview

The AI-Servis Android app follows **MVVM (Model-View-ViewModel)** architecture with **Clean Architecture** principles. The app uses modern Android development practices including Jetpack Compose for UI, Kotlin Coroutines for asynchronous operations, and Hilt for dependency injection.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Screens   │  │  ViewModels │  │  UI State (StateFlow)   │ │
│  │  (Compose)  │──│             │──│                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Domain Layer                              │
│  ┌─────────────────┐  ┌───────────────────────────────────────┐│
│  │  Repositories   │  │  Business Logic / Use Cases           ││
│  └─────────────────┘  └───────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  Remote  │  │   Local  │  │  BLE     │  │   WebSocket    │  │
│  │   APIs   │  │ Database │  │ Manager  │  │    Client      │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Details

### 1. Presentation Layer

#### Screens (Composables)
- Located in `ui/screens/`
- Pure composable functions that display UI
- Observe ViewModel state via `collectAsState()`
- Emit user events to ViewModel

```kotlin
@Composable
fun BleDevicesScreen(
    viewModel: BleDevicesViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    // ... UI rendering
}
```

#### ViewModels
- Located in `ui/screens/` or `features/`
- Extend `ViewModel` with `@HiltViewModel` annotation
- Manage UI state with `StateFlow`
- Handle business logic and data operations

```kotlin
@HiltViewModel
class BleDevicesViewModel @Inject constructor(
    private val bleManager: BLEManager
) : ViewModel() {
    private val _uiState = MutableStateFlow(BleDevicesUiState())
    val uiState: StateFlow<BleDevicesUiState> = _uiState.asStateFlow()
}
```

#### UI State
- Immutable data classes representing screen state
- Contains all data needed for UI rendering
- Updated via `copy()` method

```kotlin
data class BleDevicesUiState(
    val isScanning: Boolean = false,
    val discoveredDevices: List<BleDeviceInfo> = emptyList(),
    val connectionState: BleConnectionState = BleConnectionState.Disconnected,
    val errorMessage: String? = null
)
```

### 2. Domain Layer

#### Repositories
- Located in `data/repository/`
- Provide clean API for data operations
- Abstract data sources from consumers
- Handle error mapping and data transformation

```kotlin
@Singleton
class DeviceRepository @Inject constructor(
    private val deviceApi: DeviceApi
) {
    suspend fun getDevices(): Result<List<DeviceDto>> { ... }
}
```

#### Result Wrapper
- Sealed class for operation results
- Provides type-safe success/error handling

```kotlin
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String, val exception: Throwable? = null) : Result<Nothing>()
    object Loading : Result<Nothing>()
}
```

### 3. Data Layer

#### Remote APIs
- Retrofit interfaces in `data/remote/api/`
- DTOs in `data/remote/dto/`
- WebSocket client in `data/remote/websocket/`

#### Local Storage
- Room database in `data/db/`
- DataStore preferences in `core/storage/`

#### BLE Manager
- Located in `core/background/`
- Handles Bluetooth Low Energy operations
- Manages connection lifecycle

## Dependency Injection with Hilt

### Modules

```
di/
├── NetworkModule.kt      # Retrofit, OkHttp, APIs
├── BluetoothModule.kt    # BLE Manager bindings
└── (other modules)
```

### Scopes
- `@Singleton` - Application-wide instances
- `@ViewModelScoped` - ViewModel lifecycle instances
- `@ActivityScoped` - Activity lifecycle instances

## State Management

### StateFlow Pattern
```kotlin
// Private mutable state
private val _state = MutableStateFlow(InitialState)

// Public read-only exposure
val state: StateFlow<State> = _state.asStateFlow()

// Update state immutably
_state.update { current -> current.copy(field = newValue) }
```

### Sealed Classes for States
```kotlin
sealed class BleConnectionState {
    object Disconnected : BleConnectionState()
    object Scanning : BleConnectionState()
    object Connecting : BleConnectionState()
    object Connected : BleConnectionState()
    data class Error(val message: String) : BleConnectionState()
}
```

## Coroutines & Async Operations

### Dispatchers
- `Dispatchers.Main` - UI operations
- `Dispatchers.IO` - Network/database operations
- `Dispatchers.Default` - CPU-intensive work

### Scope Management
```kotlin
class BLEManagerImpl {
    private val job = SupervisorJob()
    private val scope = CoroutineScope(job + Dispatchers.IO)
    
    suspend fun cleanup() {
        job.cancel()
    }
}
```

### Flow Collection
```kotlin
bleManager.connectionState
    .onEach { state -> handleState(state) }
    .launchIn(viewModelScope)
```

## Testing Strategy

### Unit Tests
- Location: `src/test/`
- Framework: JUnit4, MockK, Turbine
- Test ViewModels, Repositories, Managers

### Integration Tests
- Location: `src/androidTest/`
- Framework: Compose UI Testing, Hilt Testing
- Test UI components and navigation

### Test Structure
```kotlin
@OptIn(ExperimentalCoroutinesApi::class)
class BleDevicesViewModelTest {
    private val testDispatcher = StandardTestDispatcher()
    
    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
    }
    
    @Test
    fun `state updates correctly`() = runTest {
        // Test implementation
    }
}
```

## Key Design Decisions

### 1. MVVM over MVI
- Simpler state management for our use case
- Easier to test and maintain
- Good fit for Compose's reactive paradigm

### 2. StateFlow over LiveData
- Better coroutines integration
- Explicit initial value requirement
- Works seamlessly with Compose

### 3. Hilt over Manual DI
- Compile-time dependency graph
- Reduces boilerplate
- Standard Android recommendation

### 4. Repository Pattern
- Single source of truth for data
- Easy to swap data sources
- Testability through interfaces

### 5. Sealed Classes for States
- Exhaustive when expressions
- Type-safe state handling
- Self-documenting code

## Package Structure

```
cz.mia.app/
├── core/
│   ├── background/     # Background services, BLE, MQTT
│   ├── camera/         # Camera/ANPR processing
│   ├── messaging/      # Serialization
│   ├── networking/     # Network utilities
│   ├── rules/          # Business rules engine
│   ├── security/       # Security utilities
│   ├── storage/        # Preferences, local storage
│   └── voice/          # Voice processing
├── data/
│   ├── db/             # Room database
│   ├── remote/
│   │   ├── api/        # Retrofit interfaces
│   │   ├── dto/        # Data transfer objects
│   │   └── websocket/  # WebSocket client
│   └── repository/     # Repository implementations
├── di/                 # Hilt modules
├── features/           # Feature-specific ViewModels
├── ui/
│   ├── components/     # Reusable UI components
│   └── screens/        # Screen composables + ViewModels
├── utils/              # Utility classes
├── MIAApplication.kt
└── MainActivity.kt
```

## Error Handling

### Network Errors
- Caught in repository layer
- Mapped to `Result.Error`
- Displayed via Snackbar in UI

### BLE Errors
- Handled in `BLEManager`
- Emitted as `BleConnectionState.Error`
- Displayed in UI with retry options

### Validation Errors
- Checked before API calls
- Early return with error state
- User-friendly messages

## Performance Considerations

### Memory Management
- Bounded channels for BLE responses
- Proper coroutine scope cancellation
- StateFlow replay limiting

### Battery Optimization
- BLE scan timeouts
- WorkManager for background tasks
- Efficient polling strategies

### UI Performance
- LazyColumn for device lists
- State hoisting for recomposition optimization
- Stable keys for list items
