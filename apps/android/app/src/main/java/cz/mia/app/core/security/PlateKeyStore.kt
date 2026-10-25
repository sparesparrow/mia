package cz.mia.app.core.security

import android.util.Log
import java.io.File
import java.io.IOException
import java.security.SecureRandom

/**
 * The secret behind every plate hash (ADR-0018): 32 random bytes made on first use and kept in the app's no-backup
 * files, so a hash means nothing off this install and is not restored onto another phone.
 *
 * A key file of the wrong size is treated as lost and replaced; plates stored under the old key then no longer match.
 */
class PlateKeyStore(
	private val file: File,
	private val random: SecureRandom = SecureRandom(),
) {
	private var cached: ByteArray? = null

	@Synchronized
	fun key(): ByteArray {
		cached?.let { return it.copyOf() }
		val stored = read()
		val key = stored ?: create()
		cached = key
		return key.copyOf()
	}

	private fun read(): ByteArray? {
		if (!file.exists()) return null
		val bytes = try {
			file.readBytes()
		} catch (e: IOException) {
			Log.w(TAG, "Plate key unreadable, replacing it", e)
			return null
		}
		if (bytes.size != KEY_BYTES) {
			Log.w(TAG, "Plate key has ${bytes.size} bytes, replacing it")
			return null
		}
		return bytes
	}

	private fun create(): ByteArray {
		val key = ByteArray(KEY_BYTES).also { random.nextBytes(it) }
		file.parentFile?.mkdirs()
		val partial = File(file.parentFile, "${file.name}.tmp")
		partial.writeBytes(key)
		if (!partial.renameTo(file)) {
			file.delete()
			check(partial.renameTo(file)) { "Cannot store the plate key" }
		}
		return key
	}

	companion object {
		private const val TAG = "PlateKeyStore"
		const val KEY_BYTES = 32
		const val FILE_NAME = "plate_hash.key"
	}
}
