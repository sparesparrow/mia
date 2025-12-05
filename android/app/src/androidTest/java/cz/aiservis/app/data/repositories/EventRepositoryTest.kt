package cz.aiservis.app.data.repositories

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.google.gson.Gson
import cz.aiservis.app.core.background.ANPREvent
import cz.aiservis.app.core.background.AlertSeverity
import cz.aiservis.app.core.background.OBDData
import cz.aiservis.app.core.background.VehicleAlert
import cz.aiservis.app.data.db.AlertDao
import cz.aiservis.app.data.db.AnprEventDao
import cz.aiservis.app.data.db.AppDatabase
import cz.aiservis.app.data.db.ClipsDao
import cz.aiservis.app.data.db.TelemetryDao
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Integration tests for EventRepository.
 */
@RunWith(AndroidJUnit4::class)
class EventRepositoryTest {

    private lateinit var db: AppDatabase
    private lateinit var telemetryDao: TelemetryDao
    private lateinit var alertDao: AlertDao
    private lateinit var anprEventDao: AnprEventDao
    private lateinit var clipsDao: ClipsDao
    private lateinit var repository: EventRepositoryImpl

    @Before
    fun setup() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(context, AppDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        
        telemetryDao = db.telemetry()
        alertDao = db.alerts()
        anprEventDao = db.anpr()
        clipsDao = db.clips()
        
        repository = EventRepositoryImpl(telemetryDao, alertDao, anprEventDao, clipsDao, Gson())
    }

    @After
    fun tearDown() {
        db.close()
    }

    @Test
    fun recordTelemetry_persistsData() = runBlocking {
        val obdData = OBDData(
            fuelLevel = 85,
            engineRpm = 2800,
            vehicleSpeed = 65,
            coolantTemp = 88,
            engineLoad = 52,
            dtcCodes = listOf("P0420", "P0171")
        )
        
        repository.recordTelemetry(obdData)
        
        val results = telemetryDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals(85, results[0].fuelLevel)
        assertEquals(2800, results[0].engineRpm)
        assertEquals(65, results[0].vehicleSpeed)
        assertEquals(88, results[0].coolantTemp)
        assertEquals(52, results[0].engineLoad)
    }

    @Test
    fun recordTelemetry_multipleRecords() = runBlocking {
        repeat(5) { i ->
            val obdData = OBDData(
                fuelLevel = 80 - i,
                engineRpm = 2000 + i * 100,
                vehicleSpeed = 50 + i * 5,
                coolantTemp = 85,
                engineLoad = 40 + i,
                dtcCodes = emptyList()
            )
            repository.recordTelemetry(obdData)
        }
        
        val results = telemetryDao.snapshotRecent(10)
        assertEquals(5, results.size)
    }

    @Test
    fun recordAlert_persistsWithTimestamp() = runBlocking {
        val alert = VehicleAlert(
            severity = AlertSeverity.WARNING,
            code = "P0420",
            message = "Catalyst system efficiency below threshold"
        )
        
        val beforeTime = System.currentTimeMillis()
        repository.recordAlert(alert)
        val afterTime = System.currentTimeMillis()
        
        val results = alertDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals("WARNING", results[0].severity)
        assertEquals("P0420", results[0].code)
        assertEquals("Catalyst system efficiency below threshold", results[0].message)
        
        // Verify timestamp is within expected range
        assertTrue(results[0].ts >= beforeTime)
        assertTrue(results[0].ts <= afterTime)
    }

    @Test
    fun recordAlert_differentSeverities() = runBlocking {
        val alerts = listOf(
            VehicleAlert(severity = AlertSeverity.LOW, code = "INFO01", message = "Info message"),
            VehicleAlert(severity = AlertSeverity.WARNING, code = "WARN01", message = "Warning message"),
            VehicleAlert(severity = AlertSeverity.ERROR, code = "ERR01", message = "Error message"),
            VehicleAlert(severity = AlertSeverity.CRITICAL, code = "CRIT01", message = "Critical message")
        )
        
        alerts.forEach { repository.recordAlert(it) }
        
        val results = alertDao.snapshotRecent(10)
        
        assertEquals(4, results.size)
        assertTrue(results.any { it.severity == "LOW" })
        assertTrue(results.any { it.severity == "WARNING" })
        assertTrue(results.any { it.severity == "ERROR" })
        assertTrue(results.any { it.severity == "CRITICAL" })
    }

    @Test
    fun recordAnpr_persistsEvent() = runBlocking {
        val event = ANPREvent(
            plateHash = "hashed-plate-123",
            confidence = 0.92f,
            snapshotId = "snapshot-uuid-456",
            region = "CZ"
        )
        
        repository.recordAnpr(event)
        
        val results = anprEventDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals("hashed-plate-123", results[0].plateHash)
        assertEquals(0.92f, results[0].confidence)
        assertEquals("snapshot-uuid-456", results[0].snapshotId)
    }

    @Test
    fun recordAnpr_nullSnapshotId() = runBlocking {
        val event = ANPREvent(
            plateHash = "hashed-plate-789",
            confidence = 0.75f,
            snapshotId = null,
            region = "EU"
        )
        
        repository.recordAnpr(event)
        
        val results = anprEventDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals(null, results[0].snapshotId)
    }

    @Test
    fun recordAnpr_multipleEvents() = runBlocking {
        repeat(10) { i ->
            val event = ANPREvent(
                plateHash = "plate-hash-$i",
                confidence = 0.7f + i * 0.02f,
                snapshotId = "snapshot-$i",
                region = if (i % 2 == 0) "CZ" else "EU"
            )
            repository.recordAnpr(event)
        }
        
        val results = anprEventDao.snapshotRecent(20)
        assertEquals(10, results.size)
    }

    @Test
    fun mixedOperations_allPersistCorrectly() = runBlocking {
        // Record telemetry
        repository.recordTelemetry(OBDData(
            fuelLevel = 90,
            engineRpm = 3500,
            vehicleSpeed = 80,
            coolantTemp = 92,
            engineLoad = 60,
            dtcCodes = listOf("P0300")
        ))
        
        // Record alert
        repository.recordAlert(VehicleAlert(
            severity = AlertSeverity.ERROR,
            code = "P0300",
            message = "Random misfire detected"
        ))
        
        // Record ANPR
        repository.recordAnpr(ANPREvent(
            plateHash = "test-hash",
            confidence = 0.88f,
            snapshotId = "test-snapshot",
            region = "CZ"
        ))
        
        // Verify all records
        assertEquals(1, telemetryDao.snapshotRecent(10).size)
        assertEquals(1, alertDao.snapshotRecent(10).size)
        assertEquals(1, anprEventDao.snapshotRecent(10).size)
    }
}
