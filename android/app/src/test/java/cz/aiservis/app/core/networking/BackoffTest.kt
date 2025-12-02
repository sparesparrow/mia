package cz.aiservis.app.core.networking

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Unit tests for Backoff utility functions.
 */
class BackoffTest {

    @Test
    fun `exponential doubles each attempt`() {
        val delays = Backoff.exponential(baseMs = 100, maxMs = 10000, attempts = 5)
        
        assertEquals(5, delays.size)
        assertEquals(100L, delays[0])
        assertEquals(200L, delays[1])
        assertEquals(400L, delays[2])
        assertEquals(800L, delays[3])
        assertEquals(1600L, delays[4])
    }

    @Test
    fun `exponential caps at max value`() {
        val delays = Backoff.exponential(baseMs = 1000, maxMs = 5000, attempts = 10)
        
        assertEquals(10, delays.size)
        assertEquals(1000L, delays[0])
        assertEquals(2000L, delays[1])
        assertEquals(4000L, delays[2])
        assertEquals(5000L, delays[3]) // Capped at max
        assertEquals(5000L, delays[4]) // Stays at max
        
        // All remaining should be capped at max
        for (i in 3 until delays.size) {
            assertEquals(5000L, delays[i])
        }
    }

    @Test
    fun `exponential with BLE defaults`() {
        // BLE connection retry defaults
        val delays = Backoff.exponential(baseMs = 250, maxMs = 8000, attempts = 6)
        
        assertEquals(6, delays.size)
        assertEquals(250L, delays[0])
        assertEquals(500L, delays[1])
        assertEquals(1000L, delays[2])
        assertEquals(2000L, delays[3])
        assertEquals(4000L, delays[4])
        assertEquals(8000L, delays[5])
    }

    @Test
    fun `exponential with single attempt`() {
        val delays = Backoff.exponential(baseMs = 500, maxMs = 15000, attempts = 1)
        
        assertEquals(1, delays.size)
        assertEquals(500L, delays[0])
    }

    @Test
    fun `exponential with zero attempts returns empty list`() {
        val delays = Backoff.exponential(baseMs = 500, maxMs = 15000, attempts = 0)
        
        assertEquals(0, delays.size)
    }

    @Test
    fun `linearDelays returns provided values`() {
        val delays = Backoff.linearDelays(100, 200, 300, 500, 1000)
        
        assertEquals(5, delays.size)
        assertEquals(100L, delays[0])
        assertEquals(200L, delays[1])
        assertEquals(300L, delays[2])
        assertEquals(500L, delays[3])
        assertEquals(1000L, delays[4])
    }

    @Test
    fun `linearDelays with single value`() {
        val delays = Backoff.linearDelays(1000)
        
        assertEquals(1, delays.size)
        assertEquals(1000L, delays[0])
    }

    @Test
    fun `linearDelays with no values returns empty list`() {
        val delays = Backoff.linearDelays()
        
        assertEquals(0, delays.size)
    }

    @Test
    fun `exponential default parameters`() {
        // Test default values: baseMs = 500, maxMs = 15000, attempts = 5
        val delays = Backoff.exponential()
        
        assertEquals(5, delays.size)
        assertEquals(500L, delays[0])
        assertEquals(1000L, delays[1])
        assertEquals(2000L, delays[2])
        assertEquals(4000L, delays[3])
        assertEquals(8000L, delays[4])
    }

    @Test
    fun `exponential respects maxMs from start`() {
        // If baseMs > maxMs, it should still be capped
        val delays = Backoff.exponential(baseMs = 10000, maxMs = 5000, attempts = 3)
        
        assertEquals(3, delays.size)
        // First value would be 10000, but gets capped to 5000
        assertEquals(5000L, delays[0])
        assertEquals(5000L, delays[1])
        assertEquals(5000L, delays[2])
    }

    @Test
    fun `exponential total time calculation`() {
        val delays = Backoff.exponential(baseMs = 100, maxMs = 10000, attempts = 5)
        val totalTime = delays.sum()
        
        // 100 + 200 + 400 + 800 + 1600 = 3100ms
        assertEquals(3100L, totalTime)
    }

    @Test
    fun `exponential doubles correctly at boundary`() {
        val delays = Backoff.exponential(baseMs = 4000, maxMs = 8000, attempts = 3)
        
        assertEquals(3, delays.size)
        assertEquals(4000L, delays[0])
        assertEquals(8000L, delays[1]) // Exactly at max
        assertEquals(8000L, delays[2]) // Stays at max
    }

    @Test
    fun `exponential with very small values`() {
        val delays = Backoff.exponential(baseMs = 1, maxMs = 100, attempts = 10)
        
        assertEquals(10, delays.size)
        assertEquals(1L, delays[0])
        assertEquals(2L, delays[1])
        assertEquals(4L, delays[2])
        assertEquals(8L, delays[3])
        assertEquals(16L, delays[4])
        assertEquals(32L, delays[5])
        assertEquals(64L, delays[6])
        assertEquals(100L, delays[7]) // Capped
        assertEquals(100L, delays[8])
        assertEquals(100L, delays[9])
    }

    @Test
    fun `exponential provides predictable retry pattern`() {
        val delays = Backoff.exponential(baseMs = 500, maxMs = 15000, attempts = 5)
        
        // Verify the pattern is strictly increasing until cap
        for (i in 1 until delays.size) {
            assertTrue(delays[i] >= delays[i - 1])
        }
    }
}
