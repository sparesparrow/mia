package cz.mia.app.core.update

/** Why a package was not built. */
class UpdateRefused(message: String) : Exception(message)

/** The manifest bin/mia-apply-update checks (ADR-0023). */
data class Manifest(val version: String, val packageName: String, val packageSha256: String, val schemaHash: String) {
	fun toJson(): String =
		"{\"version\": ${UpdateConfig.quote(version)}, \"package\": ${UpdateConfig.quote(packageName)}, " +
			"\"package_sha256\": ${UpdateConfig.quote(packageSha256)}, \"schema_hash\": ${UpdateConfig.quote(schemaHash)}}"
}

/**
 * Builds the `.miapkg` the Pi's mia-apply-update reads (REQ-UPD-002, REQ-UPD-007): the release bundle, its
 * SHA256SUMS, config.yaml and manifest.json. Pure: the download is [ReleaseDownloader]'s job.
 */
object PackageBuilder {
	private val VERSION = Regex("^[0-9]+\\.[0-9]+\\.[0-9]+(?:[-+][0-9A-Za-z.-]{1,32})?$")

	fun bundleName(version: String) = "mia-rpi-backend-$version.tar.gz"

	/** The schema hash of a release bundle, from the .fbs files under schemas/ inside it. */
	fun bundleSchemaHash(bundle: ByteArray): String {
		val files = Tar.readGz(bundle) { Regex("^schemas/[^/]+\\.fbs$").matches(it) }
			.mapKeys { it.key.removePrefix("schemas/") }
		if (files.isEmpty()) throw UpdateRefused("The release bundle holds no schemas/*.fbs")
		return SchemaHash.compute(files)
	}

	/**
	 * @param ownSchemaHash the hash of the schemas this app was built with; a bundle with another hash is refused
	 * @throws UpdateRefused when the version, the checksum, the schema hash or the config is wrong
	 */
	fun build(version: String, bundle: ByteArray, sha256sums: String, config: UpdateConfig, ownSchemaHash: String): ByteArray {
		if (!VERSION.matches(version)) throw UpdateRefused("Not a release version: $version")
		val name = bundleName(version)
		val digest = SchemaHash.sha256Hex(bundle)
		val listed = sha256sums.lineSequence()
			.map { it.trim().split(Regex(" [ *]"), limit = 2) }
			.firstOrNull { it.size == 2 && it[1] == name }?.get(0)
		if (listed == null) throw UpdateRefused("SHA256SUMS does not list $name")
		if (listed != digest) throw UpdateRefused("$name does not match its SHA256SUMS entry")
		val bundleHash = bundleSchemaHash(bundle)
		if (bundleHash != ownSchemaHash) {
			throw UpdateRefused("This backend speaks other FlatBuffers schemas than this app (schema_hash differs); update the app too")
		}
		val problems = config.problems()
		if (problems.isNotEmpty()) throw UpdateRefused(problems.joinToString("; "))
		val manifest = Manifest(version, name, digest, bundleHash)
		return Tar.write(
			listOf(
				name to bundle,
				// Only the line that was just verified: the release file lists every artifact.
				"SHA256SUMS" to "$listed  $name\n".toByteArray(Charsets.UTF_8),
				"config.yaml" to config.toYaml().toByteArray(Charsets.UTF_8),
				"manifest.json" to manifest.toJson().toByteArray(Charsets.UTF_8),
			)
		)
	}
}
