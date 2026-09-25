package cz.mia.app.data.remote

import com.google.gson.Gson
import cz.mia.app.data.remote.dto.Cycle1TelemetryEnvelope
import cz.mia.app.data.remote.dto.Cycle1TelemetrySignals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Cycle1TelemetryTest {
    private val gson = Gson()

    @Test
    fun parsesCanonicalCycle1Envelope() {
        val json = """
            {
              "schema_version": 1,
              "message_type": "vehicle.telemetry",
              "device_id": "cycle1-test",
              "timestamp": "2026-09-24T21:00:00Z",
              "source": "replay.can",
              "confidence": 1.0,
              "signals": {
                "ignition": {"value": true, "unit": "bool", "source": "replay:bench:kl15-frame", "confidence": 1.0},
                "battery_voltage": {"value": 13.8, "unit": "V", "source": "can:0x7E8/0x42", "confidence": 1.0},
                "engine_rpm": {"value": 1750, "unit": "rpm", "source": "can:0x7E8/0x0C", "confidence": 1.0},
                "coolant_temp_c": {"value": 86, "unit": "°C", "source": "can:0x7E8/0x05", "confidence": 1.0}
              }
            }
        """.trimIndent()
        val envelope = gson.fromJson(json, Cycle1TelemetryEnvelope::class.java)
        assertEquals(1, envelope.schemaVersion)
        assertEquals(true, envelope.boolean(Cycle1TelemetrySignals.IGNITION))
        assertEquals(13.8, envelope.number(Cycle1TelemetrySignals.BATTERY_VOLTAGE) ?: 0.0, 0.0001)
        assertEquals(1750.0, envelope.number(Cycle1TelemetrySignals.ENGINE_RPM) ?: 0.0, 0.0001)
        assertEquals(86.0, envelope.number(Cycle1TelemetrySignals.COOLANT_TEMP_C) ?: 0.0, 0.0001)
        assertTrue(envelope.confidence > 0.99)
    }
}
