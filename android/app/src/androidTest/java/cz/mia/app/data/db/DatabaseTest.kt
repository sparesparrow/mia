package cz.mia.app.data.db

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Integration tests for Room database operations.
 */
@RunWith(AndroidJUnit4::class)
class DatabaseTest {

    private lateinit var db: AppDatabase
    private lateinit var telemetryDao: TelemetryDao
    private lateinit var alertDao: AlertDao
    private lateinit var anprEventDao: AnprEventDao
    private lateinit var clipsDao: ClipsDao
    private lateinit var auditDao: AuditDao

    @Before
    fun createDb() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(context, AppDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        
        telemetryDao = db.telemetryDao()
        alertDao = db.alertDao()
        anprEventDao = db.anprEventDao()
        clipsDao = db.clipsDao()
        auditDao = db.auditDao()
    }

    @After
    fun closeDb() {
        db.close()
    }

    @Test
    fun insertTelemetry_canQuery() = runBlocking {
        val telemetry = TelemetryEntity(
            ts = System.currentTimeMillis(),
            fuelLevel = 75,
            engineRpm = 2500,
            vehicleSpeed = 60,
            coolantTemp = 85,
            engineLoad = 45
        )
        
        telemetryDao.insert(telemetry)
        
        val results = telemetryDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals(75, results[0].fuelLevel)
        assertEquals(2500, results[0].engineRpm)
        assertEquals(60, results[0].vehicleSpeed)
    }

    @Test
    fun insertMultipleTelemetry_orderedByTimestamp() = runBlocking {
        val now = System.currentTimeMillis()
        
        telemetryDao.insert(TelemetryEntity(ts = now - 2000, fuelLevel = 70, engineRpm = 2000, vehicleSpeed = 50, coolantTemp = 80, engineLoad = 40))
        telemetryDao.insert(TelemetryEntity(ts = now - 1000, fuelLevel = 71, engineRpm = 2100, vehicleSpeed = 55, coolantTemp = 82, engineLoad = 42))
        telemetryDao.insert(TelemetryEntity(ts = now, fuelLevel = 72, engineRpm = 2200, vehicleSpeed = 60, coolantTemp = 84, engineLoad = 44))
        
        val results = telemetryDao.snapshotRecent(10)
        
        assertEquals(3, results.size)
        // Most recent first
        assertEquals(72, results[0].fuelLevel)
        assertEquals(71, results[1].fuelLevel)
        assertEquals(70, results[2].fuelLevel)
    }

    @Test
    fun retention_deletesOldRecords() = runBlocking {
        val now = System.currentTimeMillis()
        val twoDaysAgo = now - TimeUnit.DAYS.toMillis(2)
        val threeDaysAgo = now - TimeUnit.DAYS.toMillis(3)
        
        telemetryDao.insert(TelemetryEntity(ts = threeDaysAgo, fuelLevel = 60, engineRpm = 1000, vehicleSpeed = 30, coolantTemp = 70, engineLoad = 30))
        telemetryDao.insert(TelemetryEntity(ts = twoDaysAgo, fuelLevel = 65, engineRpm = 1500, vehicleSpeed = 40, coolantTemp = 75, engineLoad = 35))
        telemetryDao.insert(TelemetryEntity(ts = now, fuelLevel = 70, engineRpm = 2000, vehicleSpeed = 50, coolantTemp = 80, engineLoad = 40))
        
        // Delete records older than 2.5 days
        val threshold = now - TimeUnit.HOURS.toMillis(60) // 2.5 days
        val deleted = telemetryDao.deleteOlderThan(threshold)
        
        assertEquals(1, deleted) // Only the 3-day-old record
        
        val remaining = telemetryDao.snapshotRecent(10)
        assertEquals(2, remaining.size)
    }

    @Test
    fun insertAlert_canQuery() = runBlocking {
        val alert = AlertEntity(
            ts = System.currentTimeMillis(),
            severity = "WARNING",
            code = "P0420",
            message = "Catalyst efficiency below threshold"
        )
        
        alertDao.insert(alert)
        
        val results = alertDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals("WARNING", results[0].severity)
        assertEquals("P0420", results[0].code)
    }

    @Test
    fun insertAnprEvent_canQuery() = runBlocking {
        val event = AnprEventEntity(
            ts = System.currentTimeMillis(),
            plateHash = "abc123hash",
            confidence = 0.85f,
            snapshotId = "snapshot-uuid"
        )
        
        anprEventDao.insert(event)
        
        val results = anprEventDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals("abc123hash", results[0].plateHash)
        assertEquals(0.85f, results[0].confidence)
    }

    @Test
    fun insertClip_canQueryAndMarkOffloaded() = runBlocking {
        val clip = ClipEntity(
            ts = System.currentTimeMillis(),
            reason = "manual_trigger",
            filePath = "/data/clips/test.mp4",
            durationMs = 30000,
            sizeBytes = 15000000,
            offloaded = false
        )
        
        clipsDao.insert(clip)
        
        var results = clipsDao.snapshotRecent(10)
        assertEquals(1, results.size)
        assertEquals(false, results[0].offloaded)
        
        // Mark as offloaded
        clipsDao.markOffloaded(results[0].id)
        
        results = clipsDao.snapshotRecent(10)
        assertEquals(true, results[0].offloaded)
    }

    @Test
    fun insertAuditEvent_canQuery() = runBlocking {
        val audit = AuditEventEntity(
            ts = System.currentTimeMillis(),
            category = "SERVICE",
            action = "START",
            details = "Driving service started"
        )
        
        auditDao.insert(audit)
        
        val results = auditDao.snapshotRecent(10)
        
        assertEquals(1, results.size)
        assertEquals("SERVICE", results[0].category)
        assertEquals("START", results[0].action)
    }

    @Test
    fun flowUpdates_emitNewData() = runBlocking {
        val flow = telemetryDao.recent(10)
        
        // Initial state
        var results = flow.first()
        assertEquals(0, results.size)
        
        // Insert data
        telemetryDao.insert(TelemetryEntity(
            ts = System.currentTimeMillis(),
            fuelLevel = 80,
            engineRpm = 3000,
            vehicleSpeed = 70,
            coolantTemp = 90,
            engineLoad = 50
        ))
        
        // Flow should update
        results = flow.first()
        assertEquals(1, results.size)
    }

    @Test
    fun limitQuery_respectsLimit() = runBlocking {
        repeat(20) { i ->
            telemetryDao.insert(TelemetryEntity(
                ts = System.currentTimeMillis() + i,
                fuelLevel = 50 + i,
                engineRpm = 1000 + i * 100,
                vehicleSpeed = 30 + i,
                coolantTemp = 70 + i,
                engineLoad = 20 + i
            ))
        }
        
        val results = telemetryDao.snapshotRecent(5)
        assertEquals(5, results.size)
    }

    @Test
    fun multiTableDeletion_cascadesCorrectly() = runBlocking {
        val now = System.currentTimeMillis()
        val oldTime = now - TimeUnit.DAYS.toMillis(10)
        
        // Insert old records in all tables
        telemetryDao.insert(TelemetryEntity(ts = oldTime, fuelLevel = 50, engineRpm = 1000, vehicleSpeed = 30, coolantTemp = 70, engineLoad = 20))
        alertDao.insert(AlertEntity(ts = oldTime, severity = "LOW", code = "TEST", message = "Old alert"))
        anprEventDao.insert(AnprEventEntity(ts = oldTime, plateHash = "oldhash", confidence = 0.5f, snapshotId = null))
        clipsDao.insert(ClipEntity(ts = oldTime, reason = "old_clip", filePath = "/old.mp4", durationMs = 1000, sizeBytes = 1000, offloaded = true))
        
        val threshold = now - TimeUnit.DAYS.toMillis(5)
        
        telemetryDao.deleteOlderThan(threshold)
        alertDao.deleteOlderThan(threshold)
        anprEventDao.deleteOlderThan(threshold)
        clipsDao.deleteOlderThan(threshold)
        
        assertEquals(0, telemetryDao.snapshotRecent(10).size)
        assertEquals(0, alertDao.snapshotRecent(10).size)
        assertEquals(0, anprEventDao.snapshotRecent(10).size)
        assertEquals(0, clipsDao.snapshotRecent(10).size)
    }
}
