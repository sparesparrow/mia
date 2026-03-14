package cz.mia.app.data.repository

import cz.mia.app.data.remote.api.SessionApi
import cz.mia.app.data.remote.dto.CreateSessionRequest
import cz.mia.app.data.remote.dto.HandoffResponse
import cz.mia.app.data.remote.dto.ResumeSessionRequest
import cz.mia.app.data.remote.dto.SessionDto
import cz.mia.app.data.remote.dto.UpdateSessionRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SessionRepository @Inject constructor(
    private val sessionApi: SessionApi
) {

    suspend fun createSession(
        clientType: String,
        clientName: String,
        metadata: Map<String, Any> = emptyMap()
    ): Result<SessionDto> = withContext(Dispatchers.IO) {
        try {
            val response = sessionApi.createSession(
                CreateSessionRequest(clientType, clientName, metadata)
            )
            if (response.isSuccessful) {
                response.body()?.session?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Failed to create session: ${response.code()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }

    suspend fun getSession(sessionId: String): Result<SessionDto> = withContext(Dispatchers.IO) {
        try {
            val response = sessionApi.getSession(sessionId)
            if (response.isSuccessful) {
                response.body()?.session?.let {
                    Result.Success(it)
                } ?: Result.Error("Session not found")
            } else {
                Result.Error("Failed to get session: ${response.code()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }

    suspend fun updateSubscriptions(
        sessionId: String,
        deviceSubscriptions: List<String>
    ): Result<SessionDto> = withContext(Dispatchers.IO) {
        try {
            val response = sessionApi.updateSession(
                sessionId, UpdateSessionRequest(deviceSubscriptions = deviceSubscriptions)
            )
            if (response.isSuccessful) {
                response.body()?.session?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Failed to update session: ${response.code()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }

    suspend fun deleteSession(sessionId: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = sessionApi.deleteSession(sessionId)
            if (response.isSuccessful) {
                Result.Success(Unit)
            } else {
                Result.Error("Failed to delete session: ${response.code()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }

    suspend fun generateHandoff(sessionId: String): Result<HandoffResponse> = withContext(Dispatchers.IO) {
        try {
            val response = sessionApi.generateHandoff(sessionId)
            if (response.isSuccessful) {
                response.body()?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Handoff failed: ${response.code()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }

    suspend fun resumeSession(handoffToken: String): Result<SessionDto> = withContext(Dispatchers.IO) {
        try {
            val response = sessionApi.resumeSession(ResumeSessionRequest(handoffToken))
            if (response.isSuccessful) {
                response.body()?.session?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Invalid or expired handoff token: ${response.code()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
}
