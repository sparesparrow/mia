package cz.mia.app.ui

// @req REQ-AND-024

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import cz.mia.app.ui.components.AlertRow
import cz.mia.app.ui.theme.MiaTheme
import cz.mia.app.ui.theme.mia
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ThemeAndAlertsTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun theme_isDarkWithBrandRed_andErrorIsNotTheBrandRed() {
        var primary = Color.Unspecified
        var background = Color.Unspecified
        var error = Color.Unspecified
        var warning = Color.Unspecified
        composeTestRule.setContent {
            MiaTheme {
                primary = MaterialTheme.colorScheme.primary
                background = MaterialTheme.colorScheme.background
                error = MaterialTheme.colorScheme.error
                warning = MaterialTheme.mia.warning
            }
        }
        composeTestRule.waitForIdle()
        assertEquals(Color(0xFFFF0040), primary)
        assertEquals(Color(0xFF0A0A0A), background)
        assertNotEquals(primary, error)
        assertNotEquals(warning, error)
    }

    @Test
    fun alertRow_showsSeverityWordAndMessageSeparately() {
        composeTestRule.setContent {
            MiaTheme { AlertRow(severity = "CRITICAL", message = "Coolant 112 C") }
        }
        composeTestRule.onNodeWithText("CRITICAL").assertIsDisplayed()
        composeTestRule.onNodeWithText("Coolant 112 C").assertIsDisplayed()
    }
}
