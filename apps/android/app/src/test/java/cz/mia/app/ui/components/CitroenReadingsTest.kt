package cz.mia.app.ui.components

// @req REQ-AND-003

import cz.mia.app.data.db.TelemetryEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CitroenReadingsTest {

    private fun telemetry(
        dpfSootMass: Float? = null,
        adBlueLevel: Int? = null,
        dpfStatus: String? = null,
        particulateFilterEfficiency: Float? = null,
    ) = TelemetryEntity(
        id = 1,
        ts = 1640995200000L,
        fuelLevel = 75,
        engineRpm = 1800,
        vehicleSpeed = 60,
        coolantTemp = 85,
        engineLoad = 45,
        dpfSootMass = dpfSootMass,
        adBlueLevel = adBlueLevel,
        dpfStatus = dpfStatus,
        particulateFilterEfficiency = particulateFilterEfficiency,
    )

    @Test
    fun `no telemetry shows nothing`() {
        assertTrue(citroenReadingRows(null).isEmpty())
    }

    @Test
    fun `telemetry without Citroen fields shows nothing`() {
        assertTrue(citroenReadingRows(telemetry()).isEmpty())
    }

    @Test
    fun `every Citroen field the Pi sends gets a row with its unit`() {
        val rows = citroenReadingRows(
            telemetry(dpfSootMass = 23.4f, adBlueLevel = 85, dpfStatus = "ok", particulateFilterEfficiency = 92.5f)
        )

        assertEquals(
            listOf(
                "DPF soot" to "23.4g",
                "DPF status" to "ok",
                "Filter efficiency" to "92.5%",
                "AdBlue level" to "85%",
            ),
            rows,
        )
    }

    @Test
    fun `a missing field is left out instead of shown as zero`() {
        val rows = citroenReadingRows(telemetry(adBlueLevel = 40))

        assertEquals(listOf("AdBlue level" to "40%"), rows)
    }

    @Test
    fun `the readings carry no action label, because the app never actuates the car`() {
        val rows = citroenReadingRows(
            telemetry(dpfSootMass = 23.4f, adBlueLevel = 85, dpfStatus = "warning", particulateFilterEfficiency = 92.5f)
        )

        val text = rows.joinToString(" ") { (label, value) -> "$label $value" }.lowercase()
        assertTrue("regenerat" !in text)
    }
}
