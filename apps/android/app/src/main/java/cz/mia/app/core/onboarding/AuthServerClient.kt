package cz.mia.app.core.onboarding

import com.google.gson.Gson
import com.google.gson.JsonObject
import java.io.IOException
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody

/** A server-signed grant: [json] and [signature] are forwarded to the Pi unchanged (the exact bytes are signed). */
data class Grant(val json: String, val signature: String, val plan: String, val entitlementExp: Long)

/** A Pi registered to the account; [fp] is the OpenSSH form `SHA256:<base64>`. */
data class DeviceRef(val fp: String, val label: String)

/**
 * Failures of [AuthServerClient]. The messages are shown to the user, so they are readable and never contain the
 * activation key, a URL or a response body.
 */
sealed class AuthServerError(message: String) : Exception(message) {
	/** 401: the activation key was not accepted. */
	class Unauthorized : AuthServerError("The activation key was not accepted. Check the key in the app settings.")

	/** 403: the server does not know this Pi for the account. */
	class UnknownDevice : AuthServerError("This Pi is not registered to your account.")

	/** Network failure, timeout or a 5xx from the server; trying again later may work. */
	class Retryable(detail: String) : AuthServerError("The MIA server cannot be reached right now ($detail). Try again.")

	/** The server answered, but not as ADR-0025 defines, or the client was configured unsafely. */
	class Rejected(detail: String) : AuthServerError("The MIA server request failed: $detail.")
}

/**
 * Client for the auth server contract of ADR-0025 (REQ-ONB-008): `POST /v1/grants`, `GET /v1/devices`,
 * `POST /v1/checkout`. The activation key travels only in the `Authorization: Bearer` header. Nothing is logged and
 * no method throws; every failure is an [AuthServerError] inside the [Result].
 */
class AuthServerClient(baseUrl: String, private val client: OkHttpClient, private val gson: Gson = Gson()) {
	private val base: HttpUrl? = baseUrl.trim().toHttpUrlOrNull()?.takeIf { isAllowed(it) }

	fun requestGrant(activationKey: String, devicePublicFp: String, phonePublicKeyLine: String): Result<Grant> {
		val body = JsonObject().apply {
			addProperty("device_fp", devicePublicFp)
			addProperty("phone_public_key", phonePublicKeyLine)
		}
		return call(activationKey, "v1/grants", post(gson.toJson(body))) { text ->
			val root = gson.fromJson(text, JsonObject::class.java)
			val grantJson = root.stringOrNull("grant")
			val signature = root.stringOrNull("signature")
			if (grantJson == null || signature == null) throw bad("grant response lacks grant or signature")
			val claims = try {
				gson.fromJson(grantJson, JsonObject::class.java)
			} catch (e: RuntimeException) {
				throw bad("grant is not JSON")
			}
			val plan = claims.stringOrNull("plan")
			val exp = claims?.get("entitlement_exp")?.takeIf { it.isJsonPrimitive && it.asJsonPrimitive.isNumber }?.asLong
			if (plan == null || exp == null) throw bad("grant lacks plan or entitlement_exp")
			Grant(grantJson, signature, plan, exp)
		}
	}

	fun devices(activationKey: String): Result<List<DeviceRef>> =
		call(activationKey, "v1/devices", null) { text ->
			val array = gson.fromJson(text, JsonObject::class.java).getAsJsonArray("devices")
				?: throw bad("device list missing")
			array.map { element ->
				val device = element.asJsonObject
				val fp = device.stringOrNull("fp") ?: throw bad("device without fp")
				DeviceRef(fp, device.stringOrNull("label").orEmpty())
			}
		}

	/** The hosted payment page the server returns; the app only opens it in the browser. */
	fun checkoutUrl(activationKey: String): Result<String> =
		call(activationKey, "v1/checkout", post("{}")) { text ->
			val url = gson.fromJson(text, JsonObject::class.java).stringOrNull("url")
			if (url == null || url.toHttpUrlOrNull()?.isHttps != true) throw bad("checkout URL missing or not https")
			url
		}

	private fun post(json: String): RequestBody = json.toRequestBody(JSON)

	private fun bad(detail: String) = AuthServerError.Rejected(detail)

	private fun JsonObject?.stringOrNull(name: String): String? =
		this?.get(name)?.takeIf { it.isJsonPrimitive && it.asJsonPrimitive.isString }?.asString

	private fun <T> call(activationKey: String, path: String, body: RequestBody?, parse: (String) -> T): Result<T> {
		val root = base ?: return Result.failure(bad("the server address must be https"))
		return try {
			val builder = Request.Builder()
				.url(root.newBuilder().addPathSegments(path).build())
				.header("Authorization", "Bearer $activationKey")
			val request = if (body == null) builder.get().build() else builder.post(body).build()
			client.newCall(request).execute().use { response ->
				when {
					response.code == 401 -> Result.failure(AuthServerError.Unauthorized())
					response.code == 403 -> Result.failure(AuthServerError.UnknownDevice())
					response.code >= 500 -> Result.failure(AuthServerError.Retryable("server error ${response.code}"))
					!response.isSuccessful -> Result.failure(bad("unexpected status ${response.code}"))
					else -> Result.success(parse(response.body?.string().orEmpty()))
				}
			}
		} catch (e: AuthServerError) {
			Result.failure(e)
		} catch (e: IOException) {
			Result.failure(AuthServerError.Retryable("network error"))
		} catch (e: RuntimeException) {
			// Malformed JSON, or an activation key that is not a legal header value; never echo the cause.
			Result.failure(bad("unreadable response or invalid request"))
		}
	}

	private companion object {
		val JSON = "application/json".toMediaType()
		val LOCAL_HOSTS = setOf("localhost", "127.0.0.1", "10.0.2.2")

		/** https always; plain http only for the local test server. */
		fun isAllowed(url: HttpUrl): Boolean = url.isHttps || url.host in LOCAL_HOSTS
	}
}
