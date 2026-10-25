package cz.mia.app.core.security

// @req REQ-AND-004

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlateKeyStoreTest {
	private val dir: File = Files.createTempDirectory("plate-key").toFile().apply { deleteOnExit() }
	private val file = File(dir, PlateKeyStore.FILE_NAME)

	@Test
	fun `the first use makes a 32-byte key and stores it`() {
		assertFalse(file.exists())
		val key = PlateKeyStore(file).key()
		assertEquals(32, key.size)
		assertArrayEquals(key, file.readBytes())
	}

	@Test
	fun `the key survives a restart`() {
		val first = PlateKeyStore(file).key()
		val second = PlateKeyStore(file).key()
		assertArrayEquals(first, second)
	}

	@Test
	fun `two installs get different keys`() {
		val a = PlateKeyStore(File(dir, "a.key")).key()
		val b = PlateKeyStore(File(dir, "b.key")).key()
		assertFalse(a.contentEquals(b))
	}

	@Test
	fun `a key file of the wrong size is replaced`() {
		file.writeBytes(ByteArray(7) { 1 })
		val key = PlateKeyStore(file).key()
		assertEquals(32, key.size)
		assertArrayEquals(key, file.readBytes())
		assertFalse(File(dir, "${PlateKeyStore.FILE_NAME}.tmp").exists())
	}

	@Test
	fun `callers get a copy, so they cannot change the key`() {
		val store = PlateKeyStore(file)
		val key = store.key()
		key.fill(0)
		assertTrue(store.key().any { it != 0.toByte() })
	}
}
