package cz.mia.app.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Database(
	entities = [TelemetryEntity::class, AlertEntity::class, AnprEventEntity::class, ClipEntity::class, AuditEventEntity::class],
	version = 1,
	exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
	abstract fun telemetry(): TelemetryDao
	abstract fun alerts(): AlertDao
	abstract fun anpr(): AnprEventDao
	abstract fun clips(): ClipsDao
	abstract fun audit(): AuditDao
}

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
	@Provides
	@Singleton
	fun provideDb(@ApplicationContext context: Context): AppDatabase =
		Room.databaseBuilder(context, AppDatabase::class.java, "ai_servis.db").build()

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
}
