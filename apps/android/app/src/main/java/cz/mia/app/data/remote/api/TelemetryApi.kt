package cz.mia.app.data.remote.api

import cz.mia.app.data.remote.dto.TelemetryResponse
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Query

/**
 * Retrofit API interface for telemetry data endpoints.
 * Aligned with RPi FastAPI response shapes.
 */
interface TelemetryApi {

    /**
     * Get latest telemetry readings.
     * RPi returns {telemetry: {...}, timestamp}.
     */
    @GET("telemetry")
    suspend fun getLatestTelemetry(
        @Query("device_id") deviceId: String? = null,
        @Query("sensor") sensor: String? = null
    ): Response<TelemetryResponse>
}
