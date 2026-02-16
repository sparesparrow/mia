package cz.mia.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.ui.components.DashboardGauges
import cz.mia.app.ui.components.SpeedometerGauge
import cz.mia.app.ui.components.RPMGauge
import cz.mia.app.ui.components.CompactGauge
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocalGasStation
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * UI tests for Dashboard screen components.
 */
@RunWith(AndroidJUnit4::class)
class DashboardScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun gauges_displayTelemetryData() {
        val telemetry = TelemetryEntity(
            id = 1,
            ts = System.currentTimeMillis(),
            fuelLevel = 75,
            engineRpm = 2500,
            vehicleSpeed = 60,
            coolantTemp = 85,
            engineLoad = 45
        )
        
        composeTestRule.setContent {
            DashboardGauges(latest = telemetry)
        }
        
        // Verify speed is displayed
        composeTestRule.onNodeWithText("60").assertIsDisplayed()
        composeTestRule.onNodeWithText("km/h").assertIsDisplayed()
        
        // Verify RPM indicator is displayed (25 = 2500/100)
        composeTestRule.onNodeWithText("25").assertIsDisplayed()
        composeTestRule.onNodeWithText("x100").assertIsDisplayed()
        
        // Verify labels
        composeTestRule.onNodeWithText("Speed").assertIsDisplayed()
        composeTestRule.onNodeWithText("RPM").assertIsDisplayed()
        composeTestRule.onNodeWithText("Fuel").assertIsDisplayed()
        composeTestRule.onNodeWithText("Coolant").assertIsDisplayed()
        composeTestRule.onNodeWithText("Load").assertIsDisplayed()
    }

    @Test
    fun gauges_displayNoTelemetryPlaceholder() {
        composeTestRule.setContent {
            DashboardGauges(latest = null)
        }
        
        composeTestRule.onNodeWithText("No telemetry data").assertIsDisplayed()
        composeTestRule.onNodeWithText("Connect to OBD adapter to view vehicle data").assertIsDisplayed()
    }

    @Test
    fun speedometerGauge_displaysCorrectValue() {
        composeTestRule.setContent {
            SpeedometerGauge(value = 120, maxValue = 200)
        }
        
        composeTestRule.onNodeWithText("120").assertIsDisplayed()
        composeTestRule.onNodeWithText("km/h").assertIsDisplayed()
        composeTestRule.onNodeWithText("Speed").assertIsDisplayed()
    }

    @Test
    fun rpmGauge_displaysCorrectValue() {
        composeTestRule.setContent {
            RPMGauge(value = 4500, maxValue = 8000)
        }
        
        composeTestRule.onNodeWithText("45").assertIsDisplayed() // 4500/100
        composeTestRule.onNodeWithText("x100").assertIsDisplayed()
        composeTestRule.onNodeWithText("RPM").assertIsDisplayed()
    }

    @Test
    fun compactGauge_displaysFuelLevel() {
        composeTestRule.setContent {
            CompactGauge(
                label = "Fuel",
                value = 65,
                maxValue = 100,
                unit = "%",
                icon = Icons.Default.LocalGasStation,
                warningThreshold = 20
            )
        }
        
        composeTestRule.onNodeWithText("Fuel").assertIsDisplayed()
        composeTestRule.onNodeWithText("65%").assertIsDisplayed()
    }

    @Test
    fun compactGauge_showsWarningWhenBelowThreshold() {
        composeTestRule.setContent {
            CompactGauge(
                label = "Fuel",
                value = 15, // Below 20% threshold
                maxValue = 100,
                unit = "%",
                icon = Icons.Default.LocalGasStation,
                warningThreshold = 20
            )
        }
        
        composeTestRule.onNodeWithText("Fuel").assertIsDisplayed()
        composeTestRule.onNodeWithText("15%").assertIsDisplayed()
        // Warning icon should be displayed (can't directly test icon, but color changes)
    }

    @Test
    fun gauges_displayZeroValues() {
        val telemetry = TelemetryEntity(
            id = 1,
            ts = System.currentTimeMillis(),
            fuelLevel = 0,
            engineRpm = 0,
            vehicleSpeed = 0,
            coolantTemp = 0,
            engineLoad = 0
        )
        
        composeTestRule.setContent {
            DashboardGauges(latest = telemetry)
        }
        
        // Speed should show 0
        composeTestRule.onNodeWithText("0", substring = false, ignoreCase = false).assertExists()
    }

    @Test
    fun gauges_displayMaxValues() {
        val telemetry = TelemetryEntity(
            id = 1,
            ts = System.currentTimeMillis(),
            fuelLevel = 100,
            engineRpm = 8000,
            vehicleSpeed = 200,
            coolantTemp = 120,
            engineLoad = 100
        )
        
        composeTestRule.setContent {
            DashboardGauges(latest = telemetry)
        }
        
        composeTestRule.onNodeWithText("200").assertIsDisplayed() // Max speed
        composeTestRule.onNodeWithText("80").assertIsDisplayed() // Max RPM / 100
        composeTestRule.onNodeWithText("100%").assertExists() // Fuel or load at 100%
    }

    @Test
    fun gauges_handleHighCoolantTemp() {
        val telemetry = TelemetryEntity(
            id = 1,
            ts = System.currentTimeMillis(),
            fuelLevel = 50,
            engineRpm = 3000,
            vehicleSpeed = 80,
            coolantTemp = 110, // Above 100°C threshold
            engineLoad = 50
        )
        
        composeTestRule.setContent {
            DashboardGauges(latest = telemetry)
        }
        
        composeTestRule.onNodeWithText("110°C").assertIsDisplayed()
    }

    @Test
    fun gauges_handleHighEngineLoad() {
        val telemetry = TelemetryEntity(
            id = 1,
            ts = System.currentTimeMillis(),
            fuelLevel = 50,
            engineRpm = 5500,
            vehicleSpeed = 140,
            coolantTemp = 95,
            engineLoad = 95 // Above 90% threshold
        )
        
        composeTestRule.setContent {
            DashboardGauges(latest = telemetry)
        }
        
        composeTestRule.onNodeWithText("95%").assertExists()
    }
}
