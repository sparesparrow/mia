package cz.mia.app.core.update

import java.io.IOException
import okhttp3.OkHttpClient
import okhttp3.Request

/** Downloads the backend bundle and SHA256SUMS.txt (the release workflow's checksum file) of one release tag from GitHub (ADR-0023). */
class ReleaseDownloader(
	private val client: OkHttpClient = OkHttpClient(),
	private val baseUrl: String = "https://github.com/sparesparrow/mia/releases/download",
) {
	class Downloaded(val bundle: ByteArray, val sha256sums: String)

	@Throws(IOException::class)
	fun download(version: String): Downloaded {
		val tag = "v$version"
		return Downloaded(
			bundle = get("$baseUrl/$tag/${PackageBuilder.bundleName(version)}"),
			sha256sums = String(get("$baseUrl/$tag/SHA256SUMS.txt"), Charsets.UTF_8),
		)
	}

	private fun get(url: String): ByteArray {
		client.newCall(Request.Builder().url(url).build()).execute().use { response ->
			if (!response.isSuccessful) throw IOException("Download failed (${response.code}): $url")
			return response.body?.bytes() ?: throw IOException("Empty download: $url")
		}
	}
}
