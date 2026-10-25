package cz.mia.app.ui

// @req REQ-AND-003

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.ui.components.CitroenReadings
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CitroenReadingsTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun telemetry(
        dpfSootMass: Float? = null,
        adBlueLevel: Int? = null,
        dpfStatus: String? = null,
        particulateFilterEfficiency: Float? = null,
    ) = TelemetryEntity(
        id = 1,
        ts = System.currentTimeMillis(),
        fuelLevel = 75,
        engineRpm = 1800,
        vehicleSpeed = 60,
        coolantTemp = 85,
        engineLoad = 45,
        dpfSootMass = dpfSootMass,
        adBlueLevel = adBlueLevel,
        dpfStatus = dpfStatus,
        particulateFilterEfficiency = particulateFilterEfficiency,
    )

    @Test
    fun displaysTheCitroenValuesTheTelemetryCarries() {
        composeTestRule.setContent {
            CitroenReadings(
                telemetry(dpfSootMass = 23.4f, adBlueLevel = 85, dpfStatus = "ok", particulateFilterEfficiency = 92.5f)
            )
        }

        composeTestRule.onNodeWithText("Citroën C4 readings").assertIsDisplayed()
        composeTestRule.onNodeWithText("DPF soot: 23.4g").assertIsDisplayed()
        composeTestRule.onNodeWithText("DPF status: ok").assertIsDisplayed()
        composeTestRule.onNodeWithText("Filter efficiency: 92.5%").assertIsDisplayed()
        composeTestRule.onNodeWithText("AdBlue level: 85%").assertIsDisplayed()
    }

    @Test
    fun offersNoActionBecauseTheAppNeverActuatesTheCar() {
        composeTestRule.setContent {
            CitroenReadings(
                telemetry(dpfSootMass = 23.4f, adBlueLevel = 85, dpfStatus = "warning", particulateFilterEfficiency = 92.5f)
            )
        }

        composeTestRule.onNodeWithText("Regenerate").assertDoesNotExist()
        composeTestRule.onNodeWithText("Check DPF").assertDoesNotExist()
        composeTestRule.onNodeWithText("Run Diag").assertDoesNotExist()
        composeTestRule.onNodeWithText("Check DTC").assertDoesNotExist()
    }

    @Test
    fun drawsNothingWhenTheTelemetryHasNoCitroenData() {
        composeTestRule.setContent { CitroenReadings(telemetry()) }

        composeTestRule.onNodeWithText("Citroën C4 readings").assertDoesNotExist()
        composeTestRule.onNodeWithText("DPF soot", substring = true).assertDoesNotExist()
        composeTestRule.onNodeWithText("AdBlue level", substring = true).assertDoesNotExist()
    }
}
