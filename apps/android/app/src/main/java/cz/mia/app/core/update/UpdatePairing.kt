package cz.mia.app.core.update

import com.google.gson.Gson
import com.google.gson.JsonObject
import java.io.IOException
import okhttp3.OkHttpClient
import okhttp3.Request

/**
 * Pairing is an administrator action on the Pi (ADR-0023, REQ-UPD-004): a paired key is root there by design, so the
 * API has no way to add one. The app shows the command to run over an SSH session, and can list what is paired.
 */
class UpdatePairing(private val client: OkHttpClient = OkHttpClient(), private val gson: Gson = Gson()) {
	/** The label is shell-safe by construction; the key is a bare OpenSSH line without quotes. */
	fun command(label: String, publicLine: String): String {
		require(LABEL.matches(label)) { "label must be 1-32 characters of A-Z a-z 0-9 . _ -" }
		require(!publicLine.contains('\'') && !publicLine.contains('\n')) { "not a plain public key line" }
		return "sudo /opt/mia/bin/mia-update-pair add $label '$publicLine'"
	}

	/** Read-only: `GET /admin/update/pair` with an admin-scope API key. Returns "label fingerprint" lines. */
	fun paired(apiBaseUrl: String, apiKey: String): Result<List<String>> = try {
		val request = Request.Builder()
			.url(apiBaseUrl.trimEnd('/') + "/admin/update/pair")
			.header("X-API-Key", apiKey)
			.get()
			.build()
		client.newCall(request).execute().use { response ->
			when {
				response.isSuccessful -> {
					val phones = gson.fromJson(response.body?.string().orEmpty(), JsonObject::class.java)
						.getAsJsonArray("phones")
					Result.success(phones.map { it.asJsonObject.let { p -> "${p["label"].asString} ${p["fingerprint"].asString}" } })
				}
				response.code == 403 -> Result.failure(IOException("The API key lacks the admin scope"))
				else -> Result.failure(IOException("The Pi refused the request (${response.code})"))
			}
		}
	} catch (e: IOException) {
		Result.failure(e)
	}

	companion object {
		private val LABEL = Regex("^[A-Za-z0-9._-]{1,32}$")
	}
}
