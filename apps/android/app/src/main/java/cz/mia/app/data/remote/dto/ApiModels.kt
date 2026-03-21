package cz.mia.app.data.remote.dto

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
    ERROR,

    @SerializedName("initializing")
    INITIALIZING,

    @SerializedName("unknown")
    UNKNOWN
}

/**
 * Device data transfer object — aligned with RPi DeviceProfile.to_dict().
 */
data class DeviceDto(
    @SerializedName("device_id")
    val deviceId: String,

    @SerializedName("name")
    val name: String,

    @SerializedName("device_type")
    val deviceType: String,

    @SerializedName("status")
    val status: DeviceStatus = DeviceStatus.UNKNOWN,

    @SerializedName("capabilities")
    val capabilities: List<String> = emptyList(),

    @SerializedName("last_seen")
    val lastSeen: String? = null,

    @SerializedName("metadata")
    val metadata: Map<String, Any>? = null,

    @SerializedName("error_message")
    val errorMessage: String? = null
)

/**
 * RPi envelope: GET /devices returns {devices: [...], count, timestamp}.
 */
data class DeviceListResponse(
    @SerializedName("devices")
    val devices: List<DeviceDto>,

    @SerializedName("count")
    val count: Int,

    @SerializedName("timestamp")
    val timestamp: String
)

/**
 * RPi envelope: GET /devices/{id} returns {device: {...}, timestamp}.
 */
data class SingleDeviceResponse(
    @SerializedName("device")
    val device: DeviceDto,

    @SerializedName("timestamp")
    val timestamp: String
)

/**
 * Request to send a command to a device.
 * Sends device_id which RPi now accepts alongside device.
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

    @SerializedName("response")
    val response: Map<String, Any>? = null,

    @SerializedName("error")
    val error: String? = null,

    @SerializedName("timestamp")
    val timestamp: String? = null
)

/**
 * RPi envelope: GET /telemetry returns {telemetry: {...}, timestamp}.
 */
data class TelemetryResponse(
    @SerializedName("telemetry")
    val telemetry: Map<String, Any>,

    @SerializedName("timestamp")
    val timestamp: String
)

/**
 * System status — aligned with RPi's nested memory/cpu structure.
 */
data class MemoryInfo(
    @SerializedName("total")
    val total: Long,

    @SerializedName("available")
    val available: Long,

    @SerializedName("percent")
    val percent: Double,

    @SerializedName("used")
    val used: Long
)

data class CpuInfo(
    @SerializedName("percent")
    val percent: Double,

    @SerializedName("count")
    val count: Int
)

data class SystemStatus(
    @SerializedName("status")
    val status: String,

    @SerializedName("uptime_seconds")
    val uptimeSeconds: Long,

    @SerializedName("uptime_human")
    val uptimeHuman: String? = null,

    @SerializedName("memory")
    val memory: MemoryInfo? = null,

    @SerializedName("cpu")
    val cpu: CpuInfo? = null,

    @SerializedName("devices_connected")
    val devicesConnected: Int = 0,

    @SerializedName("timestamp")
    val timestamp: String? = null
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
 * WebSocket subscription message.
 */
data class WebSocketSubscription(
    @SerializedName("action")
    val action: String,

    @SerializedName("device_id")
    val deviceId: String? = null,

    @SerializedName("channels")
    val channels: List<String>? = null
)

/**
 * LED state information for WebSocket updates.
 */
data class LEDState(
    @SerializedName("mode")
    val mode: String,

    @SerializedName("ai_state")
    val aiState: String,

    @SerializedName("brightness")
    val brightness: Float,

    @SerializedName("service_status")
    val serviceStatus: String? = null,

    @SerializedName("emergency")
    val emergency: Boolean = false,

    @SerializedName("obd_data")
    val obdData: Map<String, Any>? = null,

    @SerializedName("timestamp")
    val timestamp: String
)

/**
 * General WebSocket message wrapper for different data types.
 */
data class WebSocketMessage(
    @SerializedName("type")
    val type: String? = null,

    @SerializedName("timestamp")
    val timestamp: String,

    @SerializedName("telemetry")
    val telemetry: Map<String, Any>? = null,

    @SerializedName("led_state")
    val ledState: LEDState? = null
)
