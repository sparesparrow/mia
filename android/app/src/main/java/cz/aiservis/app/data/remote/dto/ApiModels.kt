package cz.aiservis.app.data.remote.dto

import com.google.gson.annotations.SerializedName

/**
 * Device status enumeration matching backend API.
 */
enum class DeviceStatus {
    @SerializedName("online")
    ONLINE,
    
    @SerializedName("offline")
    OFFLINE,
    
    @SerializedName("error")
    ERROR
}

/**
 * Device data transfer object from/to the API.
 */
data class DeviceDto(
    @SerializedName("id")
    val id: String,
    
    @SerializedName("name")
    val name: String,
    
    @SerializedName("type")
    val type: String,
    
    @SerializedName("status")
    val status: DeviceStatus,
    
    @SerializedName("capabilities")
    val capabilities: List<String> = emptyList(),
    
    @SerializedName("last_seen")
    val lastSeen: String? = null,
    
    @SerializedName("firmware_version")
    val firmwareVersion: String? = null,
    
    @SerializedName("metadata")
    val metadata: Map<String, Any>? = null
)

/**
 * Request to send a command to a device.
 */
data class CommandRequest(
    @SerializedName("device_id")
    val deviceId: String,
    
    @SerializedName("action")
    val action: String,
    
    @SerializedName("params")
    val params: Map<String, Any>? = null
)

/**
 * Response from a command execution.
 */
data class CommandResponse(
    @SerializedName("success")
    val success: Boolean,
    
    @SerializedName("message")
    val message: String? = null,
    
    @SerializedName("data")
    val data: Map<String, Any>? = null,
    
    @SerializedName("error_code")
    val errorCode: String? = null
)

/**
 * Single telemetry reading from a sensor.
 */
data class TelemetryReading(
    @SerializedName("device_id")
    val deviceId: String,
    
    @SerializedName("timestamp")
    val timestamp: String,
    
    @SerializedName("sensor")
    val sensor: String,
    
    @SerializedName("value")
    val value: Double,
    
    @SerializedName("unit")
    val unit: String
)

/**
 * Batch of telemetry readings for upload.
 */
data class TelemetryBatch(
    @SerializedName("readings")
    val readings: List<TelemetryReading>
)

/**
 * System status information.
 */
data class SystemStatus(
    @SerializedName("uptime")
    val uptime: Long,
    
    @SerializedName("cpu_usage")
    val cpuUsage: Double,
    
    @SerializedName("memory_usage")
    val memoryUsage: Double,
    
    @SerializedName("active_devices")
    val activeDevices: Int,
    
    @SerializedName("total_devices")
    val totalDevices: Int,
    
    @SerializedName("version")
    val version: String? = null,
    
    @SerializedName("healthy")
    val healthy: Boolean = true
)

/**
 * Response wrapper for paginated results.
 */
data class PaginatedResponse<T>(
    @SerializedName("items")
    val items: List<T>,
    
    @SerializedName("total")
    val total: Int,
    
    @SerializedName("page")
    val page: Int,
    
    @SerializedName("page_size")
    val pageSize: Int,
    
    @SerializedName("has_more")
    val hasMore: Boolean
)

/**
 * Error response from the API.
 */
data class ApiError(
    @SerializedName("error")
    val error: String,
    
    @SerializedName("message")
    val message: String,
    
    @SerializedName("code")
    val code: Int? = null,
    
    @SerializedName("details")
    val details: Map<String, Any>? = null
)

/**
 * Device pairing request.
 */
data class PairDeviceRequest(
    @SerializedName("device_id")
    val deviceId: String,
    
    @SerializedName("device_name")
    val deviceName: String? = null,
    
    @SerializedName("device_type")
    val deviceType: String? = null
)

/**
 * Device pairing response.
 */
data class PairDeviceResponse(
    @SerializedName("success")
    val success: Boolean,
    
    @SerializedName("device")
    val device: DeviceDto? = null,
    
    @SerializedName("message")
    val message: String? = null
)

/**
 * WebSocket subscription message.
 */
data class WebSocketSubscription(
    @SerializedName("action")
    val action: String,  // "subscribe" or "unsubscribe"
    
    @SerializedName("device_id")
    val deviceId: String? = null,
    
    @SerializedName("channels")
    val channels: List<String>? = null
)
