package cz.mia.app.core.onboarding

// @req REQ-ONB-008

import com.google.gson.Gson
import com.google.gson.JsonObject
import java.io.ByteArrayOutputStream
import java.io.PrintStream
import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AuthServerClientTest {
	private val activationKey = "act-SECRET-0123456789"
	private val deviceFp = "SHA256:abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"
	private val otherFp = "SHA256:" + "b".repeat(43)
	private val phoneKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeFakeFakeFakeFakeFakeFakeFakeFakeFake phone"
	private val grantJson = """{"v":1,"account_id":"acc1","jti":"j-1","device_fp":"$deviceFp","phone_fp":"SHA256:phone","plan":"pro","entitlement_exp":1900000000,"iat":1,"exp":2,"extra":true}"""
	private val signature = "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"

	private lateinit var server: MockWebServer
	private lateinit var http: OkHttpClient

	@Before
	fun setUp() {
		server = MockWebServer().also { it.start() }
		http = OkHttpClient.Builder()
			.connectTimeout(2, TimeUnit.SECONDS)
			.readTimeout(2, TimeUnit.SECONDS)
			.build()
	}

	@After
	fun tearDown() {
		runCatching { server.shutdown() }
	}

	/** The client under test, pointed at the fake server (loopback, plain http allowed only there). */
	private fun client() = AuthServerClient("http://127.0.0.1:${server.port}", http)

	private fun json(body: String, code: Int = 200) =
		MockResponse().setResponseCode(code).setHeader("Content-Type", "application/json").setBody(body)

	private fun grantResponse(): MockResponse {
		val body = JsonObject().apply {
			addProperty("grant", grantJson)
			addProperty("signature", signature)
		}
		return json(Gson().toJson(body))
	}

	@Test
	fun grantIsReturnedForValidActivationKey() {
		server.enqueue(grantResponse())
		val grant = client().requestGrant(activationKey, deviceFp, phoneKey).getOrThrow()
		assertEquals(grantJson, grant.json)
		assertEquals(signature, grant.signature)
		assertEquals("pro", grant.plan)
		assertEquals(1900000000L, grant.entitlementExp)

		val request = server.takeRequest(2, TimeUnit.SECONDS)!!
		assertEquals("POST", request.method)
		assertEquals("/v1/grants", request.path)
		assertEquals("Bearer $activationKey", request.getHeader("Authorization"))
		val sent = Gson().fromJson(request.body.readUtf8(), JsonObject::class.java)
		assertEquals(deviceFp, sent["device_fp"].asString)
		assertEquals(phoneKey, sent["phone_public_key"].asString)
		assertFalse(sent.toString().contains(activationKey))
	}

	@Test
	fun unauthorizedKeyGivesReadableError() {
		server.enqueue(json("{}", 401))
		val error = client().requestGrant(activationKey, deviceFp, phoneKey).exceptionOrNull()
		assertTrue(error is AuthServerError.Unauthorized)
		assertTrue(error!!.message!!.contains("activation key"))
	}

	@Test
	fun unknownDeviceGives403Error() {
		server.enqueue(json("{}", 403))
		val error = client().requestGrant(activationKey, deviceFp, phoneKey).exceptionOrNull()
		assertTrue(error is AuthServerError.UnknownDevice)
		assertTrue(error!!.message!!.contains("not registered"))
	}

	@Test
	fun serverDownGivesRetryableError() {
		val unreachable = client()
		server.shutdown()
		val grant = unreachable.requestGrant(activationKey, deviceFp, phoneKey)
		assertTrue(grant.exceptionOrNull() is AuthServerError.Retryable)
		assertTrue(unreachable.devices(activationKey).exceptionOrNull() is AuthServerError.Retryable)
		assertTrue(unreachable.checkoutUrl(activationKey).exceptionOrNull() is AuthServerError.Retryable)
	}

	@Test
	fun serverErrorGivesRetryableError() {
		server.enqueue(json("{}", 503))
		assertTrue(client().devices(activationKey).exceptionOrNull() is AuthServerError.Retryable)
	}

	@Test
	fun requestTimeoutGivesRetryableError() {
		// Retry-After stops OkHttp from re-sending a 408 on its own. The queued 200 would give Rejected if it were used.
		server.enqueue(MockResponse().setResponseCode(408).setHeader("Retry-After", "1"))
		server.enqueue(json("{}"))
		assertTrue(client().requestGrant(activationKey, deviceFp, phoneKey).exceptionOrNull() is AuthServerError.Retryable)
	}

	@Test
	fun tooManyRequestsGivesRetryableError() {
		server.enqueue(json("{}", 429))
		assertTrue(client().devices(activationKey).exceptionOrNull() is AuthServerError.Retryable)
	}

	@Test
	fun redirectIsNotFollowed() {
		server.enqueue(MockResponse().setResponseCode(302).setHeader("Location", server.url("/elsewhere").toString()))
		// If the client followed the redirect, this grant would be served and the call would succeed.
		server.enqueue(grantResponse())
		val error = client().requestGrant(activationKey, deviceFp, phoneKey).exceptionOrNull()
		assertTrue(error is AuthServerError.Rejected)
		assertEquals(1, server.requestCount)
		assertFalse(error!!.message!!.contains(activationKey))
	}

	@Test
	fun malformedDeviceFingerprintRejectedBeforeAnyRequest() {
		val malformed = listOf(
			"SHA256:short",
			"MD5:" + "a".repeat(43),
			"SHA256:" + "a".repeat(42) + "=",
			"SHA256:" + "a".repeat(43) + "\n",
			"SHA256:" + "a".repeat(44),
		)
		malformed.forEach { fp ->
			assertTrue(client().requestGrant(activationKey, fp, phoneKey).exceptionOrNull() is AuthServerError.Rejected)
		}
		assertEquals(0, server.requestCount)
	}

	@Test
	fun malformedFingerprintInDeviceListIsRejected() {
		server.enqueue(json("""{"devices":[{"fp":"$deviceFp","label":"Audi Pi"},{"fp":"SHA256:aaa","label":"Spare"}]}"""))
		assertTrue(client().devices(activationKey).exceptionOrNull() is AuthServerError.Rejected)
	}

	@Test
	fun devicesReturnsFingerprints() {
		server.enqueue(json("""{"devices":[{"fp":"$deviceFp","label":"Audi Pi"},{"fp":"$otherFp","label":"Spare"}]}"""))
		val devices = client().devices(activationKey).getOrThrow()
		assertEquals(listOf(DeviceRef(deviceFp, "Audi Pi"), DeviceRef(otherFp, "Spare")), devices)

		val request = server.takeRequest(2, TimeUnit.SECONDS)!!
		assertEquals("GET", request.method)
		assertEquals("/v1/devices", request.path)
		assertEquals("Bearer $activationKey", request.getHeader("Authorization"))
	}

	@Test
	fun checkoutUrlReturned() {
		server.enqueue(json("""{"url":"https://checkout.stripe.com/c/pay/cs_test_1"}"""))
		assertEquals("https://checkout.stripe.com/c/pay/cs_test_1", client().checkoutUrl(activationKey).getOrThrow())

		val request = server.takeRequest(2, TimeUnit.SECONDS)!!
		assertEquals("POST", request.method)
		assertEquals("/v1/checkout", request.path)
		assertEquals("Bearer $activationKey", request.getHeader("Authorization"))
	}

	@Test
	fun activationKeyNeverLogged() {
		val outBuffer = ByteArrayOutputStream()
		val errBuffer = ByteArrayOutputStream()
		val oldOut = System.out
		val oldErr = System.err
		val messages = mutableListOf<String>()
		try {
			System.setOut(PrintStream(outBuffer, true))
			System.setErr(PrintStream(errBuffer, true))
			val c = client()
			server.enqueue(json("{}", 401))
			server.enqueue(json("{}", 403))
			server.enqueue(json("{}", 500))
			server.enqueue(json("not json"))
			server.enqueue(grantResponse())
			repeat(4) { c.requestGrant(activationKey, deviceFp, phoneKey).exceptionOrNull()?.let { e -> messages += listOfNotNull(e.message, e.cause?.message, e.toString()) } }
			c.requestGrant(activationKey, deviceFp, phoneKey).getOrThrow()
			server.shutdown()
			c.devices(activationKey).exceptionOrNull()?.let { e -> messages += listOfNotNull(e.message, e.cause?.message, e.toString()) }
		} finally {
			System.setOut(oldOut)
			System.setErr(oldErr)
		}
		assertTrue(messages.size >= 5)
		messages.forEach { assertFalse(it.contains(activationKey)) }
		assertFalse(outBuffer.toString().contains(activationKey))
		assertFalse(errBuffer.toString().contains(activationKey))
	}

	@Test
	fun plainHttpToRemoteHostRefused() {
		val remote = AuthServerClient("http://auth.example.com", http)
		val error = remote.requestGrant(activationKey, deviceFp, phoneKey).exceptionOrNull()
		assertTrue(error is AuthServerError.Rejected)
		assertTrue(error!!.message!!.contains("https"))
		assertFalse(error.message!!.contains(activationKey))
		assertEquals(0, server.requestCount)
	}
}
