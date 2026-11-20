package cz.mia.app.core.update

import com.google.gson.Gson
import java.io.IOException
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

/** Sends the phone's public key to the Pi's admin endpoint (REQ-UPD-004). Needs an API key with the admin scope. */
class UpdatePairing(private val client: OkHttpClient = OkHttpClient(), private val gson: Gson = Gson()) {
	fun pair(apiBaseUrl: String, apiKey: String, publicLine: String, label: String): Result<String> = try {
		val body = gson.toJson(mapOf("public_key" to publicLine, "label" to label))
			.toRequestBody("application/json".toMediaType())
		val request = Request.Builder()
			.url(apiBaseUrl.trimEnd('/') + "/admin/update/pair")
			.header("X-API-Key", apiKey)
			.post(body)
			.build()
		client.newCall(request).execute().use { response ->
			when {
				response.isSuccessful -> Result.success("Paired as $label")
				response.code == 403 -> Result.failure(IOException("The API key lacks the admin scope"))
				else -> Result.failure(IOException("The Pi refused pairing (${response.code})"))
			}
		}
	} catch (e: IOException) {
		Result.failure(e)
	}
}
