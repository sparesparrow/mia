package cz.mia.app.core.update

import java.security.MessageDigest

/**
 * The fingerprint of the FlatBuffers schemas (ADR-0023, REQ-UPD-002). Same algorithm as `schema_hash` in
 * bin/mia-apply-update: for each file name in sorted order, "name\n<sha256 hex of the content>\n", hashed
 * with SHA-256. The phone pushes a backend only when its hash equals the one of the schemas this app was built with.
 */
object SchemaHash {
	fun compute(files: Map<String, ByteArray>): String {
		val digest = MessageDigest.getInstance("SHA-256")
		for (name in files.keys.sorted()) {
			digest.update("$name\n${sha256Hex(files.getValue(name))}\n".toByteArray(Charsets.UTF_8))
		}
		return digest.digest().toHex()
	}

	fun sha256Hex(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).toHex()

	private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
}
