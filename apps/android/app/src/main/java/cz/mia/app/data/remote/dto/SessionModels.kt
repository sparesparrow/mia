package cz.mia.app.data.remote.dto

import com.google.gson.annotations.SerializedName

data class CreateSessionRequest(
    @SerializedName("client_type")
    val clientType: String,

    @SerializedName("client_name")
    val clientName: String,

    @SerializedName("metadata")
    val metadata: Map<String, Any> = emptyMap()
)

data class UpdateSessionRequest(
    @SerializedName("device_subscriptions")
    val deviceSubscriptions: List<String>? = null,

    @SerializedName("metadata")
    val metadata: Map<String, Any>? = null
)

data class ResumeSessionRequest(
    @SerializedName("handoff_token")
    val handoffToken: String
)

data class SessionDto(
    @SerializedName("session_id")
    val sessionId: String,

    @SerializedName("client_type")
    val clientType: String,

    @SerializedName("client_name")
    val clientName: String,

    @SerializedName("created_at")
    val createdAt: String,

    @SerializedName("last_active")
    val lastActive: String,

    @SerializedName("device_subscriptions")
    val deviceSubscriptions: List<String> = emptyList(),

    @SerializedName("handoff_token")
    val handoffToken: String? = null,

    @SerializedName("metadata")
    val metadata: Map<String, Any> = emptyMap()
)

data class SessionResponse(
    @SerializedName("session")
    val session: SessionDto,

    @SerializedName("timestamp")
    val timestamp: String
)

data class HandoffResponse(
    @SerializedName("handoff_token")
    val handoffToken: String,

    @SerializedName("expires_in_seconds")
    val expiresInSeconds: Int,

    @SerializedName("timestamp")
    val timestamp: String
)
