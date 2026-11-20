package cz.mia.app.core.onboarding

// @req REQ-ONB-008

import com.google.gson.JsonParser
import cz.mia.app.core.update.PackageBuilder
import cz.mia.app.core.update.ReleaseDownloader
import cz.mia.app.core.update.UpdateConfig
import cz.mia.app.core.update.UpdateResult
import java.io.File
import java.nio.file.Files
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNotEquals
import org.junit.Assert.fail
import org.junit.Assert.assertTrue
import org.junit.Test

class OnboardingMachineTest {
	private val piFp = "SHA256:BV5sCSaH1iH/isrgeu9HT1AbcE//5ZfENw2cH1swC2M"
	private val phoneKey = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBPhone phone"
	private val secretKey = "ACTIVATION-SECRET-7f3a9c"
	private val grantJson = "{\"jti\":\"j-1\",  \"plan\":\"pro\",\"note\":\"a\\\\b \\u00e9\"}"
	private val pi = FoundPi("192.168.4.1", Transport.MiaWifi, piFp)

	private class FakeStorage : KnownPiStorage {
		var lines: Set<String> = emptySet()
		override fun read() = lines
		override fun write(lines: Set<String>) { this.lines = lines }
	}

	private class FakeAuth(var result: Result<Grant>) : AuthPort {
		val calls = mutableListOf<Triple<String, String, String>>()
		var throwable: Throwable? = null

		/** When set, every success carries a different signature, like a server issuing a fresh grant per request. */
		var freshEachTime = false
		override fun requestGrant(activationKey: String, devicePublicFp: String, phonePublicKeyLine: String): Result<Grant> {
			calls += Triple(activationKey, devicePublicFp, phonePublicKeyLine)
			throwable?.let { throw it }
			val grant = result.getOrNull()
			return if (freshEachTime && grant != null) Result.success(grant.copy(signature = grant.signature + "#" + calls.size)) else result
		}
	}

	private class FakeDiscovery(var result: Result<List<FoundPi>>) : DiscoveryPort {
		var calls = 0
		override suspend fun find(activationKey: String): Result<List<FoundPi>> { calls++; return result }
	}

	private class FakeEnroller(var outcome: EnrollOutcome) : EnrollTransport {
		val requests = mutableListOf<Pair<String, String>>()
		val pins = mutableListOf<String>()
		override fun enroll(host: String, expectedFp: String, requestJson: String): EnrollOutcome {
			requests += host to requestJson
			pins += expectedFp
			return outcome
		}
	}

	private class FakeInstaller(var result: UpdateResult) : InstallPort {
		val installs = mutableListOf<UpdateConfig>()
		val pis = mutableListOf<FoundPi>()
		var note: String? = null
		override suspend fun install(pi: FoundPi, config: UpdateConfig, onProgress: (Int, Int) -> Unit, onNote: (String) -> Unit): UpdateResult {
			installs += config
			pis += pi
			note?.let(onNote)
			onProgress(10, 100)
			return result
		}
	}

	private class FakePairing(val bluetooth: MutableList<StepOutcome>, val wifi: MutableList<StepOutcome>) : SystemPairing {
		var bluetoothCalls = 0
		var wifiCalls = 0
		override suspend fun bondBluetooth(): StepOutcome { bluetoothCalls++; return bluetooth.removeAt(0) }
		override suspend fun suggestWifi(): StepOutcome { wifiCalls++; return wifi.removeAt(0) }
	}

	private inner class Rig(scope: TestScope, slot: SystemPairing? = null) {
		val storage = FakeStorage()
		val store = KnownPiStore(storage)
		val auth = FakeAuth(Result.success(Grant(grantJson, "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----", "pro", 1_900_000_000L)))
		val discovery = FakeDiscovery(Result.success(listOf(pi)))
		val enroller = FakeEnroller(EnrollOutcome(true, "enrolled", null, null))
		val installer = FakeInstaller(UpdateResult(true, "done", "2.3.0", null))
		val pairing = FakePairing(mutableListOf(StepOutcome.Done), mutableListOf(StepOutcome.Done))
		val machine = OnboardingMachine(
			auth, discovery, enroller, installer, slot ?: pairing, store, { phoneKey },
			scope, UnconfinedTestDispatcher(scope.testScheduler),
		)

		fun toFirstSetup() {
			machine.begin()
			machine.submitActivationKey(secretKey)
		}
	}

	@Test
	fun happyPathReachesDone() = runTest {
		val r = Rig(this)
		assertEquals(OnboardingState.Welcome, r.machine.state.value)
		r.toFirstSetup()
		assertEquals(OnboardingState.FirstSetup, r.machine.state.value)
		r.machine.submitFirstSetup(UpdateConfig(deviceName = "Audi A4"))
		assertEquals(OnboardingState.PairingPhone, r.machine.state.value)
		assertEquals(listOf(UpdateConfig(deviceName = "Audi A4")), r.installer.installs)
		assertTrue(r.store.known().isEmpty()) // not before Done
		r.machine.resume()
		assertEquals(OnboardingState.PairAdapter, r.machine.state.value)
		r.machine.finishAdapterStep()
		assertEquals(OnboardingState.Done, r.machine.state.value)
		assertEquals(listOf(KnownPi(piFp, "192.168.4.1")), r.store.known())
		assertEquals(listOf(Triple(secretKey, piFp, phoneKey)), r.auth.calls)
	}

	@Test
	fun authServerDownStaysRetryableNeverInstalls() = runTest {
		val r = Rig(this)
		r.auth.result = Result.failure(AuthServerError.Retryable("network error"))
		r.toFirstSetup()
		val failed = r.machine.state.value as OnboardingState.Failed
		assertTrue(failed.retryable)
		assertEquals("authorizing", failed.step)
		r.machine.submitFirstSetup(UpdateConfig()) // not in FirstSetup: ignored
		r.machine.retry()
		assertTrue((r.machine.state.value as OnboardingState.Failed).retryable)
		assertEquals(2, r.auth.calls.size)
		assertTrue(r.enroller.requests.isEmpty())
		assertTrue(r.installer.installs.isEmpty())
		// The server comes back: retry goes on from the same place.
		r.auth.result = Result.success(Grant(grantJson, "sig", "pro", 1L))
		r.machine.retry()
		assertEquals(OnboardingState.FirstSetup, r.machine.state.value)
		assertEquals(1, r.discovery.calls) // retry did not rescan
	}

	@Test
	fun discoveryFailureWhenDevicesCallIsDownIsRetryable() = runTest {
		val r = Rig(this)
		r.discovery.result = Result.failure(AuthServerError.Retryable("server status 503"))
		r.toFirstSetup()
		val failed = r.machine.state.value as OnboardingState.Failed
		assertTrue(failed.retryable)
		assertEquals("finding_pi", failed.step)
		assertTrue(r.auth.calls.isEmpty())
		assertTrue(r.installer.installs.isEmpty())
	}

	@Test
	fun unauthorizedKeyIsNotRetryable() = runTest {
		val r = Rig(this)
		r.auth.result = Result.failure(AuthServerError.Unauthorized())
		r.toFirstSetup()
		val failed = r.machine.state.value as OnboardingState.Failed
		assertFalse(failed.retryable)
		r.machine.retry()
		assertEquals(failed, r.machine.state.value)
		assertEquals(1, r.auth.calls.size)
		assertTrue(r.enroller.requests.isEmpty())
		r.auth.result = Result.failure(AuthServerError.UnknownDevice())
		r.machine.restart()
		r.machine.submitActivationKey(secretKey)
		assertFalse((r.machine.state.value as OnboardingState.Failed).retryable)
	}

	@Test
	fun cancelledSystemDialogResumesSameStep() = runTest {
		val r = Rig(this)
		r.pairing.bluetooth.clear()
		r.pairing.bluetooth += StepOutcome.Cancelled("user dismissed")
		r.pairing.bluetooth += StepOutcome.Done
		r.toFirstSetup()
		r.machine.submitFirstSetup(UpdateConfig())
		r.machine.resume()
		assertEquals(OnboardingState.PairingPhone, r.machine.state.value)
		assertNotNull(r.machine.pairingIssue.value)
		assertEquals(0, r.pairing.wifiCalls)
		r.machine.retry() // same step again, not the Wi-Fi one
		assertEquals(2, r.pairing.bluetoothCalls)
		assertEquals(1, r.pairing.wifiCalls)
		assertEquals(OnboardingState.PairAdapter, r.machine.state.value)
		assertEquals(null, r.machine.pairingIssue.value)
	}

	@Test
	fun cancelledSystemDialogResumedDirectlyAsksForTheSameStep() = runTest {
		val r = Rig(this)
		r.pairing.bluetooth.clear()
		r.pairing.bluetooth += StepOutcome.Cancelled("user dismissed")
		r.pairing.bluetooth += StepOutcome.Done
		r.toFirstSetup()
		r.machine.submitFirstSetup(UpdateConfig())
		r.machine.resume()
		assertEquals(OnboardingState.PairingPhone, r.machine.state.value)
		assertNotNull(r.machine.pairingIssue.value)
		r.machine.resume() // the screen's button: same dialog again
		assertEquals(2, r.pairing.bluetoothCalls)
		assertEquals(1, r.pairing.wifiCalls)
		assertEquals(OnboardingState.PairAdapter, r.machine.state.value)
		assertEquals(null, r.machine.pairingIssue.value)
		assertEquals(1, r.enroller.requests.size)
	}

	@Test
	fun unavailableWifiIsSkippedAndShownNotFatal() = runTest {
		val r = Rig(this)
		r.pairing.wifi.clear()
		r.pairing.wifi += StepOutcome.Unavailable("no password delivered")
		r.toFirstSetup()
		r.machine.submitFirstSetup(UpdateConfig())
		r.machine.resume()
		assertEquals(OnboardingState.PairAdapter, r.machine.state.value)
		assertTrue(r.machine.notes.value.single().contains("Wi-Fi skipped"))
	}

	@Test
	fun forgetsNothingOnFailure() = runTest {
		val r = Rig(this)
		r.store.save("SHA256:old", "10.0.0.9")
		val before = r.store.known()
		// 1. the Pi refuses the enrollment
		r.enroller.outcome = EnrollOutcome(false, "grant", "grant expired", null)
		r.toFirstSetup()
		assertTrue(r.machine.state.value is OnboardingState.Failed)
		assertEquals(before, r.store.known())
		// 2. the install fails
		r.enroller.outcome = EnrollOutcome(true, "enrolled", null, null)
		r.machine.retry()
		assertEquals(OnboardingState.FirstSetup, r.machine.state.value)
		r.installer.result = UpdateResult(false, "verify", null, "bad checksum")
		r.machine.submitFirstSetup(UpdateConfig())
		assertEquals(OnboardingState.Failed("installing", true, "bad checksum"), r.machine.state.value)
		assertEquals(before, r.store.known())
		// 3. a cancelled dialog
		r.installer.result = UpdateResult(true, "done", "2.3.0", null)
		r.machine.retry()
		r.pairing.bluetooth.clear()
		r.pairing.bluetooth += StepOutcome.Cancelled("x")
		r.machine.resume()
		assertEquals(OnboardingState.PairingPhone, r.machine.state.value)
		assertEquals(before, r.store.known())
	}

	@Test
	fun firstSetupFormProblemsStayInFirstSetup() = runTest {
		val r = Rig(this)
		r.toFirstSetup()
		r.machine.submitFirstSetup(UpdateConfig(deviceName = "!bad name!", logRetentionDays = 500))
		assertEquals(OnboardingState.FirstSetup, r.machine.state.value)
		assertEquals(2, r.machine.formProblems.value.size)
		assertTrue(r.installer.installs.isEmpty())
		r.machine.submitFirstSetup(UpdateConfig(deviceName = "Audi"))
		assertTrue(r.machine.formProblems.value.isEmpty())
		assertEquals(1, r.installer.installs.size)
	}

	@Test
	fun firstSetupFormProducesSchemaValidYaml() {
		// No YAML or JSON-schema library on the JVM test classpath: a small reader for the strict subset toYaml writes
		// (`key: value`, one level of sections) is checked against the schema's properties, required, types and limits.
		val schema = JsonParser.parseString(schemaFile().readText()).asJsonObject
		val props = schema.getAsJsonObject("properties")
		for (config in listOf(UpdateConfig(), UpdateConfig("Audi A4", "info", 14, 500, true), UpdateConfig(logLevel = "debug"))) {
			val doc = parseYaml(config.toYaml())
			schema.getAsJsonArray("required").forEach { assertTrue("required ${it.asString}", doc.containsKey(it.asString)) }
			for ((key, value) in doc) {
				val rule = props.getAsJsonObject(key) ?: error("key not allowed by the schema: $key")
				if (value is Map<*, *>) {
					val inner = rule.getAsJsonObject("properties")
					for ((k, v) in value) checkScalar(inner.getAsJsonObject(k as String) ?: error("key not allowed: $key.$k"), v)
				} else {
					checkScalar(rule, value)
				}
			}
			assertFalse(config.toYaml().contains("key", ignoreCase = true)) // no api key or other secret field in the config
		}
	}

	@Test
	fun enrollRequestIsExactlyTheGrantSignatureAndPhoneKey() = runTest {
		val r = Rig(this)
		r.toFirstSetup()
		val (host, request) = r.enroller.requests.single()
		assertEquals("192.168.4.1", host)
		val json = JsonParser.parseString(request).asJsonObject
		assertEquals(setOf("grant", "signature", "phone_public_key"), json.keySet())
		val grant = r.auth.result.getOrThrow()
		assertEquals(grant.json, json.get("grant").asString) // byte-identical: the signature covers these characters
		assertEquals(grant.signature, json.get("signature").asString)
		assertEquals(phoneKey, json.get("phone_public_key").asString)
		assertFalse(request.contains(secretKey))
	}

	@Test
	fun activationKeyNeverAppearsInStateOrMessages() = runTest {
		val r = Rig(this)
		val seen = mutableListOf<String>()
		fun snap() {
			seen += r.machine.state.value.toString()
			seen += r.machine.notes.value.toString()
			seen += r.machine.formProblems.value.toString()
			seen += r.machine.pairingIssue.value.toString()
		}
		r.machine.begin(); snap()
		r.machine.submitActivationKey(secretKey); snap()
		r.machine.submitFirstSetup(UpdateConfig(deviceName = "!")); snap()
		r.machine.submitFirstSetup(UpdateConfig()); snap()
		r.machine.resume(); snap()
		r.machine.finishAdapterStep(); snap()
		for (failure in listOf(AuthServerError.Unauthorized(), AuthServerError.Retryable("network error"), AuthServerError.Rejected("x"))) {
			r.auth.result = Result.failure(failure)
			r.machine.restart(); snap()
			r.machine.submitActivationKey(secretKey); snap()
		}
		r.discovery.result = Result.failure(IllegalStateException("boom $secretKey"))
		r.machine.restart()
		r.machine.submitActivationKey(secretKey); snap()
		assertTrue(seen.none { it.contains(secretKey) })
		assertTrue(r.machine.state.value is OnboardingState.Failed)
	}

	private fun requestSignature(request: String) = JsonParser.parseString(request).asJsonObject.get("signature").asString

	@Test
	fun retryAfterRetryablePiRefusalAsksForANewGrantNeverResubmitsTheBurnedOne() = runTest {
		val r = Rig(this)
		r.auth.freshEachTime = true
		r.enroller.outcome = EnrollOutcome(false, "grant", "replayed grant", null)
		r.toFirstSetup()
		val failed = r.machine.state.value as OnboardingState.Failed
		assertTrue(failed.retryable)
		assertEquals(1, r.auth.calls.size)
		r.enroller.outcome = EnrollOutcome(true, "enrolled", null, null)
		r.machine.retry()
		assertEquals(2, r.auth.calls.size)
		assertEquals(2, r.enroller.requests.size)
		assertNotEquals(requestSignature(r.enroller.requests[0].second), requestSignature(r.enroller.requests[1].second))
		assertEquals(1, r.discovery.calls)
		assertEquals(OnboardingState.FirstSetup, r.machine.state.value)
		assertEquals(listOf(piFp, piFp), r.enroller.pins) // the machine hands the vouched fingerprint to the transport
	}

	@Test
	fun permanentPiRefusalsAreNotRetryableAndTransientOnesAre() = runTest {
		val permanent = listOf(
			EnrollOutcome(false, "grant", "grant is for another device", null),
			EnrollOutcome(false, "grant", "grant is for another phone key", null),
			EnrollOutcome(false, "grant", "bad signature", null),
			EnrollOutcome(false, "grant", "phone key refused: x", null),
			EnrollOutcome(false, "input", "request is not UTF-8", null),
		)
		for (outcome in permanent) {
			val r = Rig(this)
			r.enroller.outcome = outcome
			r.toFirstSetup()
			assertFalse(outcome.error, (r.machine.state.value as OnboardingState.Failed).retryable)
			r.machine.retry()
			assertEquals(1, r.auth.calls.size) // retry does nothing: no second grant is requested
		}
		val transient = listOf(
			EnrollOutcome(false, "grant", "grant expired", null),
			EnrollOutcome(false, "grant", "replayed grant", null),
			EnrollOutcome(false, "grant", "grant issued in the future", null),
			EnrollOutcome(false, "io", "OSError: x", null),
			EnrollOutcome(false, "internal", "unexpected KeyError", null),
			EnrollOutcome(false, "ssh", "SSH to the Pi failed (ConnectException).", null),
		)
		for (outcome in transient) {
			val r = Rig(this)
			r.enroller.outcome = outcome
			r.toFirstSetup()
			assertTrue(outcome.error, (r.machine.state.value as OnboardingState.Failed).retryable)
		}
	}

	@Test
	fun retryAfterInstallFailureDoesNotEnrollAgain() = runTest {
		val r = Rig(this)
		r.toFirstSetup()
		r.installer.result = UpdateResult(false, "verify", null, "bad checksum")
		r.machine.submitFirstSetup(UpdateConfig())
		assertEquals(OnboardingState.Failed("installing", true, "bad checksum"), r.machine.state.value)
		r.installer.result = UpdateResult(true, "done", "2.3.0", null)
		r.machine.retry()
		assertEquals(1, r.enroller.requests.size)
		assertEquals(1, r.auth.calls.size)
		assertEquals(2, r.installer.installs.size)
		assertEquals(OnboardingState.PairingPhone, r.machine.state.value)
		assertEquals(listOf(pi, pi), r.installer.pis)
	}

	@Test
	fun downloadFailureIsReportedAsTheDownloadStepAndRetryable() = runTest {
		val r = Rig(this)
		r.toFirstSetup()
		r.installer.result = UpdateResult(false, "download", null, ReleaseUnavailable.MESSAGE)
		r.machine.submitFirstSetup(UpdateConfig())
		assertEquals(OnboardingState.Failed("download", true, ReleaseUnavailable.MESSAGE), r.machine.state.value)
		r.installer.result = UpdateResult(true, "done", "2.3.0", null)
		r.installer.note = ReleasePackageSource.USING_SAVED_NOTE
		r.machine.retry()
		assertEquals(OnboardingState.PairingPhone, r.machine.state.value)
		assertEquals(listOf(ReleasePackageSource.USING_SAVED_NOTE), r.machine.notes.value)
	}

	@Test
	fun missingPairingImplementationWaitsAtPairingPhoneAndALateAttachContinues() = runTest {
		val slot = PairingSlot()
		val r = Rig(this, slot)
		r.toFirstSetup()
		r.machine.submitFirstSetup(UpdateConfig())
		r.machine.resume()
		assertEquals(OnboardingState.PairingPhone, r.machine.state.value)
		assertEquals("Pairing is not ready yet", r.machine.pairingIssue.value)
		assertTrue(r.machine.notes.value.isEmpty()) // not skipped
		slot.attach(r.pairing)
		r.machine.resume()
		assertEquals(OnboardingState.PairAdapter, r.machine.state.value)
		assertEquals(null, r.machine.pairingIssue.value)
		assertEquals(1, r.pairing.bluetoothCalls)
		assertEquals(1, r.pairing.wifiCalls)
	}

	@Test
	fun unavailableReturnedByAnAttachedImplementationStillSkipsWithANote() = runTest {
		val slot = PairingSlot()
		val r = Rig(this, slot)
		r.pairing.bluetooth.clear()
		r.pairing.bluetooth += StepOutcome.Unavailable("no adapter")
		slot.attach(r.pairing)
		r.toFirstSetup()
		r.machine.submitFirstSetup(UpdateConfig())
		r.machine.resume()
		assertEquals(OnboardingState.PairAdapter, r.machine.state.value)
		assertTrue(r.machine.notes.value.single().contains("Bluetooth skipped"))
	}

	@Test
	fun linkageErrorsBecomeAnInternalFailureWithoutTheirText() = runTest {
		for (error in listOf<LinkageError>(NoClassDefFoundError("secret-class-text"), UnsatisfiedLinkError("secret-link-text"))) {
			val r = Rig(this)
			r.auth.throwable = error
			r.toFirstSetup()
			val failed = r.machine.state.value as OnboardingState.Failed
			assertEquals("internal", failed.step)
			assertFalse(failed.retryable)
			assertFalse(failed.message.contains("secret"))
			assertTrue(r.enroller.requests.isEmpty())
		}
	}

	@Test
	fun grantToStringRedactsTheGrantAndTheSignature() {
		val grant = Grant("{\"jti\":\"j-secret\"}", "SIGNATURE-SECRET", "pro", 1_900_000_000L)
		val text = grant.toString()
		assertFalse(text.contains("j-secret"))
		assertFalse(text.contains("SIGNATURE-SECRET"))
		assertTrue(text.contains("pro"))
		assertEquals(grant, grant.copy()) // equality still compares the real content
	}

	// ---- restart races: a real thread pool, jobs blocked on latches (the machine's blocking calls ignore cancellation) ----

	private val piA = FoundPi("192.168.4.1", Transport.MiaWifi, "SHA256:" + "A".repeat(43))
	private val piB = FoundPi("192.168.4.2", Transport.MiaWifi, "SHA256:" + "B".repeat(43))

	private inner class Threaded {
		val pool = Executors.newFixedThreadPool(4)
		val rootJob: Job = SupervisorJob()
		val scope = CoroutineScope(rootJob + pool.asCoroutineDispatcher())
		val discoveryResults = mutableListOf<List<FoundPi>>()
		val entered = CountDownLatch(1)
		val release = CountDownLatch(1)
		var blockedOutcome = EnrollOutcome(true, "enrolled", null, null)
		val enrolledHosts = java.util.Collections.synchronizedList(mutableListOf<String>())
		val installedPis = java.util.Collections.synchronizedList(mutableListOf<FoundPi>())
		val grantRefusedFor = mutableSetOf<String>()
		val store = KnownPiStore(FakeStorage())

		val machine = OnboardingMachine(
			auth = object : AuthPort {
				override fun requestGrant(activationKey: String, devicePublicFp: String, phonePublicKeyLine: String): Result<Grant> =
					if (devicePublicFp in grantRefusedFor) Result.failure(AuthServerError.UnknownDevice())
					else Result.success(Grant(grantJson, "sig-for-$devicePublicFp", "pro", 1L))
			},
			discovery = object : DiscoveryPort {
				override suspend fun find(activationKey: String): Result<List<FoundPi>> =
					Result.success(synchronized(discoveryResults) { discoveryResults.removeAt(0) })
			},
			enroller = EnrollTransport { host, _, _ ->
				enrolledHosts += host
				if (host == piA.host) { // Pi A: the call hangs until the test lets it end
					entered.countDown()
					assertTrue(release.await(10, TimeUnit.SECONDS))
					blockedOutcome
				} else EnrollOutcome(true, "enrolled", null, null)
			},
			installer = InstallPort { target, _, _, _ -> installedPis += target; UpdateResult(true, "done", "2.3.0", null) },
			pairing = FakePairing(mutableListOf(StepOutcome.Done), mutableListOf(StepOutcome.Done)),
			known = store,
			phoneKeyLine = { phoneKey },
			scope = scope,
			io = pool.asCoroutineDispatcher(),
		)

		fun awaitState(what: String, test: (OnboardingState) -> Boolean) {
			val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(10)
			while (System.nanoTime() < end) {
				if (test(machine.state.value)) return
				Thread.sleep(5)
			}
			fail("timeout waiting for $what, state is ${machine.state.value}")
		}

		/** Lets the blocked job end and waits until every job of the scope has finished. */
		fun drain() {
			release.countDown()
			runBlocking { rootJob.children.toList().forEach { it.join() } }
		}

		fun close() { release.countDown(); pool.shutdownNow() }
	}

	@Test
	fun reviewersSequenceEndsFailedAndNeverInstallsOnTheOtherPi() {
		val t = Threaded()
		try {
			t.discoveryResults += listOf(piA)
			t.discoveryResults += listOf(piB)
			t.grantRefusedFor += piB.deviceFp!!
			t.machine.begin()
			t.machine.submitActivationKey(secretKey)
			assertTrue("state ${t.machine.state.value}", t.entered.await(10, TimeUnit.SECONDS)) // the job is inside enroll(A)
			t.machine.restart()
			t.machine.submitActivationKey(secretKey) // Pi B: the server refuses the grant
			t.awaitState("Failed for B") { it is OnboardingState.Failed }
			assertFalse((t.machine.state.value as OnboardingState.Failed).retryable)
			t.drain() // the old job's enroll on A now succeeds
			assertTrue(t.machine.state.value is OnboardingState.Failed) // nothing of the old job was written
			t.machine.submitFirstSetup(UpdateConfig()) // not in FirstSetup
			t.machine.retry() // not retryable
			assertTrue(t.installedPis.isEmpty())
			assertEquals(listOf(piA.host), t.enrolledHosts.toList()) // B was never enrolled either
			assertTrue(t.store.known().isEmpty())
		} finally { t.close() }
	}

	@Test
	fun staleJobAfterRestartWritesNothingNotEvenItsFailure() {
		val t = Threaded()
		try {
			t.discoveryResults += listOf(piA)
			t.blockedOutcome = EnrollOutcome(false, "grant", "grant expired", null)
			t.machine.begin()
			t.machine.submitActivationKey(secretKey)
			assertTrue("state ${t.machine.state.value}", t.entered.await(10, TimeUnit.SECONDS))
			t.machine.restart()
			t.drain()
			assertEquals(OnboardingState.EnterActivationKey, t.machine.state.value)
			t.machine.retry() // nothing failed in this run
			assertEquals(OnboardingState.EnterActivationKey, t.machine.state.value)
		} finally { t.close() }
	}

	@Test
	fun staleSuccessCannotEnrollTheNewRunsPiForAnotherPi() {
		val t = Threaded()
		try {
			t.discoveryResults += listOf(piA)
			t.discoveryResults += listOf(piB)
			t.machine.begin()
			t.machine.submitActivationKey(secretKey)
			assertTrue("state ${t.machine.state.value}", t.entered.await(10, TimeUnit.SECONDS))
			t.machine.restart()
			t.machine.submitActivationKey(secretKey) // B enrolls normally
			t.awaitState("FirstSetup for B") { it == OnboardingState.FirstSetup }
			t.drain() // the stale A success arrives late
			assertEquals(OnboardingState.FirstSetup, t.machine.state.value)
			t.machine.submitFirstSetup(UpdateConfig())
			t.awaitState("PairingPhone") { it == OnboardingState.PairingPhone }
			assertEquals(listOf(piB), t.installedPis.toList()) // only the Pi this run enrolled
		} finally { t.close() }
	}

	@Test
	fun secondSubmitWhileTheFirstRunIsBlockedStartsNoSecondJob() {
		// A second submit while the first run is blocked must not start another job.
		val t = Threaded()
		try {
			t.discoveryResults += listOf(piA)
			t.machine.begin()
			t.machine.submitActivationKey(secretKey)
			assertTrue("state ${t.machine.state.value}", t.entered.await(10, TimeUnit.SECONDS))
			t.machine.submitActivationKey("other") // state is Authorizing: ignored
			t.machine.retry()
			t.drain()
			t.awaitState("FirstSetup") { it == OnboardingState.FirstSetup }
			assertEquals(listOf(piA.host), t.enrolledHosts.toList())
		} finally { t.close() }
	}

	// ---- release package cache ----

	private fun release(version: String, tamper: Boolean = false): ReleaseDownloader.Downloaded {
		val bundle = "bundle-$version".toByteArray()
		val digest = cz.mia.app.core.update.SchemaHash.sha256Hex(if (tamper) "other".toByteArray() else bundle)
		return ReleaseDownloader.Downloaded(bundle, "$digest  ${PackageBuilder.bundleName(version)}\n")
	}

	private fun tempDir(): File = Files.createTempDirectory("mia-release-cache").toFile().also { it.deleteOnExit() }

	@Test
	fun releaseDownloadIsSavedAndUsedWhenTheNetworkFailsLater() {
		val dir = tempDir()
		val online = ReleasePackageSource(dir) { release(it) }.obtain("2.3.0")
		assertEquals(null, online.note)
		var calls = 0
		val offline = ReleasePackageSource(dir) { calls++; throw java.io.IOException("secret-url") }
		val got = offline.obtain("2.3.0")
		assertEquals(1, calls)
		assertEquals(ReleasePackageSource.USING_SAVED_NOTE, got.note)
		assertTrue(online.release.bundle.contentEquals(got.release.bundle))
	}

	@Test
	fun noNetworkAndNoSavedCopyForThatVersionIsAReadableFailure() {
		val dir = tempDir()
		ReleasePackageSource(dir) { release(it) }.obtain("2.3.0")
		val offline = ReleasePackageSource(dir) { throw java.io.IOException("secret-url") }
		try {
			offline.obtain("2.4.0") // only 2.3.0 is saved
			fail("expected ReleaseUnavailable")
		} catch (e: ReleaseUnavailable) {
			assertEquals("The release package cannot be downloaded and none is saved on this phone", e.message)
			assertFalse(e.message!!.contains("secret-url"))
		}
	}

	@Test
	fun aTamperedSavedCopyIsNotUsedAndIsDropped() {
		val dir = tempDir()
		ReleasePackageSource(dir) { release(it) }.obtain("2.3.0")
		File(dir, "release-2.3.0/bundle.tar.gz").writeBytes("tampered".toByteArray())
		val offline = ReleasePackageSource(dir) { throw java.io.IOException("down") }
		try {
			offline.obtain("2.3.0")
			fail("expected ReleaseUnavailable")
		} catch (_: ReleaseUnavailable) {
		}
		assertFalse(File(dir, "release-2.3.0").exists())
	}

	@Test
	fun aDownloadThatFailsItsChecksumIsRefusedAndNeverSaved() {
		val dir = tempDir()
		try {
			ReleasePackageSource(dir) { release(it, tamper = true) }.obtain("2.3.0")
			fail("expected UpdateRefused")
		} catch (_: cz.mia.app.core.update.UpdateRefused) {
		}
		assertFalse(File(dir, "release-2.3.0").exists())
	}

	@Test
	fun aVersionThatIsNotAReleaseNumberNeverTouchesThePath() {
		val dir = tempDir()
		try {
			ReleasePackageSource(dir) { release("1.0.0") }.obtain("../../etc")
			fail("expected UpdateRefused")
		} catch (_: cz.mia.app.core.update.UpdateRefused) {
		}
	}

	private fun schemaFile(): File {
		var dir: File? = File(System.getProperty("user.dir")).absoluteFile
		while (dir != null) {
			val f = File(dir, "schemas/json/mia-user-config.schema.json")
			if (f.isFile) return f
			dir = dir.parentFile
		}
		error("schemas/json/mia-user-config.schema.json not found above ${System.getProperty("user.dir")}")
	}

	/** The subset UpdateConfig.toYaml writes: `key: value` lines, `key:` opening a section of two-space-indented lines. */
	private fun parseYaml(text: String): Map<String, Any> {
		val root = linkedMapOf<String, Any>()
		var section: MutableMap<String, Any>? = null
		for (line in text.lines().filter { it.isNotBlank() }) {
			val indented = line.startsWith("  ")
			val key = line.trim().substringBefore(':')
			val raw = line.trim().substringAfter(':').trim()
			if (!indented && raw.isEmpty()) {
				section = linkedMapOf<String, Any>().also { root[key] = it }
				continue
			}
			val value: Any = when {
				raw.startsWith("\"") -> JsonParser.parseString(raw).asString
				raw == "true" || raw == "false" -> raw.toBoolean()
				else -> raw.toInt()
			}
			if (indented) section!![key] = value else { root[key] = value; section = null }
		}
		return root
	}

	private fun checkScalar(rule: com.google.gson.JsonObject, value: Any?) {
		rule.get("const")?.let { assertEquals(it.asInt, value) }
		when (rule.get("type")?.asString) {
			"string" -> {
				val s = value as String
				rule.get("minLength")?.let { assertTrue(s.length >= it.asInt) }
				rule.get("maxLength")?.let { assertTrue(s.length <= it.asInt) }
				rule.get("pattern")?.let { assertTrue(Regex(it.asString).containsMatchIn(s)) }
				rule.getAsJsonArray("enum")?.let { e -> assertTrue(e.any { it.asString == s }) }
			}
			"integer" -> {
				val n = value as Int
				rule.get("minimum")?.let { assertTrue(n >= it.asInt) }
				rule.get("maximum")?.let { assertTrue(n <= it.asInt) }
			}
			"boolean" -> assertTrue(value is Boolean)
		}
	}
}
