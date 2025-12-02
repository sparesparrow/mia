package cz.aiservis.app.data.remote.api

import cz.aiservis.app.data.remote.dto.CommandRequest
import cz.aiservis.app.data.remote.dto.CommandResponse
import cz.aiservis.app.data.remote.dto.DeviceDto
import cz.aiservis.app.data.remote.dto.PairDeviceRequest
import cz.aiservis.app.data.remote.dto.PairDeviceResponse
import cz.aiservis.app.data.remote.dto.SystemStatus
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit API interface for device management endpoints.
 */
interface DeviceApi {

    /**
     * Get all registered devices.
     */
    @GET("devices")
    suspend fun getDevices(
        @Query("status") status: String? = null,
        @Query("type") type: String? = null,
        @Query("page") page: Int? = null,
        @Query("page_size") pageSize: Int? = null
    ): Response<List<DeviceDto>>

    /**
     * Get a specific device by ID.
     */
    @GET("devices/{id}")
    suspend fun getDevice(
        @Path("id") deviceId: String
    ): Response<DeviceDto>

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
     * Pair/register a new device.
     */
    @POST("devices/{id}/pair")
    suspend fun pairDevice(
        @Path("id") deviceId: String,
        @Body request: PairDeviceRequest? = null
    ): Response<PairDeviceResponse>

    /**
     * Unpair/remove a device.
     */
    @DELETE("devices/{id}")
    suspend fun unpairDevice(
        @Path("id") deviceId: String
    ): Response<Unit>

    /**
     * Update device information.
     */
    @POST("devices/{id}")
    suspend fun updateDevice(
        @Path("id") deviceId: String,
        @Body device: DeviceDto
    ): Response<DeviceDto>

    /**
     * Get device capabilities.
     */
    @GET("devices/{id}/capabilities")
    suspend fun getDeviceCapabilities(
        @Path("id") deviceId: String
    ): Response<List<String>>

    /**
     * Ping/health check for a device.
     */
    @GET("devices/{id}/ping")
    suspend fun pingDevice(
        @Path("id") deviceId: String
    ): Response<CommandResponse>
}
