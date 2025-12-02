package cz.aiservis.app.core.background

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Standard OBD-II PIDs (Parameter IDs) for vehicle data.
 */
object OBDPIDs {
    // Mode 01 - Current Data
    const val ENGINE_LOAD = "0104"
    const val COOLANT_TEMP = "0105"
    const val FUEL_PRESSURE = "010A"
    const val ENGINE_RPM = "010C"
    const val VEHICLE_SPEED = "010D"
    const val TIMING_ADVANCE = "010E"
    const val INTAKE_TEMP = "010F"
    const val MAF_RATE = "0110"
    const val THROTTLE_POS = "0111"
    const val FUEL_LEVEL = "012F"
    const val BATTERY_VOLTAGE = "0142"
    
    // Mode 03 - Diagnostic Trouble Codes
    const val READ_DTC = "03"
    
    // Mode 04 - Clear DTCs
    const val CLEAR_DTC = "04"
}

/**
 * Connection status for OBD adapter.
 */
sealed class OBDConnectionStatus {
    object Disconnected : OBDConnectionStatus()
    object Connecting : OBDConnectionStatus()
    object Connected : OBDConnectionStatus()
    object Initializing : OBDConnectionStatus()
    object Ready : OBDConnectionStatus()
    data class Error(val message: String) : OBDConnectionStatus()
}

/**
 * OBD Manager interface for vehicle telemetry.
 */
interface OBDManager {
    /** Flow of OBD data updates */
    val obdData: Flow<OBDData>
    
    /** Current connection status */
    val connectionStatus: StateFlow<OBDConnectionStatus>
    
    /** List of detected DTCs */
    val dtcCodes: StateFlow<List<DTCInfo>>
    
    /** Start monitoring vehicle data */
    suspend fun startMonitoring()
    
    /** Stop monitoring */
    suspend fun stopMonitoring()
    
    /** Set sampling mode (affects polling frequency) */
    fun setSamplingMode(mode: SamplingMode)
    
    /** Read all DTCs from vehicle */
    suspend fun readDTCs(): List<DTCInfo>
    
    /** Clear all DTCs */
    suspend fun clearDTCs(): Boolean
    
    /** Check if monitoring is active */
    fun isMonitoring(): Boolean
}

/**
 * Diagnostic Trouble Code information.
 */
data class DTCInfo(
    val code: String,
    val type: DTCType,
    val description: String? = null
)

enum class DTCType {
    POWERTRAIN,  // P codes
    CHASSIS,     // C codes
    BODY,        // B codes
    NETWORK      // U codes
}

@Singleton
class OBDManagerImpl @Inject constructor(
    private val bleManager: BLEManager
) : OBDManager {

    companion object {
        private const val TAG = "OBDManager"
        
        private val POLLING_INTERVALS = mapOf(
            SamplingMode.NORMAL to 500L,
            SamplingMode.REDUCED to 2000L,
            SamplingMode.MINIMAL to 10000L
        )
        
        // DTCs to query per mode
        private val PIDS_NORMAL = listOf(
            OBDPIDs.ENGINE_RPM,
            OBDPIDs.VEHICLE_SPEED,
            OBDPIDs.COOLANT_TEMP,
            OBDPIDs.FUEL_LEVEL,
            OBDPIDs.ENGINE_LOAD
        )
        
        private val PIDS_REDUCED = listOf(
            OBDPIDs.ENGINE_RPM,
            OBDPIDs.VEHICLE_SPEED,
            OBDPIDs.FUEL_LEVEL
        )
        
        private val PIDS_MINIMAL = listOf(
            OBDPIDs.FUEL_LEVEL
        )
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    private val _obdData = MutableSharedFlow<OBDData>(replay = 1)
    override val obdData: Flow<OBDData> = _obdData.asSharedFlow()
    
    private val _connectionStatus = MutableStateFlow<OBDConnectionStatus>(OBDConnectionStatus.Disconnected)
    override val connectionStatus: StateFlow<OBDConnectionStatus> = _connectionStatus.asStateFlow()
    
    private val _dtcCodes = MutableStateFlow<List<DTCInfo>>(emptyList())
    override val dtcCodes: StateFlow<List<DTCInfo>> = _dtcCodes.asStateFlow()
    
    private var monitoringJob: Job? = null
    
    @Volatile
    private var samplingMode: SamplingMode = SamplingMode.NORMAL
    
    // Current data values
    private var currentFuelLevel: Int = 0
    private var currentRpm: Int = 0
    private var currentSpeed: Int = 0
    private var currentCoolantTemp: Int = 0
    private var currentEngineLoad: Int = 0
    private var currentDtcCodes: List<String> = emptyList()

    override suspend fun startMonitoring() = withContext(Dispatchers.IO) {
        if (monitoringJob?.isActive == true) {
            Log.d(TAG, "Monitoring already active")
            return@withContext
        }
        
        _connectionStatus.value = OBDConnectionStatus.Connecting
        
        // Check BLE connection
        if (!bleManager.isConnected()) {
            _connectionStatus.value = OBDConnectionStatus.Error("BLE not connected")
            return@withContext
        }
        
        _connectionStatus.value = OBDConnectionStatus.Initializing
        
        // Initialize OBD adapter
        if (!initializeOBDAdapter()) {
            _connectionStatus.value = OBDConnectionStatus.Error("Failed to initialize OBD adapter")
            return@withContext
        }
        
        _connectionStatus.value = OBDConnectionStatus.Ready
        
        monitoringJob = scope.launch {
            while (isActive) {
                try {
                    val data = pollOBDData()
                    _obdData.emit(data)
                } catch (e: Exception) {
                    Log.e(TAG, "Error polling OBD data", e)
                }
                
                delay(POLLING_INTERVALS[samplingMode] ?: 1000L)
            }
        }
        
        Log.d(TAG, "OBD monitoring started with mode: $samplingMode")
    }

    override suspend fun stopMonitoring() {
        monitoringJob?.cancel()
        monitoringJob = null
        _connectionStatus.value = OBDConnectionStatus.Disconnected
        Log.d(TAG, "OBD monitoring stopped")
    }

    override fun setSamplingMode(mode: SamplingMode) {
        samplingMode = mode
        Log.d(TAG, "Sampling mode changed to: $mode")
    }
    
    override fun isMonitoring(): Boolean = monitoringJob?.isActive == true

    private suspend fun initializeOBDAdapter(): Boolean {
        try {
            // Reset adapter
            var response = bleManager.sendCommand("ATZ")
            Log.d(TAG, "ATZ response: $response")
            delay(1000)
            
            // Turn off echo
            response = bleManager.sendCommand("ATE0")
            Log.d(TAG, "ATE0 response: $response")
            
            // Turn off line feeds
            response = bleManager.sendCommand("ATL0")
            Log.d(TAG, "ATL0 response: $response")
            
            // Turn off spaces
            response = bleManager.sendCommand("ATS0")
            Log.d(TAG, "ATS0 response: $response")
            
            // Auto protocol detection
            response = bleManager.sendCommand("ATSP0")
            Log.d(TAG, "ATSP0 response: $response")
            
            // Set timeout
            response = bleManager.sendCommand("ATST32")
            Log.d(TAG, "ATST32 response: $response")
            
            return true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize OBD adapter", e)
            return false
        }
    }

    private suspend fun pollOBDData(): OBDData {
        val pids = when (samplingMode) {
            SamplingMode.NORMAL -> PIDS_NORMAL
            SamplingMode.REDUCED -> PIDS_REDUCED
            SamplingMode.MINIMAL -> PIDS_MINIMAL
        }
        
        for (pid in pids) {
            try {
                val response = bleManager.sendCommand(pid)
                if (response != null && !response.contains("NO DATA") && !response.contains("ERROR")) {
                    parseOBDResponse(pid, response)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error querying PID: $pid", e)
            }
            delay(50) // Small delay between commands
        }
        
        return OBDData(
            fuelLevel = currentFuelLevel,
            engineRpm = currentRpm,
            vehicleSpeed = currentSpeed,
            coolantTemp = currentCoolantTemp,
            engineLoad = currentEngineLoad,
            dtcCodes = currentDtcCodes
        )
    }

    private fun parseOBDResponse(pid: String, response: String) {
        try {
            // Remove spaces and clean response
            val cleanResponse = response.replace(" ", "").uppercase()
            
            // Expected format: 41 XX YY (where XX is PID, YY is value)
            // Mode 01 responses start with 41
            when (pid) {
                OBDPIDs.FUEL_LEVEL -> {
                    // 41 2F XX - Fuel level (0-100%)
                    val value = extractValue(cleanResponse, "412F", 1)
                    currentFuelLevel = (value * 100 / 255).coerceIn(0, 100)
                }
                
                OBDPIDs.ENGINE_RPM -> {
                    // 41 0C XX YY - RPM = ((A*256)+B)/4
                    val values = extractValues(cleanResponse, "410C", 2)
                    if (values.size >= 2) {
                        currentRpm = ((values[0] * 256 + values[1]) / 4).coerceAtLeast(0)
                    }
                }
                
                OBDPIDs.VEHICLE_SPEED -> {
                    // 41 0D XX - Speed in km/h
                    val value = extractValue(cleanResponse, "410D", 1)
                    currentSpeed = value.coerceIn(0, 255)
                }
                
                OBDPIDs.COOLANT_TEMP -> {
                    // 41 05 XX - Coolant temp (°C) = A - 40
                    val value = extractValue(cleanResponse, "4105", 1)
                    currentCoolantTemp = (value - 40).coerceIn(-40, 215)
                }
                
                OBDPIDs.ENGINE_LOAD -> {
                    // 41 04 XX - Engine load (0-100%)
                    val value = extractValue(cleanResponse, "4104", 1)
                    currentEngineLoad = (value * 100 / 255).coerceIn(0, 100)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing response for PID $pid: $response", e)
        }
    }

    private fun extractValue(response: String, prefix: String, bytes: Int): Int {
        val index = response.indexOf(prefix)
        if (index == -1 || index + prefix.length + bytes * 2 > response.length) {
            return 0
        }
        val valueHex = response.substring(index + prefix.length, index + prefix.length + bytes * 2)
        return valueHex.toIntOrNull(16) ?: 0
    }

    private fun extractValues(response: String, prefix: String, bytes: Int): List<Int> {
        val index = response.indexOf(prefix)
        if (index == -1 || index + prefix.length + bytes * 2 > response.length) {
            return emptyList()
        }
        val values = mutableListOf<Int>()
        for (i in 0 until bytes) {
            val startPos = index + prefix.length + i * 2
            val valueHex = response.substring(startPos, startPos + 2)
            values.add(valueHex.toIntOrNull(16) ?: 0)
        }
        return values
    }

    override suspend fun readDTCs(): List<DTCInfo> = withContext(Dispatchers.IO) {
        val dtcList = mutableListOf<DTCInfo>()
        
        try {
            val response = bleManager.sendCommand(OBDPIDs.READ_DTC)
            if (response != null && !response.contains("NO DATA")) {
                dtcList.addAll(parseDTCResponse(response))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error reading DTCs", e)
        }
        
        _dtcCodes.value = dtcList
        currentDtcCodes = dtcList.map { it.code }
        
        return@withContext dtcList
    }

    private fun parseDTCResponse(response: String): List<DTCInfo> {
        val dtcs = mutableListOf<DTCInfo>()
        val cleanResponse = response.replace(" ", "").uppercase()
        
        // Mode 03 response: 43 XX YY ZZ WW ...
        // Each DTC is 2 bytes (4 hex chars)
        val index = cleanResponse.indexOf("43")
        if (index == -1) return dtcs
        
        var i = index + 2
        while (i + 4 <= cleanResponse.length) {
            val dtcHex = cleanResponse.substring(i, i + 4)
            if (dtcHex != "0000") {
                val dtc = decodeDTC(dtcHex)
                if (dtc != null) {
                    dtcs.add(dtc)
                }
            }
            i += 4
        }
        
        return dtcs
    }

    private fun decodeDTC(hex: String): DTCInfo? {
        if (hex.length != 4) return null
        
        val firstChar = hex[0].digitToIntOrNull(16) ?: return null
        
        // First 2 bits determine the type
        val type = when (firstChar shr 2) {
            0 -> DTCType.POWERTRAIN  // P
            1 -> DTCType.CHASSIS     // C
            2 -> DTCType.BODY        // B
            3 -> DTCType.NETWORK     // U
            else -> DTCType.POWERTRAIN
        }
        
        val typeChar = when (type) {
            DTCType.POWERTRAIN -> 'P'
            DTCType.CHASSIS -> 'C'
            DTCType.BODY -> 'B'
            DTCType.NETWORK -> 'U'
        }
        
        // Remaining bits form the code
        val secondDigit = firstChar and 0x03
        val code = "$typeChar$secondDigit${hex.substring(1)}"
        
        return DTCInfo(
            code = code,
            type = type,
            description = getDTCDescription(code)
        )
    }

    private fun getDTCDescription(code: String): String? {
        // Common DTC descriptions
        return when (code) {
            "P0300" -> "Random/Multiple Cylinder Misfire Detected"
            "P0171" -> "System Too Lean (Bank 1)"
            "P0174" -> "System Too Lean (Bank 2)"
            "P0420" -> "Catalyst System Efficiency Below Threshold"
            "P0442" -> "Evaporative Emission Control System Leak Detected (small)"
            "P0455" -> "Evaporative Emission Control System Leak Detected (large)"
            "P0128" -> "Coolant Thermostat Below Thermostat Regulating Temperature"
            "P0401" -> "Exhaust Gas Recirculation Flow Insufficient"
            else -> null
        }
    }

    override suspend fun clearDTCs(): Boolean = withContext(Dispatchers.IO) {
        try {
            val response = bleManager.sendCommand(OBDPIDs.CLEAR_DTC)
            val success = response != null && !response.contains("ERROR")
            
            if (success) {
                _dtcCodes.value = emptyList()
                currentDtcCodes = emptyList()
            }
            
            return@withContext success
        } catch (e: Exception) {
            Log.e(TAG, "Error clearing DTCs", e)
            return@withContext false
        }
    }
}
