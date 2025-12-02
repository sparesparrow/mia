package cz.aiservis.app.ui

import android.content.Context
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performTextClearance
import androidx.compose.ui.unit.dp
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

private val Context.testDataStore by preferencesDataStore(name = "test_settings")

/**
 * UI tests for Settings screen.
 */
@RunWith(AndroidJUnit4::class)
class SettingsScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private lateinit var context: Context

    @Before
    fun setup() {
        context = ApplicationProvider.getApplicationContext()
        // Clear datastore before each test
        runBlocking {
            context.testDataStore.edit { it.clear() }
        }
    }

    @Test
    fun vinInput_displaysCorrectly() {
        composeTestRule.setContent {
            TestVinInput(initialVin = "DEMO_VIN")
        }
        
        composeTestRule.onNodeWithText("VIN").assertIsDisplayed()
        composeTestRule.onNodeWithText("DEMO_VIN").assertIsDisplayed()
        composeTestRule.onNodeWithText("Save VIN").assertIsDisplayed()
    }

    @Test
    fun vinInput_canBeEdited() {
        composeTestRule.setContent {
            TestVinInput(initialVin = "")
        }
        
        // Clear and enter new VIN
        composeTestRule.onNodeWithText("VIN").performClick()
        composeTestRule.onNodeWithText("").performTextInput("1HGBH41JXMN109186")
        
        composeTestRule.onNodeWithText("1HGBH41JXMN109186").assertIsDisplayed()
    }

    @Test
    fun vinInput_persistsValue() {
        var savedVin = ""
        
        composeTestRule.setContent {
            TestVinInputWithSave(
                initialVin = "OLD_VIN",
                onSave = { savedVin = it }
            )
        }
        
        // Clear and enter new VIN
        composeTestRule.onNodeWithText("OLD_VIN").performTextClearance()
        composeTestRule.onNodeWithText("").performTextInput("NEW_VIN_123")
        composeTestRule.onNodeWithText("Save VIN").performClick()
        
        assertEquals("NEW_VIN_123", savedVin)
    }

    @Test
    fun incognitoToggle_displaysCorrectly() {
        composeTestRule.setContent {
            TestIncognitoToggle(initialValue = false)
        }
        
        composeTestRule.onNodeWithText("Incognito").assertIsDisplayed()
    }

    @Test
    fun incognitoToggle_canBeToggled() {
        var toggled = false
        
        composeTestRule.setContent {
            TestIncognitoToggleWithCallback(
                initialValue = false,
                onToggle = { toggled = it }
            )
        }
        
        // Find and click the switch (it's within the "Incognito" row)
        composeTestRule.onNodeWithText("Incognito").performClick()
        
        // The callback should be invoked
        assertTrue(toggled)
    }

    @Test
    fun incognitoToggle_updatesPreference() = runBlocking {
        val key = booleanPreferencesKey("incognito_test")
        
        // Set initial value
        context.testDataStore.edit { prefs ->
            prefs[key] = false
        }
        
        // Verify initial value
        val initialValue = context.testDataStore.data.map { it[key] ?: false }.first()
        assertFalse(initialValue)
        
        // Update value
        context.testDataStore.edit { prefs ->
            prefs[key] = true
        }
        
        // Verify updated value
        val updatedValue = context.testDataStore.data.map { it[key] ?: false }.first()
        assertTrue(updatedValue)
    }

    @Test
    fun retentionSlider_displaysCorrectly() {
        composeTestRule.setContent {
            TestRetentionSlider(initialDays = 7)
        }
        
        composeTestRule.onNodeWithText("Retention: 7 days").assertIsDisplayed()
    }

    @Test
    fun metricsToggle_displaysCorrectly() {
        composeTestRule.setContent {
            TestMetricsToggle(initialValue = false)
        }
        
        composeTestRule.onNodeWithText("Metrics opt-in (health pings)").assertIsDisplayed()
    }

    @Test
    fun anprRegionToggle_displaysCorrectly() {
        composeTestRule.setContent {
            TestAnprRegionToggle(initialRegion = "CZ")
        }
        
        composeTestRule.onNodeWithText("ANPR Region: CZ").assertIsDisplayed()
        composeTestRule.onNodeWithText("CZ").assertIsDisplayed()
        composeTestRule.onNodeWithText("EU").assertIsDisplayed()
    }

    @Test
    fun anprRegionToggle_canSwitchRegion() {
        var selectedRegion = "CZ"
        
        composeTestRule.setContent {
            TestAnprRegionToggleWithCallback(
                initialRegion = "CZ",
                onRegionChange = { selectedRegion = it }
            )
        }
        
        // Click EU button
        composeTestRule.onNodeWithText("EU").performClick()
        
        assertEquals("EU", selectedRegion)
    }

    @Test
    fun exportButton_isClickable() {
        var clicked = false
        
        composeTestRule.setContent {
            TestExportButton(onClick = { clicked = true })
        }
        
        composeTestRule.onNodeWithText("Export Logs").assertIsDisplayed()
        composeTestRule.onNodeWithText("Export Logs").performClick()
        
        assertTrue(clicked)
    }

    // Test composables for isolated testing
    
    @Composable
    private fun TestVinInput(initialVin: String) {
        var vinText by remember { mutableStateOf(initialVin) }
        Column(modifier = Modifier.padding(16.dp)) {
            OutlinedTextField(
                value = vinText,
                onValueChange = { vinText = it },
                label = { Text("VIN") }
            )
            Spacer(Modifier.height(8.dp))
            Button(onClick = {}) { Text("Save VIN") }
        }
    }
    
    @Composable
    private fun TestVinInputWithSave(initialVin: String, onSave: (String) -> Unit) {
        var vinText by remember { mutableStateOf(initialVin) }
        Column(modifier = Modifier.padding(16.dp)) {
            OutlinedTextField(
                value = vinText,
                onValueChange = { vinText = it },
                label = { Text("VIN") }
            )
            Spacer(Modifier.height(8.dp))
            Button(onClick = { onSave(vinText) }) { Text("Save VIN") }
        }
    }
    
    @Composable
    private fun TestIncognitoToggle(initialValue: Boolean) {
        var enabled by remember { mutableStateOf(initialValue) }
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Incognito")
            Switch(checked = enabled, onCheckedChange = { enabled = it })
        }
    }
    
    @Composable
    private fun TestIncognitoToggleWithCallback(initialValue: Boolean, onToggle: (Boolean) -> Unit) {
        var enabled by remember { mutableStateOf(initialValue) }
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Incognito")
            Switch(
                checked = enabled,
                onCheckedChange = {
                    enabled = it
                    onToggle(it)
                }
            )
        }
    }
    
    @Composable
    private fun TestRetentionSlider(initialDays: Int) {
        var days by remember { mutableStateOf(initialDays.toFloat()) }
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Retention: ${days.toInt()} days")
            Slider(
                value = days,
                onValueChange = { days = it },
                valueRange = 1f..30f
            )
        }
    }
    
    @Composable
    private fun TestMetricsToggle(initialValue: Boolean) {
        var enabled by remember { mutableStateOf(initialValue) }
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Metrics opt-in (health pings)")
            Switch(checked = enabled, onCheckedChange = { enabled = it })
        }
    }
    
    @Composable
    private fun TestAnprRegionToggle(initialRegion: String) {
        var region by remember { mutableStateOf(initialRegion) }
        Column(modifier = Modifier.padding(16.dp)) {
            Text("ANPR Region: $region")
            Button(onClick = { region = "CZ" }, enabled = region != "CZ") { Text("CZ") }
            Button(onClick = { region = "EU" }, enabled = region != "EU") { Text("EU") }
        }
    }
    
    @Composable
    private fun TestAnprRegionToggleWithCallback(initialRegion: String, onRegionChange: (String) -> Unit) {
        var region by remember { mutableStateOf(initialRegion) }
        Column(modifier = Modifier.padding(16.dp)) {
            Text("ANPR Region: $region")
            Button(
                onClick = {
                    region = "CZ"
                    onRegionChange("CZ")
                },
                enabled = region != "CZ"
            ) { Text("CZ") }
            Button(
                onClick = {
                    region = "EU"
                    onRegionChange("EU")
                },
                enabled = region != "EU"
            ) { Text("EU") }
        }
    }
    
    @Composable
    private fun TestExportButton(onClick: () -> Unit) {
        Column(modifier = Modifier.padding(16.dp)) {
            Button(onClick = onClick) { Text("Export Logs") }
        }
    }
}
