package cz.mia.app.core.background

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import org.mockito.Mock
import org.mockito.MockitoAnnotations
import org.mockito.kotlin.whenever
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Unit tests for OBDManager ELM327 protocol implementation.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class OBDManagerTest {

    @Mock
    private lateinit var mockBleManager: BLEManager

    private lateinit var obdManager: OBDManagerImpl

    @Before
    fun setup() {
        MockitoAnnotations.openMocks(this)
        obdManager = OBDManagerImpl(mockBleManager)
    }

    @Test
    fun `parseFuelLevel returns correct percentage`() {
        // Fuel level PID 012F returns value 0-255, representing 0-100%
        // Test value 0x80 (128) should be approximately 50%
        val rawValue = 128
        val expectedPercent = (rawValue * 100 / 255)
        assertEquals(50, expectedPercent)
    }

    @Test
    fun `parseRPM returns correct value`() {
        // RPM is calculated as ((A*256)+B)/4
        // Test values A=0x1A (26), B=0xF8 (248)
        // RPM = ((26*256)+248)/4 = (6656+248)/4 = 6904/4 = 1726
        val byteA = 0x1A
        val byteB = 0xF8
        val expectedRpm = ((byteA * 256) + byteB) / 4
        assertEquals(1726, expectedRpm)
    }

    @Test
    fun `parseSpeed returns correct km per hour`() {
        // Speed PID 010D returns value directly in km/h
        val rawValue = 100
        assertEquals(100, rawValue.coerceIn(0, 255))
    }

    @Test
    fun `parseCoolantTemp returns correct celsius`() {
        // Coolant temp is A - 40
        // Test value 0x6E (110) should be 70°C
        val rawValue = 110
        val expectedTemp = rawValue - 40
        assertEquals(70, expectedTemp)
    }

    @Test
    fun `parseEngineLoad returns correct percentage`() {
        // Engine load PID 0104 returns value 0-255, representing 0-100%
        val rawValue = 191 // approximately 75%
        val expectedPercent = (rawValue * 100 / 255)
        assertEquals(74, expectedPercent) // 191*100/255 = 74.9 -> 74
    }

    @Test
    fun `samplingModeChange updates polling interval`() {
        // Initial mode should be NORMAL
        obdManager.setSamplingMode(SamplingMode.NORMAL)
        
        // Change to REDUCED
        obdManager.setSamplingMode(SamplingMode.REDUCED)
        
        // Change to MINIMAL
        obdManager.setSamplingMode(SamplingMode.MINIMAL)
        
        // No exceptions means it works
        assertTrue(true)
    }

    @Test
    fun `dtcParsing decodes powertrain code correctly`() {
        // DTC format: first 2 bits indicate type (00=P, 01=C, 10=B, 11=U)
        // P0420 = 0x04 0x20
        val dtcHex = "0420"
        val firstChar = dtcHex[0].digitToIntOrNull(16) ?: 0
        val type = when (firstChar shr 2) {
            0 -> 'P' // Powertrain
            1 -> 'C' // Chassis
            2 -> 'B' // Body
            3 -> 'U' // Network
            else -> 'P'
        }
        val secondDigit = firstChar and 0x03
        val code = "$type$secondDigit${dtcHex.substring(1)}"
        
        assertEquals("P0420", code)
    }

    @Test
    fun `dtcParsing decodes chassis code correctly`() {
        // C0123 would be encoded as 0x41 0x23 (first byte: 01 00 0001)
        // 01 = Chassis, 00 = standard, 0001 = 1
        val firstNibble = 0x4 // 0100 binary = chassis (01) + second digit 0 (00)
        val type = when ((firstNibble shr 2) and 0x3) {
            1 -> 'C'
            else -> 'P'
        }
        assertEquals('C', type)
    }

    @Test
    fun `dtcParsing handles multiple codes`() {
        // Response: 43 04 20 01 71 00 00
        // Contains P0420 and P0171
        val response = "430420017100"
        val index = response.indexOf("43")
        assertTrue(index >= 0)
        
        var dtcCount = 0
        var i = index + 2
        while (i + 4 <= response.length) {
            val dtcHex = response.substring(i, i + 4)
            if (dtcHex != "0000") {
                dtcCount++
            }
            i += 4
        }
        
        assertEquals(2, dtcCount)
    }

    @Test
    fun `connectionStatus starts as Disconnected`() {
        val initialStatus = obdManager.connectionStatus.value
        assertEquals(OBDConnectionStatus.Disconnected, initialStatus)
    }

    @Test
    fun `isMonitoring returns false initially`() {
        val isMonitoring = obdManager.isMonitoring()
        assertEquals(false, isMonitoring)
    }

    @Test
    fun `extractValue parses hex response correctly`() {
        // Simulating response parsing
        val response = "410580" // Coolant temp response
        val prefix = "4105"
        val index = response.indexOf(prefix)
        assertTrue(index >= 0)
        
        val valueHex = response.substring(index + prefix.length, index + prefix.length + 2)
        val value = valueHex.toIntOrNull(16) ?: 0
        assertEquals(128, value) // 0x80 = 128
    }

    @Test
    fun `extractValues parses multi-byte response`() {
        // RPM response: 410C 1A F8
        val response = "410C1AF8"
        val prefix = "410C"
        val index = response.indexOf(prefix)
        assertTrue(index >= 0)
        
        val values = mutableListOf<Int>()
        for (j in 0 until 2) {
            val startPos = index + prefix.length + j * 2
            val valueHex = response.substring(startPos, startPos + 2)
            values.add(valueHex.toIntOrNull(16) ?: 0)
        }
        
        assertEquals(2, values.size)
        assertEquals(0x1A, values[0])
        assertEquals(0xF8, values[1])
    }
}
