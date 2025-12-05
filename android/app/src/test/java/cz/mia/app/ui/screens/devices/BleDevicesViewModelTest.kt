package cz.mia.app.ui.screens.devices

import app.cash.turbine.test
import cz.mia.app.core.background.BLEManager
import cz.mia.app.core.background.BleConnectionState
import cz.mia.app.core.background.BleDeviceInfo
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Unit tests for BleDevicesViewModel.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class BleDevicesViewModelTest {

    private lateinit var bleManager: BLEManager
    private lateinit var viewModel: BleDevicesViewModel
    
    private val testDispatcher = StandardTestDispatcher()
    
    private val connectionStateFlow = MutableStateFlow<BleConnectionState>(BleConnectionState.Disconnected)
    private val discoveredDevicesFlow = MutableStateFlow<List<BleDeviceInfo>>(emptyList())

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        bleManager = mockk(relaxed = true)
        
        every { bleManager.connectionState } returns connectionStateFlow
        every { bleManager.discoveredDevices } returns discoveredDevicesFlow
        every { bleManager.isConnected() } returns false
        coEvery { bleManager.initialize() } returns Unit
        
        viewModel = BleDevicesViewModel(bleManager)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `initial state is correct`() = runTest {
        advanceUntilIdle()
        
        val state = viewModel.uiState.value
        
        assertFalse(state.isScanning)
        assertTrue(state.discoveredDevices.isEmpty())
        assertNull(state.connectedDevice)
        assertTrue(state.connectionState is BleConnectionState.Disconnected)
        assertNull(state.errorMessage)
    }

    @Test
    fun `uiState reflects scanning state from BLE manager`() = runTest {
        advanceUntilIdle()
        
        // Simulate scanning state change
        connectionStateFlow.value = BleConnectionState.Scanning
        advanceUntilIdle()
        
        assertTrue(viewModel.uiState.value.isScanning)
        
        // Simulate scan stopped
        connectionStateFlow.value = BleConnectionState.Disconnected
        advanceUntilIdle()
        
        assertFalse(viewModel.uiState.value.isScanning)
    }

    @Test
    fun `uiState updates with discovered devices`() = runTest {
        advanceUntilIdle()
        
        val testDevices = listOf(
            BleDeviceInfo("OBD Device 1", "AA:BB:CC:DD:EE:FF", -50),
            BleDeviceInfo("OBD Device 2", "11:22:33:44:55:66", -65)
        )
        
        discoveredDevicesFlow.value = testDevices
        advanceUntilIdle()
        
        assertEquals(2, viewModel.uiState.value.discoveredDevices.size)
        assertEquals("OBD Device 1", viewModel.uiState.value.discoveredDevices[0].name)
        assertEquals("AA:BB:CC:DD:EE:FF", viewModel.uiState.value.discoveredDevices[0].address)
    }

    @Test
    fun `startScanning calls BLE manager`() = runTest {
        advanceUntilIdle()
        
        viewModel.startScanning()
        advanceUntilIdle()
        
        coVerify { bleManager.startScanning() }
    }

    @Test
    fun `stopScanning calls BLE manager`() = runTest {
        advanceUntilIdle()
        
        viewModel.stopScanning()
        advanceUntilIdle()
        
        verify { bleManager.stopScanning() }
    }

    @Test
    fun `toggleScanning starts when not scanning`() = runTest {
        advanceUntilIdle()
        connectionStateFlow.value = BleConnectionState.Disconnected
        advanceUntilIdle()
        
        viewModel.toggleScanning()
        advanceUntilIdle()
        
        coVerify { bleManager.startScanning() }
    }

    @Test
    fun `toggleScanning stops when scanning`() = runTest {
        advanceUntilIdle()
        connectionStateFlow.value = BleConnectionState.Scanning
        advanceUntilIdle()
        
        viewModel.toggleScanning()
        advanceUntilIdle()
        
        verify { bleManager.stopScanning() }
    }

    @Test
    fun `connectToDevice calls BLE manager with correct address`() = runTest {
        val testAddress = "AA:BB:CC:DD:EE:FF"
        coEvery { bleManager.connectWithRetry(testAddress) } returns true
        
        advanceUntilIdle()
        
        viewModel.connectToDevice(testAddress)
        advanceUntilIdle()
        
        coVerify { bleManager.connectWithRetry(testAddress) }
    }

    @Test
    fun `connectToDevice sets error on failure`() = runTest {
        val testAddress = "AA:BB:CC:DD:EE:FF"
        coEvery { bleManager.connectWithRetry(testAddress) } returns false
        
        advanceUntilIdle()
        
        viewModel.connectToDevice(testAddress)
        advanceUntilIdle()
        
        assertEquals("Failed to connect to device", viewModel.uiState.value.errorMessage)
    }

    @Test
    fun `disconnect calls BLE manager`() = runTest {
        advanceUntilIdle()
        
        viewModel.disconnect()
        advanceUntilIdle()
        
        coVerify { bleManager.disconnect() }
    }

    @Test
    fun `clearError removes error message`() = runTest {
        advanceUntilIdle()
        
        // First set an error
        connectionStateFlow.value = BleConnectionState.Error("Test error")
        advanceUntilIdle()
        
        assertEquals("Test error", viewModel.uiState.value.errorMessage)
        
        // Clear the error
        viewModel.clearError()
        advanceUntilIdle()
        
        assertNull(viewModel.uiState.value.errorMessage)
    }

    @Test
    fun `error state is reflected in uiState`() = runTest {
        advanceUntilIdle()
        
        connectionStateFlow.value = BleConnectionState.Error("Connection failed")
        advanceUntilIdle()
        
        assertEquals("Connection failed", viewModel.uiState.value.errorMessage)
        assertTrue(viewModel.uiState.value.connectionState is BleConnectionState.Error)
    }

    @Test
    fun `connected state updates connectedDevice`() = runTest {
        val testDevice = BleDeviceInfo("OBD Device", "AA:BB:CC:DD:EE:FF", -50)
        discoveredDevicesFlow.value = listOf(testDevice)
        
        advanceUntilIdle()
        
        // Simulate connection process
        coEvery { bleManager.connectWithRetry("AA:BB:CC:DD:EE:FF") } returns true
        
        viewModel.connectToDevice("AA:BB:CC:DD:EE:FF")
        advanceUntilIdle()
        
        // Simulate connected state
        connectionStateFlow.value = BleConnectionState.Connected
        advanceUntilIdle()
        
        assertEquals(testDevice, viewModel.uiState.value.connectedDevice)
    }

    @Test
    fun `refresh stops and starts scanning`() = runTest {
        advanceUntilIdle()
        
        viewModel.refresh()
        advanceUntilIdle()
        
        verify { bleManager.stopScanning() }
        coVerify { bleManager.startScanning() }
    }

    @Test
    fun `isConnected delegates to BLE manager`() = runTest {
        every { bleManager.isConnected() } returns true
        
        assertTrue(viewModel.isConnected())
        
        every { bleManager.isConnected() } returns false
        
        assertFalse(viewModel.isConnected())
    }

    @Test
    fun `sendCommand calls BLE manager and returns result`() = runTest {
        val testCommand = "ATZ"
        val expectedResponse = "OK"
        coEvery { bleManager.sendCommand(testCommand) } returns expectedResponse
        
        advanceUntilIdle()
        
        var result: String? = null
        viewModel.sendCommand(testCommand) { response ->
            result = response
        }
        advanceUntilIdle()
        
        assertEquals(expectedResponse, result)
        coVerify { bleManager.sendCommand(testCommand) }
    }

}
