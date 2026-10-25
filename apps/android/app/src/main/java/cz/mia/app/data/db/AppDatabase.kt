package cz.mia.app.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Database(
	entities = [
		TelemetryEntity::class,
		AlertEntity::class,
		AnprEventEntity::class,
		ClipEntity::class,
		AuditEventEntity::class,
		WatchlistEntity::class,
	],
	version = 2,
	exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
	abstract fun telemetry(): TelemetryDao
	abstract fun alerts(): AlertDao
	abstract fun anpr(): AnprEventDao
	abstract fun clips(): ClipsDao
	abstract fun audit(): AuditDao
	abstract fun watchlist(): WatchlistDao

	companion object {
		const val NAME = "ai_servis.db"

		/**
		 * Adds the black book and the sightings index. Plate sightings from version 1 are deleted: their hashes used
		 * a key built into the app, so anyone could reverse them, and they would never match a hash made with this
		 * install's key (ADR-0018). Everything else is kept.
		 */
		val MIGRATION_1_2 = object : Migration(1, 2) {
			override fun migrate(db: SupportSQLiteDatabase) {
				db.execSQL("DELETE FROM `anpr_events`")
				db.execSQL(
					"CREATE TABLE IF NOT EXISTS `watchlist` (`plateHash` TEXT NOT NULL, `label` TEXT NOT NULL, " +
						"`addedAt` INTEGER NOT NULL, PRIMARY KEY(`plateHash`))"
				)
				db.execSQL(
					"CREATE INDEX IF NOT EXISTS `index_anpr_events_plateHash_ts` ON `anpr_events` (`plateHash`, `ts`)"
				)
			}
		}

		val MIGRATIONS = arrayOf(MIGRATION_1_2)
	}
}

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
	@Provides
	@Singleton
	fun provideDb(@ApplicationContext context: Context): AppDatabase =
		Room.databaseBuilder(context, AppDatabase::class.java, AppDatabase.NAME)
			.addMigrations(*AppDatabase.MIGRATIONS)
			.build()

	@Provides
	fun provideTelemetryDao(db: AppDatabase): TelemetryDao = db.telemetry()

	@Provides
	fun provideAlertDao(db: AppDatabase): AlertDao = db.alerts()

	@Provides
	fun provideAnprDao(db: AppDatabase): AnprEventDao = db.anpr()

	@Provides
	fun provideClipsDao(db: AppDatabase): ClipsDao = db.clips()

	@Provides
	fun provideAuditDao(db: AppDatabase): AuditDao = db.audit()

	@Provides
	fun provideWatchlistDao(db: AppDatabase): WatchlistDao = db.watchlist()
}
