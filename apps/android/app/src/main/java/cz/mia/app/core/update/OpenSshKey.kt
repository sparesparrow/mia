package cz.mia.app.core.update

import java.io.ByteArrayOutputStream
import java.security.interfaces.ECPublicKey

/** Writes an EC P-256 public key as an OpenSSH `authorized_keys` line, which is what the Pi's pairing endpoint takes. */
object OpenSshKey {
	const val TYPE = "ecdsa-sha2-nistp256"

	fun publicLine(key: ECPublicKey): String = "$TYPE ${base64(blob(key))}"

	fun blob(key: ECPublicKey): ByteArray {
		val out = ByteArrayOutputStream()
		writeString(out, TYPE.toByteArray())
		writeString(out, "nistp256".toByteArray())
		val x = fixed(key.w.affineX.toByteArray())
		val y = fixed(key.w.affineY.toByteArray())
		writeString(out, byteArrayOf(4) + x + y)
		return out.toByteArray()
	}

	/** BigInteger bytes to exactly 32: drop a sign byte, left-pad short values. */
	private fun fixed(raw: ByteArray): ByteArray {
		val trimmed = if (raw.size > 32) raw.copyOfRange(raw.size - 32, raw.size) else raw
		return ByteArray(32 - trimmed.size) + trimmed
	}

	private fun writeString(out: ByteArrayOutputStream, data: ByteArray) {
		out.write(byteArrayOf((data.size ushr 24).toByte(), (data.size ushr 16).toByte(), (data.size ushr 8).toByte(), data.size.toByte()))
		out.write(data)
	}

	// java.util.Base64 needs API 26; this is the same encoding without it (minSdk is 22).
	private fun base64(data: ByteArray): String {
		val alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
		val sb = StringBuilder()
		var i = 0
		while (i < data.size) {
			val b0 = data[i].toInt() and 0xff
			val b1 = if (i + 1 < data.size) data[i + 1].toInt() and 0xff else -1
			val b2 = if (i + 2 < data.size) data[i + 2].toInt() and 0xff else -1
			sb.append(alphabet[b0 shr 2])
			sb.append(alphabet[((b0 and 3) shl 4) or (if (b1 < 0) 0 else b1 shr 4)])
			sb.append(if (b1 < 0) '=' else alphabet[((b1 and 15) shl 2) or (if (b2 < 0) 0 else b2 shr 6)])
			sb.append(if (b2 < 0) '=' else alphabet[b2 and 63])
			i += 3
		}
		return sb.toString()
	}
}
