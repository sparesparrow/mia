package cz.mia.app.core.networking

// @req REQ-AND-018

import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PiRequestInterceptorTest {

    private val defaultBase = "http://10.0.2.2:8000/"
    private val piConnection = PiConnection("http://192.168.1.50:8000/", "ws://192.168.1.50:8000", "secret")

    /** The request that reaches the network after the interceptor has run. */
    private fun sent(connection: PiConnection, url: String): Request {
        val chain = mockk<Interceptor.Chain>()
        val proceeded = slot<Request>()
        every { chain.request() } returns Request.Builder().url(url).build()
        every { chain.proceed(capture(proceeded)) } returns mockk<Response>(relaxed = true)
        PiRequestInterceptor(defaultBase) { connection }.intercept(chain)
        return proceeded.captured
    }

    @Test
    fun `with no address entered a call keeps its URL and carries no key`() {
        val defaults = PiConnection(defaultBase, "ws://10.0.2.2:8000", "")

        val request = sent(defaults, "http://10.0.2.2:8000/api/v1/devices")

        assertEquals("http://10.0.2.2:8000/api/v1/devices", request.url.toString())
        assertNull(request.header("X-API-Key"))
    }

    @Test
    fun `a call for the build's default host goes to the Pi that was entered, with the key`() {
        val request = sent(piConnection, "http://10.0.2.2:8000/api/v1/devices?limit=5")

        assertEquals("http://192.168.1.50:8000/api/v1/devices?limit=5", request.url.toString())
        assertEquals("secret", request.header("X-API-Key"))
    }

    @Test
    fun `the scheme and port follow the entered address`() {
        val secure = PiConnection("https://pi.example:8443/", "wss://pi.example:8443", "secret")

        val request = sent(secure, "http://10.0.2.2:8000/status")

        assertEquals("https://pi.example:8443/status", request.url.toString())
        assertEquals("secret", request.header("X-API-Key"))
    }

    @Test
    fun `a call to any other host is left alone and never carries the key`() {
        val request = sent(piConnection, "https://example.org/elsewhere")

        assertEquals("https://example.org/elsewhere", request.url.toString())
        assertNull(request.header("X-API-Key"))
    }

    @Test
    fun `a blank key adds no header`() {
        val noKey = piConnection.copy(apiKey = "")

        assertNull(sent(noKey, "http://10.0.2.2:8000/status").header("X-API-Key"))
    }
}
