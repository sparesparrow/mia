package cz.mia.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import cz.mia.app.data.remote.websocket.WebSocketState
import cz.mia.app.ui.components.Cycle1TelemetryCard
import org.junit.Rule
import org.junit.Test

class Cycle1TelemetryCardTest {
    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun disconnectedState_isExplicitlyShown() {
        composeTestRule.setContent {
            Cycle1TelemetryCard(null, WebSocketState.Disconnected)
        }
        composeTestRule.onNodeWithText("Cycle 1 telemetry").assertIsDisplayed()
        composeTestRule.onNodeWithText("Pi offline — no live telemetry").assertIsDisplayed()
    }
}
