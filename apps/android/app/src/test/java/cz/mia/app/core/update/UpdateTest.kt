package cz.mia.app.core.update

// @req REQ-UPD-002 REQ-UPD-003 REQ-UPD-007

import java.io.ByteArrayOutputStream
import java.math.BigInteger
import java.security.KeyPairGenerator
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.util.zip.GZIPOutputStream
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class UpdateTest {
	private val schemas = mapOf("a.fbs" to "table A {}\n".toByteArray(), "b.fbs" to "table B {}\n".toByteArray())
	private val ownHash = SchemaHash.compute(schemas)

	private fun bundle(version: String, files: Map<String, ByteArray> = schemas.mapKeys { "schemas/${it.key}" }): Pair<ByteArray, String> {
		val tar = Tar.write(files.map { it.key to it.value })
		val gz = ByteArrayOutputStream().also { out -> GZIPOutputStream(out).use { it.write(tar) } }.toByteArray()
		return gz to "${SchemaHash.sha256Hex(gz)}  ${PackageBuilder.bundleName(version)}\n"
	}

	@Test
	fun schemaHash_matchesTheValueTheTool_computes() {
		// Same input and expected value as GOLDEN_SCHEMA_HASH in tests/unit/tools/test_mia_apply_update.py.
		assertEquals("36f8bc162b7316679c41da930a62b9f201d9236ac7939e7239e8e41427bbefc2", ownHash)
	}

	@Test
	fun schemaHash_doesNotDependOnInsertionOrder() {
		val reversed = linkedMapOf("b.fbs" to schemas.getValue("b.fbs"), "a.fbs" to schemas.getValue("a.fbs"))
		assertEquals(ownHash, SchemaHash.compute(reversed))
	}

	@Test
	fun yaml_writesTheSubsetTheTool_parses() {
		val yaml = UpdateConfig("Audi A4", "info", 14, 500, true).toYaml()
		assertEquals(
			"version: 1\ndevice_name: \"Audi A4\"\nlogging:\n  level: \"info\"\n  retention_days: 14\n" +
				"telemetry:\n  interval_ms: 500\n  enabled: true\n",
			yaml,
		)
	}

	@Test
	fun yaml_minimalConfigIsJustTheVersion() {
		assertEquals("version: 1\n", UpdateConfig().toYaml())
	}

	@Test
	fun yaml_valuesCannotBreakOutOfTheirLine() {
		assertEquals("\"a\\\"b\\nc\\\\\"", UpdateConfig.quote("a\"b\nc\\"))
		val bad = UpdateConfig(deviceName = "x\nversion: 2")
		assertTrue(bad.problems().isNotEmpty())
		try {
			bad.toYaml()
			fail("a name with a newline must be refused")
		} catch (e: IllegalArgumentException) {
		}
	}

	@Test
	fun config_rangesFollowTheSchema() {
		assertTrue(UpdateConfig(logRetentionDays = 0).problems().isNotEmpty())
		assertTrue(UpdateConfig(logRetentionDays = 91).problems().isNotEmpty())
		assertTrue(UpdateConfig(telemetryIntervalMs = 99).problems().isNotEmpty())
		assertTrue(UpdateConfig(logLevel = "loud").problems().isNotEmpty())
		assertTrue(UpdateConfig("A", "debug", 90, 60000, false).problems().isEmpty())
	}

	@Test
	fun builder_makesAPackageTheToolCanRead() {
		val (gz, sums) = bundle("2.3.0")
		val pkg = PackageBuilder.build("2.3.0", gz, sums, UpdateConfig(deviceName = "Car"), ownHash)
		val files = Tar.read(pkg.inputStream()) { true }
		assertEquals(setOf("mia-rpi-backend-2.3.0.tar.gz", "SHA256SUMS", "config.yaml", "manifest.json"), files.keys)
		val manifest = String(files.getValue("manifest.json"))
		assertTrue(manifest.contains("\"schema_hash\": \"$ownHash\""))
		assertTrue(manifest.contains("\"package_sha256\": \"${SchemaHash.sha256Hex(gz)}\""))
		assertEquals(sums, String(files.getValue("SHA256SUMS")))
		assertTrue(files.getValue("mia-rpi-backend-2.3.0.tar.gz").contentEquals(gz))
	}

	@Test
	fun builder_refusesABackendWithOtherSchemas() {
		val (gz, sums) = bundle("2.3.0", mapOf("schemas/a.fbs" to "table Changed {}\n".toByteArray()))
		try {
			PackageBuilder.build("2.3.0", gz, sums, UpdateConfig(), ownHash)
			fail("expected a schema_hash refusal")
		} catch (e: UpdateRefused) {
			assertTrue(e.message!!.contains("schema_hash"))
		}
	}

	@Test
	fun builder_refusesABundleThatDoesNotMatchItsChecksum() {
		val (gz, _) = bundle("2.3.0")
		val sums = "${"0".repeat(64)}  mia-rpi-backend-2.3.0.tar.gz\n"
		try {
			PackageBuilder.build("2.3.0", gz, sums, UpdateConfig(), ownHash)
			fail("expected a checksum refusal")
		} catch (e: UpdateRefused) {
			assertTrue(e.message!!.contains("SHA256SUMS"))
		}
	}

	@Test
	fun builder_refusesAVersionThatIsNotARelease_andAMissingChecksumLine() {
		val (gz, sums) = bundle("2.3.0")
		for (version in listOf("../2.3.0", "latest", "2.3")) {
			try {
				PackageBuilder.build(version, gz, sums, UpdateConfig(), ownHash)
				fail("version $version must be refused")
			} catch (e: UpdateRefused) {
			}
		}
		try {
			PackageBuilder.build("2.3.0", gz, "", UpdateConfig(), ownHash)
			fail("a missing checksum line must be refused")
		} catch (e: UpdateRefused) {
		}
	}

	@Test
	fun builder_picksItsLineOutOfAReleaseWideChecksumFile() {
		val (gz, line) = bundle("2.3.0")
		val sums = "${"1".repeat(64)}  app-release.apk\n$line${"2".repeat(64)}  SHA256SUMS.txt\n"
		val pkg = PackageBuilder.build("2.3.0", gz, sums, UpdateConfig(), ownHash)
		assertEquals(line, String(Tar.read(pkg.inputStream()) { it == "SHA256SUMS" }.getValue("SHA256SUMS")))
	}

	@Test
	fun result_readsTheLastJsonLine() {
		val ok = UpdateResult.parse("noise\n{\"ok\": true, \"step\": \"done\", \"version\": \"2.3.0\", \"error\": null}\n", 0)
		assertTrue(ok.ok); assertEquals("2.3.0", ok.version)
		val failed = UpdateResult.parse("{\"ok\": false, \"step\": \"verify\", \"version\": null, \"error\": \"bad\"}", 1)
		assertFalse(failed.ok); assertEquals("verify", failed.step); assertEquals("bad", failed.error)
		assertFalse(UpdateResult.parse("", 255).ok)
		assertFalse(UpdateResult.parse("{\"ok\": true, \"step\": \"done\", \"version\": \"1.0.0\", \"error\": null}", 1).ok)
	}

	@Test
	fun openSshKey_hasTheWireLayoutSshExpects() {
		val generator = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }
		val key = generator.generateKeyPair().public as ECPublicKey
		val blob = OpenSshKey.blob(key)
		// 4+19 type, 4+8 curve name, 4+65 point
		assertEquals(4 + 19 + 4 + 8 + 4 + 65, blob.size)
		assertEquals(65, blob[blob.size - 66].toInt())
		assertEquals(4, blob[blob.size - 65].toInt())
		assertEquals(key.w.affineX, BigInteger(1, blob.copyOfRange(blob.size - 64, blob.size - 32)))
		assertTrue(OpenSshKey.publicLine(key).startsWith("ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTY"))
	}
}
