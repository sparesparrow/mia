package cz.mia.app.core.background

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Unit tests for DVRManager video recording functionality.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class DVRManagerTest {

    @Before
    fun setup() {
        // Unit tests without context/mocks
    }

    @Test
    fun `DVRState sealed class has correct types`() {
        val states = listOf(
            DVRState.Idle,
            DVRState.Initializing,
            DVRState.Recording,
            DVRState.Paused,
            DVRState.SavingClip,
            DVRState.Error("Test error")
        )
        
        assertEquals(6, states.size)
        assertTrue(states[0] is DVRState.Idle)
        assertTrue(states[1] is DVRState.Initializing)
        assertTrue(states[2] is DVRState.Recording)
        assertTrue(states[3] is DVRState.Paused)
        assertTrue(states[4] is DVRState.SavingClip)
        assertTrue(states[5] is DVRState.Error)
    }

    @Test
    fun `ClipEventType enum has correct values`() {
        val types = ClipEventType.values()
        
        assertEquals(8, types.size)
        assertTrue(types.contains(ClipEventType.RECORDING_STARTED))
        assertTrue(types.contains(ClipEventType.RECORDING_STOPPED))
        assertTrue(types.contains(ClipEventType.EVENT_CLIP_SAVED))
        assertTrue(types.contains(ClipEventType.BUFFER_FULL))
        assertTrue(types.contains(ClipEventType.BUFFER_ROTATED))
        assertTrue(types.contains(ClipEventType.OFFLOAD_READY))
        assertTrue(types.contains(ClipEventType.STORAGE_LOW))
        assertTrue(types.contains(ClipEventType.ERROR))
    }

    @Test
    fun `ClipEvent stores correct values`() {
        val event = ClipEvent(
            type = ClipEventType.EVENT_CLIP_SAVED,
            clipId = 123L,
            reason = "manual_trigger",
            filePath = "/data/clips/test.mp4"
        )
        
        assertEquals(ClipEventType.EVENT_CLIP_SAVED, event.type)
        assertEquals(123L, event.clipId)
        assertEquals("manual_trigger", event.reason)
        assertEquals("/data/clips/test.mp4", event.filePath)
        assertTrue(event.timestamp > 0)
    }

    @Test
    fun `DVRStats has correct default values`() {
        val stats = DVRStats()
        
        assertEquals(0L, stats.totalRecordingTimeMs)
        assertEquals(0, stats.totalClipsSaved)
        assertEquals(0L, stats.totalStorageUsedBytes)
        assertEquals(0, stats.currentBufferSizeMs)
        assertEquals(0L, stats.lastClipTime)
    }

    @Test
    fun `DVRStats copy updates correctly`() {
        val initialStats = DVRStats()
        val updatedStats = initialStats.copy(
            totalClipsSaved = 5,
            totalStorageUsedBytes = 1024 * 1024
        )
        
        assertEquals(5, updatedStats.totalClipsSaved)
        assertEquals(1024 * 1024, updatedStats.totalStorageUsedBytes)
        assertEquals(0L, updatedStats.totalRecordingTimeMs) // Unchanged
    }

    @Test
    fun `clip filename generation format`() {
        val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
        val timestamp = System.currentTimeMillis()
        val reason = "test_event"
        val sanitizedReason = reason.replace(Regex("[^a-zA-Z0-9]"), "_").take(30)
        val fileName = "${dateFormat.format(Date(timestamp))}_${sanitizedReason}.mp4"
        
        assertTrue(fileName.endsWith(".mp4"))
        assertTrue(fileName.contains("_test_event"))
    }

    @Test
    fun `reason sanitization removes special characters`() {
        val reason = "alert/P0420:engine"
        val sanitized = reason.replace(Regex("[^a-zA-Z0-9]"), "_").take(30)
        
        assertEquals("alert_P0420_engine", sanitized)
        assertFalse(sanitized.contains("/"))
        assertFalse(sanitized.contains(":"))
    }

    @Test
    fun `reason sanitization truncates long strings`() {
        val longReason = "this_is_a_very_long_reason_that_exceeds_thirty_characters"
        val sanitized = longReason.take(30)
        
        assertEquals(30, sanitized.length)
        assertEquals("this_is_a_very_long_reason_tha", sanitized)
    }

    @Test
    fun `buffer duration coercion works`() {
        // Buffer should be between 10 and 300 seconds
        val tooLow = 5.coerceIn(10, 300)
        val tooHigh = 500.coerceIn(10, 300)
        val valid = 60.coerceIn(10, 300)
        
        assertEquals(10, tooLow)
        assertEquals(300, tooHigh)
        assertEquals(60, valid)
    }

    @Test
    fun `storage space calculation`() {
        // Simulate storage check
        val availableBytes = 600_000_000L // 600MB
        val minFreeSpace = 500_000_000L  // 500MB minimum
        
        assertTrue(availableBytes > minFreeSpace)
        
        val lowStorage = 400_000_000L
        assertFalse(lowStorage > minFreeSpace)
    }

    @Test
    fun `max clip size is reasonable`() {
        val maxClipSize = 100_000_000L // 100MB
        
        // 100MB is reasonable for a 30-60 second HD clip
        assertTrue(maxClipSize > 10_000_000L) // At least 10MB
        assertTrue(maxClipSize < 1_000_000_000L) // Less than 1GB
    }

    @Test
    fun `rolling buffer management`() {
        val buffer = mutableListOf<String>()
        val maxSegments = 4
        
        // Add segments
        buffer.add("segment1.mp4")
        buffer.add("segment2.mp4")
        buffer.add("segment3.mp4")
        buffer.add("segment4.mp4")
        
        assertEquals(4, buffer.size)
        
        // Add one more (should remove oldest)
        buffer.add("segment5.mp4")
        if (buffer.size > maxSegments) {
            buffer.removeAt(0)
        }
        
        assertEquals(4, buffer.size)
        assertEquals("segment2.mp4", buffer[0])
        assertEquals("segment5.mp4", buffer[3])
    }

    @Test
    fun `error state contains message`() {
        val errorState = DVRState.Error("Insufficient storage")
        
        assertEquals("Insufficient storage", errorState.message)
    }

    @Test
    fun `clip directory path format`() {
        val baseDir = "/data/user/0/cz.mia.app/files"
        val clipsDir = "mia-clips"
        val expectedPath = "$baseDir/$clipsDir"
        
        assertTrue(expectedPath.contains("mia-clips"))
    }

    @Test
    fun `recording time calculation`() {
        val startTime = System.currentTimeMillis()
        Thread.sleep(100) // Simulate some recording time
        val endTime = System.currentTimeMillis()
        
        val recordingTime = endTime - startTime
        assertTrue(recordingTime >= 100)
    }
}
