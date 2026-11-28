package cz.mia.app.core.update

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.io.File
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.SecureRandom
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.X509EncodedKeySpec
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/** Seals and opens the SSH private key bytes. */
interface KeyWrap {
	fun seal(plain: ByteArray): ByteArray
	fun open(sealed: ByteArray): ByteArray
}

/** AES-GCM with a key given by [secret]: the wrap behind both storage options below. */
abstract class AesGcmWrap : KeyWrap {
	protected abstract fun secret(): SecretKey

	override fun seal(plain: ByteArray): ByteArray {
		val cipher = Cipher.getInstance("AES/GCM/NoPadding")
		cipher.init(Cipher.ENCRYPT_MODE, secret())
		return cipher.iv + cipher.doFinal(plain)
	}

	override fun open(sealed: ByteArray): ByteArray {
		val cipher = Cipher.getInstance("AES/GCM/NoPadding")
		cipher.init(Cipher.DECRYPT_MODE, secret(), GCMParameterSpec(128, sealed.copyOfRange(0, 12)))
		return cipher.doFinal(sealed, 12, sealed.size - 12)
	}
}

/** API 22: a random AES key in an app-private no-backup file. Software-held; a rooted phone can read it (ADR-0023). */
class FileKeyWrap(private val file: File, private val random: SecureRandom = SecureRandom()) : AesGcmWrap() {
	override fun secret(): SecretKey {
		if (!file.exists() || file.length() != 32L) {
			file.parentFile?.mkdirs()
			file.writeBytes(ByteArray(32).also { random.nextBytes(it) })
		}
		return SecretKeySpec(file.readBytes(), "AES")
	}
}

/** API 23 and later: an AES key that never leaves the Android Keystore. */
class KeystoreKeyWrap(private val alias: String = "mia_update_wrap") : AesGcmWrap() {
	override fun secret(): SecretKey {
		val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
		(store.getKey(alias, null) as? SecretKey)?.let { return it }
		val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
		generator.init(
			KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
				.setBlockModes(KeyProperties.BLOCK_MODE_GCM)
				.setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
				.setKeySize(256)
				.build()
		)
		return generator.generateKey()
	}
}

/**
 * The phone's SSH identity for updates (ADR-0023): an EC P-256 pair made on first use, the private half sealed with
 * a [KeyWrap] and kept in [dir]. The key can run the update command on a Pi that paired it, and nothing else.
 * The terminal (ADR-0028) keeps its own pair under another [name], so an update key never becomes a login key.
 */
class SshKeyStore(private val dir: File, private val wrap: KeyWrap, private val name: String = "update_key") {
	@Synchronized
	fun keyPair(): KeyPair {
		val priv = File(dir, "$name.enc")
		val pub = File(dir, "$name.pub")
		val factory = KeyFactory.getInstance("EC")
		if (priv.exists() && pub.exists()) {
			try {
				return KeyPair(
					factory.generatePublic(X509EncodedKeySpec(pub.readBytes())),
					factory.generatePrivate(PKCS8EncodedKeySpec(wrap.open(priv.readBytes()))),
				)
			} catch (e: java.security.GeneralSecurityException) {
				// Unreadable (a restored backup, a lost wrap key): make a new pair; the Pi needs pairing again.
			}
		}
		val generator = KeyPairGenerator.getInstance("EC")
		generator.initialize(ECGenParameterSpec("secp256r1"))
		val pair = generator.generateKeyPair()
		dir.mkdirs()
		priv.writeBytes(wrap.seal(pair.private.encoded))
		pub.writeBytes(pair.public.encoded)
		return pair
	}

	fun publicLine(): String = OpenSshKey.publicLine(keyPair().public as ECPublicKey)

	companion object {
		/** Keystore-backed wrap where the platform allows it, the file wrap on API 22. */
		fun wrapFor(dir: File, alias: String = "mia_update_wrap"): KeyWrap =
			if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) KeystoreKeyWrap(alias) else FileKeyWrap(File(dir, "wrap.key"))
	}
}
