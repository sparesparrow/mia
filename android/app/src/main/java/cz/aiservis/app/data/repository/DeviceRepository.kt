package cz.aiservis.app.data.repository

import cz.aiservis.app.data.remote.api.DeviceApi
import cz.aiservis.app.data.remote.dto.CommandRequest
import cz.aiservis.app.data.remote.dto.CommandResponse
import cz.aiservis.app.data.remote.dto.DeviceDto
import cz.aiservis.app.data.remote.dto.PairDeviceRequest
import cz.aiservis.app.data.remote.dto.PairDeviceResponse
import cz.aiservis.app.data.remote.dto.SystemStatus
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Result wrapper for repository operations.
 */
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String, val exception: Throwable? = null) : Result<Nothing>()
    object Loading : Result<Nothing>()
    
    val isSuccess: Boolean get() = this is Success
    val isError: Boolean get() = this is Error
    val isLoading: Boolean get() = this is Loading
    
    fun getOrNull(): T? = (this as? Success)?.data
    fun getOrThrow(): T = (this as Success).data
    
    fun <R> map(transform: (T) -> R): Result<R> = when (this) {
        is Success -> Success(transform(data))
        is Error -> Error(message, exception)
        is Loading -> Loading
    }
}

/**
 * Repository for device-related operations.
 * Provides a clean API layer between the ViewModel and the remote data source.
 */
@Singleton
class DeviceRepository @Inject constructor(
    private val deviceApi: DeviceApi
) {
    
    /**
     * Get all registered devices.
     */
    suspend fun getDevices(
        status: String? = null,
        type: String? = null
    ): Result<List<DeviceDto>> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.getDevices(status = status, type = type)
            if (response.isSuccessful) {
                Result.Success(response.body() ?: emptyList())
            } else {
                Result.Error("Failed to fetch devices: ${response.code()} ${response.message()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    /**
     * Get a specific device by ID.
     */
    suspend fun getDevice(deviceId: String): Result<DeviceDto> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.getDevice(deviceId)
            if (response.isSuccessful) {
                response.body()?.let {
                    Result.Success(it)
                } ?: Result.Error("Device not found")
            } else {
                Result.Error("Failed to fetch device: ${response.code()} ${response.message()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    /**
     * Send a command to a device.
     */
    suspend fun sendCommand(
        deviceId: String,
        action: String,
        params: Map<String, Any>? = null
    ): Result<CommandResponse> = withContext(Dispatchers.IO) {
        try {
            val request = CommandRequest(
                deviceId = deviceId,
                action = action,
                params = params
            )
            val response = deviceApi.sendCommand(request)
            if (response.isSuccessful) {
                response.body()?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Command failed: ${response.code()} ${response.message()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    /**
     * Get system status.
     */
    suspend fun getSystemStatus(): Result<SystemStatus> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.getSystemStatus()
            if (response.isSuccessful) {
                response.body()?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Failed to fetch status: ${response.code()} ${response.message()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    /**
     * Pair a new device.
     */
    suspend fun pairDevice(
        deviceId: String,
        deviceName: String? = null,
        deviceType: String? = null
    ): Result<PairDeviceResponse> = withContext(Dispatchers.IO) {
        try {
            val request = PairDeviceRequest(
                deviceId = deviceId,
                deviceName = deviceName,
                deviceType = deviceType
            )
            val response = deviceApi.pairDevice(deviceId, request)
            if (response.isSuccessful) {
                response.body()?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Pairing failed: ${response.code()} ${response.message()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    /**
     * Unpair/remove a device.
     */
    suspend fun unpairDevice(deviceId: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.unpairDevice(deviceId)
            if (response.isSuccessful) {
                Result.Success(Unit)
            } else {
                Result.Error("Unpairing failed: ${response.code()} ${response.message()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    /**
     * Update device information.
     */
    suspend fun updateDevice(device: DeviceDto): Result<DeviceDto> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.updateDevice(device.id, device)
            if (response.isSuccessful) {
                response.body()?.let {
                    Result.Success(it)
                } ?: Result.Error("Empty response")
            } else {
                Result.Error("Update failed: ${response.code()} ${response.message()}")
            }
        } catch (e: Exception) {
            Result.Error("Network error: ${e.message}", e)
        }
    }
    
    /**
     * Ping a device to check if it's responsive.
     */
    suspend fun pingDevice(deviceId: String): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = deviceApi.pingDevice(deviceId)
            if (response.isSuccessful) {
                Result.Success(response.body()?.success == true)
            } else {
                Result.Success(false)
            }
        } catch (e: Exception) {
            Result.Success(false)
        }
    }
}
