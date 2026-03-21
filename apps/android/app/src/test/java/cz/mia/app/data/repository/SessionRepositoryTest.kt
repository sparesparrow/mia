package cz.mia.app.data.repository

import cz.mia.app.data.remote.api.SessionApi
import cz.mia.app.data.remote.dto.HandoffResponse
import cz.mia.app.data.remote.dto.SessionDto
import cz.mia.app.data.remote.dto.SessionResponse
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import org.mockito.kotlin.any
import org.mockito.kotlin.mock
import org.mockito.kotlin.whenever
import retrofit2.Response
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class SessionRepositoryTest {

    private lateinit var sessionApi: SessionApi
    private lateinit var repository: SessionRepository

    @Before
    fun setup() {
        sessionApi = mock()
        repository = SessionRepository(sessionApi)
    }

    private fun sampleSession(
        sessionId: String = "test-session-123",
        clientType: String = "android",
        clientName: String = "Test Phone"
    ) = SessionDto(
        sessionId = sessionId,
        clientType = clientType,
        clientName = clientName,
        createdAt = "2026-03-12T10:00:00",
        lastActive = "2026-03-12T10:00:00"
    )

    @Test
    fun `createSession returns unwrapped SessionDto`() = runTest {
        val session = sampleSession()
        whenever(sessionApi.createSession(any())).thenReturn(
            Response.success(SessionResponse(session = session, timestamp = "2026-03-12T10:00:00"))
        )

        val result = repository.createSession("android", "Test Phone")
        assertTrue(result.isSuccess)
        assertEquals("test-session-123", result.getOrThrow().sessionId)
        assertEquals("android", result.getOrThrow().clientType)
    }

    @Test
    fun `getSession returns session`() = runTest {
        val session = sampleSession()
        whenever(sessionApi.getSession(any())).thenReturn(
            Response.success(SessionResponse(session = session, timestamp = "2026-03-12T10:00:00"))
        )

        val result = repository.getSession("test-session-123")
        assertTrue(result.isSuccess)
        assertEquals("test-session-123", result.getOrThrow().sessionId)
    }

    @Test
    fun `updateSubscriptions returns updated session`() = runTest {
        val session = sampleSession().copy(
            deviceSubscriptions = listOf("esp32-obd-001", "pi-gateway-001")
        )
        whenever(sessionApi.updateSession(any(), any())).thenReturn(
            Response.success(SessionResponse(session = session, timestamp = "2026-03-12T10:00:00"))
        )

        val result = repository.updateSubscriptions("test-session-123", listOf("esp32-obd-001", "pi-gateway-001"))
        assertTrue(result.isSuccess)
        assertEquals(2, result.getOrThrow().deviceSubscriptions.size)
    }

    @Test
    fun `generateHandoff returns token`() = runTest {
        whenever(sessionApi.generateHandoff(any())).thenReturn(
            Response.success(HandoffResponse(
                handoffToken = "abc123token",
                expiresInSeconds = 300,
                timestamp = "2026-03-12T10:00:00"
            ))
        )

        val result = repository.generateHandoff("test-session-123")
        assertTrue(result.isSuccess)
        assertEquals("abc123token", result.getOrThrow().handoffToken)
        assertEquals(300, result.getOrThrow().expiresInSeconds)
    }

    @Test
    fun `resumeSession returns session on valid token`() = runTest {
        val session = sampleSession()
        whenever(sessionApi.resumeSession(any())).thenReturn(
            Response.success(SessionResponse(session = session, timestamp = "2026-03-12T10:00:00"))
        )

        val result = repository.resumeSession("valid-token")
        assertTrue(result.isSuccess)
        assertEquals("test-session-123", result.getOrThrow().sessionId)
    }

    @Test
    fun `deleteSession returns success`() = runTest {
        whenever(sessionApi.deleteSession(any())).thenReturn(
            Response.success(mapOf("success" to true))
        )

        val result = repository.deleteSession("test-session-123")
        assertTrue(result.isSuccess)
    }

    @Test
    fun `createSession returns error on network failure`() = runTest {
        whenever(sessionApi.createSession(any())).thenThrow(RuntimeException("Timeout"))

        val result = repository.createSession("android", "Test Phone")
        assertTrue(result.isError)
    }
}
