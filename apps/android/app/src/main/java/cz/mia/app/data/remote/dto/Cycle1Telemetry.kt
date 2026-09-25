package cz.mia.app.data.remote.dto

import com.google.gson.JsonElement
import com.google.gson.annotations.SerializedName

object Cycle1TelemetrySignals {
    const val IGNITION = "ignition"
    const val BATTERY_VOLTAGE = "battery_voltage"
    const val ENGINE_RPM = "engine_rpm"
    const val COOLANT_TEMP_C = "coolant_temp_c"
}

data class Cycle1TelemetrySignal(
    @SerializedName("value") val value: JsonElement,
    @SerializedName("unit") val unit: String,
    @SerializedName("source") val source: String,
    @SerializedName("confidence") val confidence: Double,
)

data class Cycle1TelemetryEnvelope(
    @SerializedName("schema_version") val schemaVersion: Int,
    @SerializedName("message_type") val messageType: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("timestamp") val timestamp: String,
    @SerializedName("source") val source: String,
    @SerializedName("confidence") val confidence: Double,
    @SerializedName("signals") val signals: Map<String, Cycle1TelemetrySignal>,
) {
    fun number(name: String): Double? {
        val value = signals[name]?.value ?: return null
        return if (value.isJsonPrimitive && value.asJsonPrimitive.isNumber) value.asDouble else null
    }

    fun boolean(name: String): Boolean? {
        val value = signals[name]?.value ?: return null
        return if (value.isJsonPrimitive && value.asJsonPrimitive.isBoolean) value.asBoolean else null
    }
}
