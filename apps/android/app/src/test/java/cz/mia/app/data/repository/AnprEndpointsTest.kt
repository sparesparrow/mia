package cz.mia.app.data.repository

// @req REQ-AND-018

import cz.mia.app.core.networking.PiConnection
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AnprEndpointsTest {
	private val pi = PiConnection("http://192.168.1.50:8000/", "ws://192.168.1.50:8000", "secret-key")
	private val body = "{}".toRequestBody("application/json".toMediaType())

	@Test
	fun `every plate-check request goes to the Pi from Settings with its key`() {
		val requests = listOf(
			AnprEndpoints.capture(pi, body),
			AnprEndpoints.process(pi, body),
			AnprEndpoints.history(pi, 50, 0),
			AnprEndpoints.alerts(pi, 20),
			AnprEndpoints.stream(pi),
		)
		for (request in requests) {
			assertEquals("192.168.1.50", request.url.host)
			assertEquals(8000, request.url.port)
			assertEquals("secret-key", request.header(PiConnection.API_KEY_HEADER))
		}
		assertEquals(
			listOf("/anpr/capture", "/anpr/process", "/anpr/history", "/anpr/alerts", "/anpr/stream"),
			requests.map { it.url.encodedPath },
		)
		assertEquals("50", requests[2].url.queryParameter("limit"))
		assertEquals("POST", requests[0].method)
		assertEquals("GET", requests[3].method)
	}

	@Test
	fun `without a key no header is sent`() {
		val open = pi.copy(apiKey = "")
		assertNull(AnprEndpoints.history(open, 10, 0).header(PiConnection.API_KEY_HEADER))
		assertNull(AnprEndpoints.stream(open).header(PiConnection.API_KEY_HEADER))
	}
}
