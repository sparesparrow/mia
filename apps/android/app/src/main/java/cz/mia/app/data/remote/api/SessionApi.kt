package cz.mia.app.data.remote.api

import cz.mia.app.data.remote.dto.CreateSessionRequest
import cz.mia.app.data.remote.dto.HandoffResponse
import cz.mia.app.data.remote.dto.ResumeSessionRequest
import cz.mia.app.data.remote.dto.SessionResponse
import cz.mia.app.data.remote.dto.UpdateSessionRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * Retrofit API interface for session management endpoints.
 */
interface SessionApi {

    @POST("sessions")
    suspend fun createSession(
        @Body request: CreateSessionRequest
    ): Response<SessionResponse>

    @GET("sessions/{session_id}")
    suspend fun getSession(
        @Path("session_id") sessionId: String
    ): Response<SessionResponse>

    @PATCH("sessions/{session_id}")
    suspend fun updateSession(
        @Path("session_id") sessionId: String,
        @Body request: UpdateSessionRequest
    ): Response<SessionResponse>

    @DELETE("sessions/{session_id}")
    suspend fun deleteSession(
        @Path("session_id") sessionId: String
    ): Response<Map<String, Any>>

    @POST("sessions/{session_id}/handoff")
    suspend fun generateHandoff(
        @Path("session_id") sessionId: String
    ): Response<HandoffResponse>

    @POST("sessions/resume")
    suspend fun resumeSession(
        @Body request: ResumeSessionRequest
    ): Response<SessionResponse>
}
