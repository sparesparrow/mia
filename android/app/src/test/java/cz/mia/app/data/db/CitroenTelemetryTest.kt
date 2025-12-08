package cz.mia.app.data.db

import org.junit.Assert.assertEquals
import org.junit.Test

class CitroenTelemetryTest {

    @Test
    fun `test TelemetryEntity with Citroen C4 fields`() {
        val entity = TelemetryEntity(
            id = 1,
            ts = 1640995200000L, // 2022-01-01 00:00:00 UTC
            fuelLevel = 75,
            engineRpm = 1800,
            vehicleSpeed = 60,
            coolantTemp = 85,
            engineLoad = 45,
            // Citroën C4 specific fields
            dpfSootMass = 23.4f,
            adBlueLevel = 85,
            dpfStatus = "ok",
            particulateFilterEfficiency = 92.5f,
            differentialPressure = 0.8f,
            eolysAdditiveLevel = 5.2f
        )

        assertEquals(1L, entity.id)
        assertEquals(1640995200000L, entity.ts)
        assertEquals(75, entity.fuelLevel)
        assertEquals(1800, entity.engineRpm)
        assertEquals(60, entity.vehicleSpeed)
        assertEquals(85, entity.coolantTemp)
        assertEquals(45, entity.engineLoad)

        // Citroën C4 assertions
        assertEquals(23.4f, entity.dpfSootMass)
        assertEquals(85, entity.adBlueLevel)
        assertEquals("ok", entity.dpfStatus)
        assertEquals(92.5f, entity.particulateFilterEfficiency)
        assertEquals(0.8f, entity.differentialPressure)
        assertEquals(5.2f, entity.eolysAdditiveLevel)
    }

    @Test
    fun `test TelemetryEntity with null Citroen fields`() {
        val entity = TelemetryEntity(
            id = 2,
            ts = 1640995200000L,
            fuelLevel = 50,
            engineRpm = 1200,
            vehicleSpeed = 30,
            coolantTemp = 75,
            engineLoad = 25
            // Citroën fields remain null
        )

        assertEquals(2L, entity.id)
        assertEquals(null, entity.dpfSootMass)
        assertEquals(null, entity.adBlueLevel)
        assertEquals(null, entity.dpfStatus)
        assertEquals(null, entity.particulateFilterEfficiency)
        assertEquals(null, entity.differentialPressure)
        assertEquals(null, entity.eolysAdditiveLevel)
    }

    @Test
    fun `test TelemetryEntity copy with Citroen fields`() {
        val original = TelemetryEntity(
            id = 1,
            ts = 1640995200000L,
            fuelLevel = 75,
            engineRpm = 1800,
            vehicleSpeed = 60,
            coolantTemp = 85,
            engineLoad = 45,
            dpfSootMass = 23.4f,
            adBlueLevel = 85,
            dpfStatus = "ok"
        )

        val updated = original.copy(
            dpfSootMass = 25.1f,
            adBlueLevel = 80,
            dpfStatus = "warning"
        )

        assertEquals(23.4f, original.dpfSootMass)
        assertEquals(85, original.adBlueLevel)
        assertEquals("ok", original.dpfStatus)

        assertEquals(25.1f, updated.dpfSootMass)
        assertEquals(80, updated.adBlueLevel)
        assertEquals("warning", updated.dpfStatus)

        // Ensure other fields remain the same
        assertEquals(original.id, updated.id)
        assertEquals(original.fuelLevel, updated.fuelLevel)
    }
}
