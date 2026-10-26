package cz.mia.app.ui

// @req REQ-AND-017

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import cz.mia.app.core.voice.console.ConnectionState
import cz.mia.app.core.voice.console.ConsoleCommand
import cz.mia.app.core.voice.console.VerbosityLevel
import cz.mia.app.core.voice.console.VoiceConsoleState
import cz.mia.app.ui.components.VoiceSettingsSection
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class VoiceSettingsSectionTest {
    @get:Rule
    val composeTestRule = createComposeRule()

    private val reported = VoiceConsoleState(
        connection = ConnectionState.CONNECTED,
        verbosity = VerbosityLevel.NORMAL,
        persona = "mia",
        personas = listOf("mia", "holly", "rimmer"),
        language = "en",
        languages = listOf("cs", "en"),
    )

    @Test
    fun personaAndLanguageChipsComeFromThePiAndSendTheirCommand() {
        val pressed = mutableListOf<ConsoleCommand>()
        composeTestRule.setContent {
            VoiceSettingsSection(reported, { pressed += it; true })
        }
        composeTestRule.onNodeWithTag("voice_persona_mia").assertIsSelected()
        composeTestRule.onNodeWithTag("voice_persona_rimmer").assertIsDisplayed().performClick()
        composeTestRule.onNodeWithTag("voice_language_cs").performClick()

        assertEquals(listOf(ConsoleCommand.SwitchPersona("rimmer"), ConsoleCommand.SetLanguage("cs")), pressed)
    }

    @Test
    fun withoutAConnectionNothingIsReportedAndNothingCanBePressed() {
        composeTestRule.setContent {
            VoiceSettingsSection(reported.forgetSettings().copy(connection = ConnectionState.DISCONNECTED), { true })
        }
        composeTestRule.onNodeWithTag("voice_persona_unknown").assertIsDisplayed()
        composeTestRule.onNodeWithTag("voice_language_unknown").assertIsDisplayed()
        composeTestRule.onNodeWithTag("voice_verbosity_quiet").assertIsNotEnabled()
    }
}
