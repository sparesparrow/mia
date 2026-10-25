package cz.mia.app.core.security

import android.content.Context
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

/**
 * The one way a plate becomes a hash, for plates the camera reads and plates the user types (REQ-AND-004), so the
 * two always meet. Clear text goes in and is not kept.
 */
@Singleton
class PlateIdentity(private val key: () -> ByteArray) {
	@Inject
	constructor(store: PlateKeyStore) : this(store::key)

	fun hash(plate: String): String = PlateHasher.hmacSha256(plate, key())

	/** Whether typed text can be a plate: 4 to 10 letters and digits once spaces and dashes are gone. */
	fun isPlausible(plate: String): Boolean = PLATE.matches(PlateHasher.normalize(plate))

	companion object {
		private val PLATE = Regex("^[A-Z0-9]{4,10}$")
	}
}

@Module
@InstallIn(SingletonComponent::class)
object PlateKeyModule {
	@Provides
	@Singleton
	fun providePlateKeyStore(@ApplicationContext context: Context): PlateKeyStore =
		PlateKeyStore(File(context.noBackupFilesDir, PlateKeyStore.FILE_NAME))
}
