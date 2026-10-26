package cz.mia.app.data.db

// @req REQ-AND-011 REQ-AND-020

import android.content.Context
import androidx.room.Room
import androidx.room.testing.MigrationTestHelper
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import kotlin.test.assertEquals

/** Upgrades a version 1 database, built from the exported schema in app/schemas, to the current one. */
@RunWith(AndroidJUnit4::class)
class MigrationTest {
	private val name = "migration-test.db"

	@get:Rule
	val helper = MigrationTestHelper(InstrumentationRegistry.getInstrumentation(), AppDatabase::class.java)

	private fun SupportSQLiteDatabase.count(table: String): Int =
		query("SELECT COUNT(*) FROM $table").use { it.moveToFirst(); it.getInt(0) }

	@Test
	fun version1To2_keepsEverythingButTheOldPlateSightings() {
		helper.createDatabase(name, 1).apply {
			execSQL("INSERT INTO telemetry (ts, fuelLevel, engineRpm, vehicleSpeed, coolantTemp, engineLoad) VALUES (1, 50, 900, 0, 80, 10)")
			execSQL("INSERT INTO alerts (ts, severity, code, message) VALUES (2, 'WARNING', 'FUEL_LOW', 'Palivo 12 %.')")
			execSQL("INSERT INTO anpr_events (ts, plateHash, confidence, snapshotId) VALUES (3, 'hash-made-with-the-built-in-key', 0.9, NULL)")
			execSQL("INSERT INTO clips (ts, reason, filePath, durationMs, sizeBytes, offloaded) VALUES (4, 'manual', '/c.mp4', 1000, 10, 0)")
			execSQL("INSERT INTO audit_events (ts, category, action, details) VALUES (5, 'policy', 'set_vin', NULL)")
			close()
		}

		// Validates the result against the exported version 2 schema, the new table and index included.
		val db = helper.runMigrationsAndValidate(name, 2, true, AppDatabase.MIGRATION_1_2)

		assertEquals(1, db.count("telemetry"))
		assertEquals(1, db.count("alerts"))
		assertEquals(1, db.count("clips"))
		assertEquals(1, db.count("audit_events"))
		assertEquals(0, db.count("anpr_events"))
		assertEquals(0, db.count("watchlist"))
		db.close()
	}

	@Test
	fun theAppOpensAnUpgradedDatabaseWithItsOwnMigrations() {
		helper.createDatabase(name, 1).close()
		val context = ApplicationProvider.getApplicationContext<Context>()
		val room = Room.databaseBuilder(context, AppDatabase::class.java, name)
			.addMigrations(*AppDatabase.MIGRATIONS)
			.build()
		helper.closeWhenFinished(room)

		runBlocking {
			room.watchlist().upsert(WatchlistEntity("h", "soused", 1))
			assertEquals("soused", room.watchlist().find("h")?.label)
		}
	}
}
