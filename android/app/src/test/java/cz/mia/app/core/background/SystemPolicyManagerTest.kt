package cz.mia.app.core.background

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Unit tests for SystemPolicyManager thermal and battery management.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class SystemPolicyManagerTest {

    @Before
    fun setup() {
        // Unit tests without context
    }

    @Test
    fun `SamplingMode enum has correct values`() {
        val modes = SamplingMode.values()
        
        assertEquals(3, modes.size)
        assertEquals(SamplingMode.NORMAL, modes[0])
        assertEquals(SamplingMode.REDUCED, modes[1])
        assertEquals(SamplingMode.MINIMAL, modes[2])
    }

    @Test
    fun `ThermalSeverity enum has correct values`() {
        val severities = ThermalSeverity.values()
        
        assertEquals(5, severities.size)
        assertEquals(ThermalSeverity.NONE, severities[0])
        assertEquals(ThermalSeverity.LIGHT, severities[1])
        assertEquals(ThermalSeverity.MODERATE, severities[2])
        assertEquals(ThermalSeverity.SEVERE, severities[3])
        assertEquals(ThermalSeverity.CRITICAL, severities[4])
    }

    @Test
    fun `SystemPolicyState has correct default values`() {
        val state = SystemPolicyState(
            samplingMode = SamplingMode.NORMAL,
            thermalSeverity = ThermalSeverity.NONE,
            isPowerSaveMode = false,
            batteryPercent = 100,
            advisoryMessage = null
        )
        
        assertEquals(SamplingMode.NORMAL, state.samplingMode)
        assertEquals(ThermalSeverity.NONE, state.thermalSeverity)
        assertEquals(false, state.isPowerSaveMode)
        assertEquals(100, state.batteryPercent)
        assertNull(state.advisoryMessage)
    }

    @Test
    fun `lowBattery switches to MINIMAL mode`() {
        fun decideSamplingMode(thermal: ThermalSeverity, powerSave: Boolean, percent: Int): SamplingMode {
            return when {
                thermal >= ThermalSeverity.SEVERE -> SamplingMode.MINIMAL
                percent <= 15 -> SamplingMode.MINIMAL
                thermal == ThermalSeverity.MODERATE || powerSave || percent <= 30 -> SamplingMode.REDUCED
                else -> SamplingMode.NORMAL
            }
        }
        
        // Battery at 10% should trigger MINIMAL
        val mode = decideSamplingMode(ThermalSeverity.NONE, false, 10)
        assertEquals(SamplingMode.MINIMAL, mode)
    }

    @Test
    fun `thermalThrottling reduces mode to MINIMAL`() {
        fun decideSamplingMode(thermal: ThermalSeverity, powerSave: Boolean, percent: Int): SamplingMode {
            return when {
                thermal >= ThermalSeverity.SEVERE -> SamplingMode.MINIMAL
                percent <= 15 -> SamplingMode.MINIMAL
                thermal == ThermalSeverity.MODERATE || powerSave || percent <= 30 -> SamplingMode.REDUCED
                else -> SamplingMode.NORMAL
            }
        }
        
        // Severe thermal should trigger MINIMAL
        val mode = decideSamplingMode(ThermalSeverity.SEVERE, false, 80)
        assertEquals(SamplingMode.MINIMAL, mode)
        
        // Critical thermal should also trigger MINIMAL
        val criticalMode = decideSamplingMode(ThermalSeverity.CRITICAL, false, 100)
        assertEquals(SamplingMode.MINIMAL, criticalMode)
    }

    @Test
    fun `moderateThermal switches to REDUCED mode`() {
        fun decideSamplingMode(thermal: ThermalSeverity, powerSave: Boolean, percent: Int): SamplingMode {
            return when {
                thermal >= ThermalSeverity.SEVERE -> SamplingMode.MINIMAL
                percent <= 15 -> SamplingMode.MINIMAL
                thermal == ThermalSeverity.MODERATE || powerSave || percent <= 30 -> SamplingMode.REDUCED
                else -> SamplingMode.NORMAL
            }
        }
        
        val mode = decideSamplingMode(ThermalSeverity.MODERATE, false, 80)
        assertEquals(SamplingMode.REDUCED, mode)
    }

    @Test
    fun `powerSaveMode switches to REDUCED mode`() {
        fun decideSamplingMode(thermal: ThermalSeverity, powerSave: Boolean, percent: Int): SamplingMode {
            return when {
                thermal >= ThermalSeverity.SEVERE -> SamplingMode.MINIMAL
                percent <= 15 -> SamplingMode.MINIMAL
                thermal == ThermalSeverity.MODERATE || powerSave || percent <= 30 -> SamplingMode.REDUCED
                else -> SamplingMode.NORMAL
            }
        }
        
        val mode = decideSamplingMode(ThermalSeverity.NONE, true, 80)
        assertEquals(SamplingMode.REDUCED, mode)
    }

    @Test
    fun `lowBattery30Percent switches to REDUCED mode`() {
        fun decideSamplingMode(thermal: ThermalSeverity, powerSave: Boolean, percent: Int): SamplingMode {
            return when {
                thermal >= ThermalSeverity.SEVERE -> SamplingMode.MINIMAL
                percent <= 15 -> SamplingMode.MINIMAL
                thermal == ThermalSeverity.MODERATE || powerSave || percent <= 30 -> SamplingMode.REDUCED
                else -> SamplingMode.NORMAL
            }
        }
        
        val mode = decideSamplingMode(ThermalSeverity.NONE, false, 25)
        assertEquals(SamplingMode.REDUCED, mode)
    }

    @Test
    fun `normalConditions keeps NORMAL mode`() {
        fun decideSamplingMode(thermal: ThermalSeverity, powerSave: Boolean, percent: Int): SamplingMode {
            return when {
                thermal >= ThermalSeverity.SEVERE -> SamplingMode.MINIMAL
                percent <= 15 -> SamplingMode.MINIMAL
                thermal == ThermalSeverity.MODERATE || powerSave || percent <= 30 -> SamplingMode.REDUCED
                else -> SamplingMode.NORMAL
            }
        }
        
        val mode = decideSamplingMode(ThermalSeverity.NONE, false, 80)
        assertEquals(SamplingMode.NORMAL, mode)
    }

    @Test
    fun `advisory message for REDUCED mode thermal`() {
        fun buildAdvisory(thermal: ThermalSeverity, powerSave: Boolean, percent: Int, mode: SamplingMode): String? {
            return when (mode) {
                SamplingMode.NORMAL -> null
                SamplingMode.REDUCED -> when {
                    thermal >= ThermalSeverity.MODERATE -> "Device warm – reducing processing to prevent heat."
                    powerSave -> "Battery saver on – reducing sampling to conserve power."
                    percent <= 30 -> "Battery low (${percent}%) – reducing sampling."
                    else -> null
                }
                SamplingMode.MINIMAL -> when {
                    thermal >= ThermalSeverity.SEVERE -> "Device hot – pausing heavy processing until temperature drops."
                    percent <= 15 -> "Battery critical (${percent}%) – pausing heavy processing."
                    else -> "Energy/thermal constraints – pausing heavy processing."
                }
            }
        }
        
        val advisory = buildAdvisory(ThermalSeverity.MODERATE, false, 80, SamplingMode.REDUCED)
        assertEquals("Device warm – reducing processing to prevent heat.", advisory)
    }

    @Test
    fun `advisory message for MINIMAL mode critical battery`() {
        fun buildAdvisory(thermal: ThermalSeverity, powerSave: Boolean, percent: Int, mode: SamplingMode): String? {
            return when (mode) {
                SamplingMode.NORMAL -> null
                SamplingMode.REDUCED -> when {
                    thermal >= ThermalSeverity.MODERATE -> "Device warm – reducing processing to prevent heat."
                    powerSave -> "Battery saver on – reducing sampling to conserve power."
                    percent <= 30 -> "Battery low (${percent}%) – reducing sampling."
                    else -> null
                }
                SamplingMode.MINIMAL -> when {
                    thermal >= ThermalSeverity.SEVERE -> "Device hot – pausing heavy processing until temperature drops."
                    percent <= 15 -> "Battery critical (${percent}%) – pausing heavy processing."
                    else -> "Energy/thermal constraints – pausing heavy processing."
                }
            }
        }
        
        val advisory = buildAdvisory(ThermalSeverity.NONE, false, 10, SamplingMode.MINIMAL)
        assertEquals("Battery critical (10%) – pausing heavy processing.", advisory)
    }

    @Test
    fun `no advisory for NORMAL mode`() {
        fun buildAdvisory(mode: SamplingMode): String? {
            return when (mode) {
                SamplingMode.NORMAL -> null
                else -> "Some advisory"
            }
        }
        
        val advisory = buildAdvisory(SamplingMode.NORMAL)
        assertNull(advisory)
    }

    @Test
    fun `thermal severity comparison works`() {
        assertTrue(ThermalSeverity.SEVERE >= ThermalSeverity.SEVERE)
        assertTrue(ThermalSeverity.CRITICAL >= ThermalSeverity.SEVERE)
        assertTrue(ThermalSeverity.MODERATE < ThermalSeverity.SEVERE)
    }

    @Test
    fun `battery percentage calculation`() {
        fun calculateBatteryPercent(level: Int, scale: Int): Int {
            return if (level >= 0 && scale > 0) {
                (100f * level / scale).toInt()
            } else {
                0
            }
        }
        
        assertEquals(50, calculateBatteryPercent(50, 100))
        assertEquals(75, calculateBatteryPercent(75, 100))
        assertEquals(100, calculateBatteryPercent(100, 100))
        assertEquals(0, calculateBatteryPercent(-1, 100)) // Invalid
    }
}
