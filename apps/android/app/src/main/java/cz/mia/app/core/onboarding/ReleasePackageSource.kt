package cz.mia.app.core.onboarding

import cz.mia.app.core.update.PackageBuilder
import cz.mia.app.core.update.ReleaseDownloader
import cz.mia.app.core.update.SchemaHash
import cz.mia.app.core.update.UpdateRefused
import java.io.File
import java.io.IOException

/** No download and no saved copy for this version. The text is shown to the user as it is. */
class ReleaseUnavailable : IOException(MESSAGE) {
	companion object {
		const val MESSAGE = "The release package cannot be downloaded and none is saved on this phone"
	}
}

/**
 * Gets the release bundle and its SHA256SUMS (ADR-0023): from the network, and every verified download is saved under
 * [dir] keyed by version. When the download fails and a saved copy of that version exists it is used. A saved copy is
 * never trusted: it is checked against its SHA256SUMS again before every use (the package build checks once more).
 */
class ReleasePackageSource(private val dir: File, private val fetch: (version: String) -> ReleaseDownloader.Downloaded) {
	class Obtained(val release: ReleaseDownloader.Downloaded, val note: String?)

	/** @throws UpdateRefused a downloaded bundle does not match its checksum, or the version is not a release version
	 *  @throws ReleaseUnavailable download failed and no usable saved copy exists */
	fun obtain(version: String): Obtained {
		if (!SAFE_VERSION.matches(version)) throw UpdateRefused("Not a release version: $version")
		val fresh = try {
			fetch(version)
		} catch (e: IOException) {
			null // the text of a network error is not shown: it can carry the URL
		}
		if (fresh != null) {
			if (!matches(version, fresh)) throw UpdateRefused("${PackageBuilder.bundleName(version)} does not match its SHA256SUMS entry")
			save(version, fresh)
			return Obtained(fresh, null)
		}
		val saved = load(version)
		if (saved == null || !matches(version, saved)) {
			if (saved != null) folder(version).deleteRecursively() // damaged or tampered: drop it
			throw ReleaseUnavailable()
		}
		return Obtained(saved, USING_SAVED_NOTE)
	}

	private fun folder(version: String) = File(dir, "release-$version")

	private fun save(version: String, release: ReleaseDownloader.Downloaded) {
		try { // best effort: failing to save must not fail the install
			val target = folder(version)
			val tmp = File(dir, "release-$version.tmp")
			tmp.deleteRecursively()
			if (!tmp.mkdirs()) return
			File(tmp, BUNDLE).writeBytes(release.bundle)
			File(tmp, SUMS).writeText(release.sha256sums, Charsets.UTF_8)
			target.deleteRecursively()
			if (!tmp.renameTo(target)) tmp.deleteRecursively()
		} catch (_: IOException) {
		}
	}

	private fun load(version: String): ReleaseDownloader.Downloaded? =
		try {
			val folder = folder(version)
			val bundle = File(folder, BUNDLE)
			val sums = File(folder, SUMS)
			if (bundle.isFile && sums.isFile) ReleaseDownloader.Downloaded(bundle.readBytes(), sums.readText(Charsets.UTF_8)) else null
		} catch (_: IOException) {
			null
		}

	private fun matches(version: String, release: ReleaseDownloader.Downloaded): Boolean {
		val name = PackageBuilder.bundleName(version)
		val listed = release.sha256sums.lineSequence()
			.map { it.trim().split(Regex(" [ *]"), limit = 2) }
			.firstOrNull { it.size == 2 && it[1] == name }?.get(0)
		return listed != null && listed == SchemaHash.sha256Hex(release.bundle)
	}

	companion object {
		const val USING_SAVED_NOTE = "Using the release package saved earlier on this phone"
		private const val BUNDLE = "bundle.tar.gz"
		private const val SUMS = "SHA256SUMS.txt"
		private val SAFE_VERSION = Regex("^[0-9]+\\.[0-9]+\\.[0-9]+(?:[-+][0-9A-Za-z.-]{1,32})?$")
	}
}
