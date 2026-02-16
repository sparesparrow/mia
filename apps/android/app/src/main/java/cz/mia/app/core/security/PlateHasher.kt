package cz.mia.app.core.security

import java.util.Base64
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object PlateHasher {
	private const val HMAC_ALGO = "HmacSHA256"

	fun normalize(input: String): String = input
		.trim()
		.uppercase()
		.replace("O", "0")
		.replace("B", "8")
		.replace(" ", "")

	fun hmacSha256(plate: String, secret: ByteArray): String {
		val normalized = normalize(plate)
		val mac = Mac.getInstance(HMAC_ALGO)
		mac.init(SecretKeySpec(secret, HMAC_ALGO))
		val raw = mac.doFinal(normalized.toByteArray(Charsets.UTF_8))
		return Base64.getEncoder().encodeToString(raw)
	}
}
