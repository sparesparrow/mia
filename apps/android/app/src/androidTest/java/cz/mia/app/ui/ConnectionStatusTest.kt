package cz.mia.app.ui

// @req REQ-AND-022

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.google.gson.JsonPrimitive
import cz.mia.app.data.db.TelemetryEntity
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.dto.Cycle1TelemetrySignal
import cz.mia.app.data.remote.dto.Cycle1TelemetrySignals
import cz.mia.app.data.remote.websocket.WebSocketState
import cz.mia.app.ui.components.Cycle1StatusChip
import cz.mia.app.ui.components.DashboardTelemetrySection
import cz.mia.app.ui.theme.MiaTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ConnectionStatusTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun envelope() = Cycle1TelemetryEnvelope(
        schemaVersion = 1,
        messageType = "telemetry",
        deviceId = "pi-test",
        timestamp = "2026-01-01T00:00:00Z",
        source = "obd-sim",
        confidence = 0.9,
        signals = mapOf(
            Cycle1TelemetrySignals.ENGINE_RPM to Cycle1TelemetrySignal(JsonPrimitive(800), "rpm", "obd-sim", 0.92),
        ),
    )

    @Test
    fun chip_saysPiOnlineWithSourceAndConfidence() {
        composeTestRule.setContent {
            MiaTheme { Cycle1StatusChip(envelope(), WebSocketState.Connected) }
        }
        composeTestRule.onNodeWithText("Pi online", substring = true).assertIsDisplayed()
        composeTestRule.onNodeWithText("source obd-sim", substring = true).assertIsDisplayed()
        composeTestRule.onNodeWithText("confidence 0.92", substring = true).assertIsDisplayed()
    }

    @Test
    fun chip_saysPiOfflineWhenDisconnected() {
        composeTestRule.setContent {
            MiaTheme { Cycle1StatusChip(null, WebSocketState.Disconnected) }
        }
        composeTestRule.onNodeWithText("Pi offline", substring = true).assertIsDisplayed()
    }

    @Test
    fun liveCycle1Data_hidesTheNoTelemetryPlaceholder() {
        composeTestRule.setContent {
            MiaTheme { DashboardTelemetrySection(null, envelope(), WebSocketState.Connected) }
        }
        composeTestRule.onNodeWithText("Pi online", substring = true).assertIsDisplayed()
        composeTestRule.onNodeWithText("No telemetry data").assertDoesNotExist()
        composeTestRule.onNodeWithText("Connect to OBD adapter to view vehicle data").assertDoesNotExist()
    }

    @Test
    fun noData_stillShowsThePlaceholder() {
        composeTestRule.setContent {
            MiaTheme { DashboardTelemetrySection(null, null, WebSocketState.Disconnected) }
        }
        composeTestRule.onNodeWithText("Pi offline", substring = true).assertIsDisplayed()
        composeTestRule.onNodeWithText("No telemetry data").assertIsDisplayed()
    }

    @Test
    fun phoneReading_showsTheGauges() {
        val reading = TelemetryEntity(
            id = 1,
            ts = System.currentTimeMillis(),
            fuelLevel = 75,
            engineRpm = 2500,
            vehicleSpeed = 60,
            coolantTemp = 85,
            engineLoad = 45,
        )
        composeTestRule.setContent {
            MiaTheme { DashboardTelemetrySection(reading, envelope(), WebSocketState.Connected) }
        }
        composeTestRule.onNodeWithText("Speed").assertIsDisplayed()
        composeTestRule.onNodeWithText("No telemetry data").assertDoesNotExist()
    }
}
