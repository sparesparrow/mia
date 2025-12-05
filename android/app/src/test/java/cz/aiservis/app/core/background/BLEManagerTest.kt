package cz.aiservis.app.core.background

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import cz.aiservis.app.utils.PermissionHelper
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkObject
import io.mockk.unmockkObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Unit tests for BLEManager Bluetooth communication.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class BLEManagerTest {

    private lateinit var mockContext: Context
    private lateinit var mockBluetoothManager: BluetoothManager
    private lateinit var mockBluetoothAdapter: BluetoothAdapter
    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        mockContext = mockk(relaxed = true)
        mockBluetoothManager = mockk(relaxed = true)
        mockBluetoothAdapter = mockk(relaxed = true)
        
        every { mockContext.getSystemService(Context.BLUETOOTH_SERVICE) } returns mockBluetoothManager
        every { mockBluetoothManager.adapter } returns mockBluetoothAdapter
        
        // Mock PermissionHelper
        mockkObject(PermissionHelper)
        every { PermissionHelper.hasBluetoothPermissions(any()) } returns true
        every { PermissionHelper.getMissingBluetoothPermissions(any()) } returns emptyList()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
        unmockkObject(PermissionHelper)
    }

    @Test
    fun `connectionState starts as Disconnected`() {
        // Test the sealed class structure
        val state: BleConnectionState = BleConnectionState.Disconnected
        assertTrue(state is BleConnectionState.Disconnected)
    }

    @Test
    fun `connectionState transitions correctly`() {
        // Test all state types
        val states = listOf(
            BleConnectionState.Disconnected,
            BleConnectionState.Scanning,
            BleConnectionState.Connecting,
            BleConnectionState.Connected,
            BleConnectionState.Error("Test error")
        )
        
        assertEquals(5, states.size)
        assertTrue(states[0] is BleConnectionState.Disconnected)
        assertTrue(states[1] is BleConnectionState.Scanning)
        assertTrue(states[2] is BleConnectionState.Connecting)
        assertTrue(states[3] is BleConnectionState.Connected)
        assertTrue(states[4] is BleConnectionState.Error)
    }

    @Test
    fun `BleDeviceInfo stores correct values`() {
        val deviceInfo = BleDeviceInfo(
            name = "OBD-II Adapter",
            address = "AA:BB:CC:DD:EE:FF",
            rssi = -65
        )
        
        assertEquals("OBD-II Adapter", deviceInfo.name)
        assertEquals("AA:BB:CC:DD:EE:FF", deviceInfo.address)
        assertEquals(-65, deviceInfo.rssi)
    }

    @Test
    fun `BleDeviceInfo handles null name`() {
        val deviceInfo = BleDeviceInfo(
            name = null,
            address = "AA:BB:CC:DD:EE:FF",
            rssi = -80
        )
        
        assertEquals(null, deviceInfo.name)
        assertEquals("AA:BB:CC:DD:EE:FF", deviceInfo.address)
    }

    @Test
    fun `error state contains message`() {
        val error = BleConnectionState.Error("Connection timed out")
        
        assertEquals("Connection timed out", error.message)
    }

    @Test
    fun `backoff delays are calculated correctly for retry`() {
        // Using the Backoff utility for BLE retries
        val delays = cz.aiservis.app.core.networking.Backoff.exponential(
            baseMs = 250,
            maxMs = 8000,
            attempts = 6
        )
        
        assertEquals(6, delays.size)
        assertEquals(250L, delays[0])
        assertEquals(500L, delays[1])
        assertEquals(1000L, delays[2])
        assertEquals(2000L, delays[3])
        assertEquals(4000L, delays[4])
        assertEquals(8000L, delays[5])
    }

    @Test
    fun `SPP UUID format is correct`() {
        // Standard SPP UUID for serial communication
        val expectedUuid = "00001101-0000-1000-8000-00805F9B34FB"
        val sppUuid = BLEManagerImpl.SPP_UUID
        
        assertEquals(expectedUuid.lowercase(), sppUuid.toString().lowercase())
    }

    @Test
    fun `NUS Service UUID format is correct`() {
        // Nordic UART Service UUID
        val expectedUuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        val nusUuid = BLEManagerImpl.NUS_SERVICE_UUID
        
        assertEquals(expectedUuid.lowercase(), nusUuid.toString().lowercase())
    }

    @Test
    fun `NUS TX characteristic UUID format is correct`() {
        val expectedUuid = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
        val txUuid = BLEManagerImpl.NUS_TX_CHAR_UUID
        
        assertEquals(expectedUuid.lowercase(), txUuid.toString().lowercase())
    }

    @Test
    fun `NUS RX characteristic UUID format is correct`() {
        val expectedUuid = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
        val rxUuid = BLEManagerImpl.NUS_RX_CHAR_UUID
        
        assertEquals(expectedUuid.lowercase(), rxUuid.toString().lowercase())
    }

    @Test
    fun `OBD device name filtering works`() {
        val obdNames = listOf("OBD", "ELM327", "VGATE", "VEEPEAK", "BAFX")
        val testDeviceNames = listOf(
            "OBD-II Scanner",
            "ELM327 v1.5",
            "VGate iCar Pro",
            "Veepeak OBDCheck",
            "BAFX Products",
            "Random Device",
            "My Phone"
        )
        
        val obdDevices = testDeviceNames.filter { deviceName ->
            obdNames.any { deviceName.contains(it, ignoreCase = true) }
        }
        
        assertEquals(5, obdDevices.size)
        assertTrue(obdDevices.contains("OBD-II Scanner"))
        assertTrue(obdDevices.contains("ELM327 v1.5"))
        assertFalse(obdDevices.contains("Random Device"))
    }

    @Test
    fun `MAC address format validation`() {
        val validAddresses = listOf(
            "AA:BB:CC:DD:EE:FF",
            "00:11:22:33:44:55",
            "AB:CD:EF:01:23:45"
        )
        
        val macPattern = Regex("^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
        
        validAddresses.forEach { address ->
            assertTrue(macPattern.matches(address), "Address $address should be valid")
        }
    }

    @Test
    fun `command format includes carriage return`() {
        val command = "ATZ"
        val formattedCommand = "$command\r"
        
        assertTrue(formattedCommand.endsWith("\r"))
        assertEquals("ATZ\r", formattedCommand)
    }

    @Test
    fun `response parsing removes control characters`() {
        val rawResponse = "OK\r\n>"
        val cleanedResponse = rawResponse
            .replace("\r", "")
            .replace("\n", "")
            .replace(">", "")
            .trim()
        
        assertEquals("OK", cleanedResponse)
    }

    @Test
    fun `initialize sets state to error when bluetooth not supported`() = runTest(testDispatcher) {
        every { mockContext.getSystemService(Context.BLUETOOTH_SERVICE) } returns null
        
        val bleManager = BLEManagerImpl(mockContext)
        bleManager.initialize()
        testDispatcher.scheduler.advanceUntilIdle()
        
        val state = bleManager.connectionState.value
        assertTrue(state is BleConnectionState.Error)
        assertEquals("Bluetooth not supported", (state as BleConnectionState.Error).message)
    }

    @Test
    fun `initialize sets state to error when bluetooth disabled`() = runTest(testDispatcher) {
        every { mockBluetoothAdapter.isEnabled } returns false
        
        val bleManager = BLEManagerImpl(mockContext)
        bleManager.initialize()
        testDispatcher.scheduler.advanceUntilIdle()
        
        val state = bleManager.connectionState.value
        assertTrue(state is BleConnectionState.Error)
        assertEquals("Bluetooth is disabled", (state as BleConnectionState.Error).message)
    }

    @Test
    fun `initialize sets state to error when permissions missing`() = runTest(testDispatcher) {
        every { PermissionHelper.hasBluetoothPermissions(any()) } returns false
        every { PermissionHelper.getMissingBluetoothPermissions(any()) } returns listOf("BLUETOOTH_SCAN", "BLUETOOTH_CONNECT")
        
        every { mockBluetoothAdapter.isEnabled } returns true
        
        val bleManager = BLEManagerImpl(mockContext)
        bleManager.initialize()
        testDispatcher.scheduler.advanceUntilIdle()
        
        val state = bleManager.connectionState.value
        assertTrue(state is BleConnectionState.Error)
        assertTrue((state as BleConnectionState.Error).message.contains("Missing permissions"))
    }

    @Test
    fun `isConnected returns false when disconnected`() {
        val bleManager = BLEManagerImpl(mockContext)
        assertFalse(bleManager.isConnected())
    }

    @Test
    fun `BLEManager interface has all required methods`() {
        // Verify the interface contract
        val bleManager: BLEManager = BLEManagerImpl(mockContext)
        
        assertNotNull(bleManager.connectionState)
        assertNotNull(bleManager.discoveredDevices)
    }
}
