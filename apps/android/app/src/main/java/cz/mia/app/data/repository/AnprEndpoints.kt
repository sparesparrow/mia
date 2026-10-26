package cz.mia.app.data.repository

import cz.mia.app.core.networking.PiConnection
import okhttp3.Request
import okhttp3.RequestBody

/**
 * The requests for the Pi's plate check (`/anpr/...`), built for the Pi entered in Settings and carrying its key
 * (REQ-AND-018). The Pi answers with plates in clear for the vignette check; the app shows them and stores none.
 */
object AnprEndpoints {
	fun capture(target: PiConnection, body: RequestBody): Request = post(target, "/anpr/capture", body)

	fun process(target: PiConnection, body: RequestBody): Request = post(target, "/anpr/process", body)

	fun history(target: PiConnection, limit: Int, offset: Int): Request =
		get(target, "/anpr/history?limit=$limit&offset=$offset")

	fun alerts(target: PiConnection, limit: Int): Request = get(target, "/anpr/alerts?limit=$limit")

	fun stream(target: PiConnection): Request =
		authorised(target, Request.Builder().url("${target.wsBaseUrl.trimEnd('/')}/anpr/stream")).build()

	private fun get(target: PiConnection, path: String): Request =
		authorised(target, Request.Builder().url(target.apiBaseUrl.trimEnd('/') + path).get()).build()

	private fun post(target: PiConnection, path: String, body: RequestBody): Request =
		authorised(target, Request.Builder().url(target.apiBaseUrl.trimEnd('/') + path).post(body)).build()

	private fun authorised(target: PiConnection, builder: Request.Builder): Request.Builder =
		builder.apply { target.authHeaders().forEach { (name, value) -> header(name, value) } }
}
