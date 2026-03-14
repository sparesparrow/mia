package cz.mia.app.data.remote.api

import cz.mia.app.data.remote.dto.CommandRequest
import cz.mia.app.data.remote.dto.CommandResponse
import cz.mia.app.data.remote.dto.DeviceListResponse
import cz.mia.app.data.remote.dto.SingleDeviceResponse
import cz.mia.app.data.remote.dto.SystemStatus
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit API interface for device management endpoints.
 * Aligned with RPi FastAPI response shapes.
 */
interface DeviceApi {

    /**
     * Get all registered devices.
     * RPi returns {devices: [...], count, timestamp}.
     */
    @GET("devices")
    suspend fun getDevices(
        @Query("status") status: String? = null,
        @Query("type") type: String? = null
    ): Response<DeviceListResponse>

    /**
     * Get a specific device by ID.
     * RPi returns {device: {...}, timestamp}.
     */
    @GET("devices/{device_id}")
    suspend fun getDevice(
        @Path("device_id") deviceId: String
    ): Response<SingleDeviceResponse>

    /**
     * Send a command to a device.
     */
    @POST("command")
    suspend fun sendCommand(
        @Body request: CommandRequest
    ): Response<CommandResponse>

    /**
     * Get system status and health information.
     */
    @GET("status")
    suspend fun getSystemStatus(): Response<SystemStatus>

    /**
     * Remove a device.
     */
    @DELETE("devices/{device_id}")
    suspend fun removeDevice(
        @Path("device_id") deviceId: String
    ): Response<Map<String, Any>>

    /**
     * Send device heartbeat.
     */
    @POST("devices/{device_id}/heartbeat")
    suspend fun heartbeat(
        @Path("device_id") deviceId: String
    ): Response<Map<String, Any>>
}
