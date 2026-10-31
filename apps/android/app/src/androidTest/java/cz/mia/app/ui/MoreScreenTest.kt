package cz.mia.app.ui

// @req REQ-AND-023

import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import cz.mia.app.ui.screens.MoreDestination
import cz.mia.app.ui.screens.MoreScreen
import cz.mia.app.ui.theme.MiaTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MoreScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun showMore() {
        composeTestRule.setContent {
            MiaTheme {
                var current by remember { mutableStateOf<MoreDestination?>(null) }
                MoreScreen(current = current, onSelect = { current = it }) { destination, _ ->
                    Text("screen for " + destination.title)
                }
            }
        }
    }

    @Test
    fun moreList_showsAlertsObdPairingAndSettings() {
        showMore()
        composeTestRule.onNodeWithText("Alerts").assertIsDisplayed()
        composeTestRule.onNodeWithText("OBD pairing").assertIsDisplayed()
        composeTestRule.onNodeWithText("Settings").assertIsDisplayed()
    }

    @Test
    fun tappingAnEntry_showsThatScreen_andBackReturnsToTheList() {
        showMore()

        composeTestRule.onNodeWithText("OBD pairing").performClick()
        composeTestRule.onNodeWithText("screen for OBD pairing").assertIsDisplayed()
        composeTestRule.onNodeWithText("Settings").assertDoesNotExist()

        composeTestRule.onNodeWithContentDescription("Back to More").performClick()
        composeTestRule.onNodeWithText("OBD pairing").assertIsDisplayed()
        composeTestRule.onNodeWithText("Settings").assertIsDisplayed()
    }
}
