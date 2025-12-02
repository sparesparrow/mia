package cz.aiservis.app.data.remote.api

import cz.aiservis.app.data.remote.dto.TelemetryBatch
import cz.aiservis.app.data.remote.dto.TelemetryReading
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Retrofit API interface for telemetry data endpoints.
 */
interface TelemetryApi {

    /**
     * Get latest telemetry readings.
     * 
     * @param deviceId Filter by device ID
     * @param sensor Filter by sensor type (e.g., "temperature", "speed", "rpm")
     * @param limit Maximum number of readings to return
     */
    @GET("telemetry")
    suspend fun getLatestTelemetry(
        @Query("device_id") deviceId: String? = null,
        @Query("sensor") sensor: String? = null,
        @Query("limit") limit: Int? = null
    ): Response<List<TelemetryReading>>

    /**
     * Get historical telemetry data.
     * 
     * @param deviceId Filter by device ID
     * @param sensor Filter by sensor type
     * @param start Start timestamp (ISO 8601 format)
     * @param end End timestamp (ISO 8601 format)
     * @param interval Aggregation interval (e.g., "1m", "5m", "1h")
     */
    @GET("telemetry/history")
    suspend fun getTelemetryHistory(
        @Query("device_id") deviceId: String? = null,
        @Query("sensor") sensor: String? = null,
        @Query("start") start: String? = null,
        @Query("end") end: String? = null,
        @Query("interval") interval: String? = null
    ): Response<List<TelemetryReading>>

    /**
     * Upload a batch of telemetry readings.
     * 
     * @param batch The batch of telemetry readings to upload
     */
    @POST("telemetry")
    suspend fun uploadTelemetry(
        @Body batch: TelemetryBatch
    ): Response<Unit>

    /**
     * Get available sensors for a device.
     * 
     * @param deviceId The device ID to query sensors for
     */
    @GET("telemetry/sensors")
    suspend fun getAvailableSensors(
        @Query("device_id") deviceId: String
    ): Response<List<String>>

    /**
     * Get aggregated telemetry statistics.
     * 
     * @param deviceId Filter by device ID
     * @param sensor Filter by sensor type
     * @param period Aggregation period (e.g., "day", "week", "month")
     */
    @GET("telemetry/stats")
    suspend fun getTelemetryStats(
        @Query("device_id") deviceId: String? = null,
        @Query("sensor") sensor: String? = null,
        @Query("period") period: String? = null
    ): Response<Map<String, Any>>
}
