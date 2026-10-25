package cz.mia.app.core.networking

// @req REQ-AND-018

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PiConnectionTest {

    private val defaults = PiConnection("http://10.0.2.2:8000/", "ws://10.0.2.2:8000", "")

    private fun valid(input: String): PiAddressResult.Valid =
        PiAddress.parse(input) as PiAddressResult.Valid

    @Test
    fun `a bare IP gets http and the Pi's port`() {
        assertEquals(PiAddressResult.Valid("http://192.168.1.50:8000/", "ws://192.168.1.50:8000"), valid("192.168.1.50"))
    }

    @Test
    fun `a typed port is kept`() {
        assertEquals(PiAddressResult.Valid("http://pi.local:9000/", "ws://pi.local:9000"), valid("pi.local:9000"))
        assertEquals(PiAddressResult.Valid("http://pi.local:80/", "ws://pi.local:80"), valid("http://pi.local:80"))
    }

    @Test
    fun `a full URL loses its path, query and trailing slash`() {
        assertEquals(
            PiAddressResult.Valid("http://pi.local:8000/", "ws://pi.local:8000"),
            valid("  http://pi.local:8000/api/v1/devices?x=1#top  "),
        )
    }

    @Test
    fun `https keeps its default port and maps to wss`() {
        assertEquals(PiAddressResult.Valid("https://pi.example/", "wss://pi.example"), valid("https://pi.example"))
        assertEquals(
            PiAddressResult.Valid("https://pi.example:8443/", "wss://pi.example:8443"),
            valid("https://pi.example:8443"),
        )
    }

    @Test
    fun `ws and wss are read as http and https`() {
        assertEquals(PiAddressResult.Valid("http://pi.local:8000/", "ws://pi.local:8000"), valid("ws://pi.local"))
        assertEquals(PiAddressResult.Valid("https://pi.example/", "wss://pi.example"), valid("WSS://pi.example"))
    }

    @Test
    fun `an IPv6 literal keeps its brackets`() {
        assertEquals(PiAddressResult.Valid("http://[fd00::1]:8000/", "ws://[fd00::1]:8000"), valid("[fd00::1]"))
    }

    @Test
    fun `nothing usable is refused with a reason`() {
        for (input in listOf("", "   ", "http://", "ftp://pi.local", "pi local", "http://pi.local:99999")) {
            val result = PiAddress.parse(input)
            assertTrue("'$input' should be refused", result is PiAddressResult.Invalid)
            assertTrue((result as PiAddressResult.Invalid).reason.isNotBlank())
        }
    }

    @Test
    fun `a blank address means the build defaults, even with a key typed`() {
        assertEquals(defaults, resolvePiConnection("", "secret", defaults))
        assertEquals(defaults, resolvePiConnection("   ", "secret", defaults))
    }

    @Test
    fun `an address and key become the connection, with the key trimmed`() {
        assertEquals(
            PiConnection("http://192.168.1.50:8000/", "ws://192.168.1.50:8000", "secret"),
            resolvePiConnection("192.168.1.50", "  secret \n", defaults),
        )
    }

    @Test
    fun `a stored address that no longer parses falls back to the defaults instead of half applying`() {
        assertEquals(defaults, resolvePiConnection("ftp://pi.local", "secret", defaults))
    }

    @Test
    fun `the key goes in the X-API-Key header and nowhere else`() {
        assertEquals(mapOf("X-API-Key" to "abc"), PiConnection("http://h/", "ws://h", "abc").authHeaders())
        assertEquals(emptyMap<String, String>(), PiConnection("http://h/", "ws://h", "").authHeaders())
        assertEquals(emptyMap<String, String>(), PiConnection.headersFor("   "))
    }

    @Test
    fun `printing a connection never prints the key`() {
        val text = PiConnection("http://h/", "ws://h", "super-secret-key").toString()

        assertFalse(text.contains("super-secret-key"))
        assertTrue(text.contains("apiKey=set"))
        assertTrue(PiConnection("http://h/", "ws://h", "").toString().contains("apiKey=none"))
    }
}
