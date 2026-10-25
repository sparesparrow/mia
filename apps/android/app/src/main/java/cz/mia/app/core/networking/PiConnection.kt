package cz.mia.app.core.networking

import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

/**
 * Where the app reaches the Pi and the key it shows there. The two always travel together, so the
 * key is never sent to a host the user did not enter alongside it.
 */
data class PiConnection(
    val apiBaseUrl: String,
    val wsBaseUrl: String,
    val apiKey: String,
) {
    /** The only header the Pi reads a key from; a key in a URL ends up in logs (REQ-SEC-001). */
    fun authHeaders(): Map<String, String> = headersFor(apiKey)

    /** Never prints the key, so a log line or a crash report cannot leak it. */
    override fun toString(): String =
        "PiConnection(apiBaseUrl=$apiBaseUrl, wsBaseUrl=$wsBaseUrl, apiKey=${if (apiKey.isBlank()) "none" else "set"})"

    companion object {
        const val API_KEY_HEADER = "X-API-Key"

        /** No key, no header. */
        fun headersFor(apiKey: String): Map<String, String> =
            if (apiKey.isBlank()) emptyMap() else mapOf(API_KEY_HEADER to apiKey)
    }
}

/** What a typed Pi address turns into, or why it was refused. */
sealed class PiAddressResult {
    data class Valid(val apiBaseUrl: String, val wsBaseUrl: String) : PiAddressResult()
    data class Invalid(val reason: String) : PiAddressResult()
}

object PiAddress {
    /** The port the Pi's FastAPI gateway listens on when the address names none. */
    const val DEFAULT_PORT = 8000

    /**
     * Accepts `192.168.1.50`, `pi.local:8000`, `http://pi.local:8000/` and `https://pi.example`.
     * `ws://` and `wss://` are read as `http://` and `https://`. A path, query or fragment is dropped.
     */
    fun parse(input: String): PiAddressResult {
        val text = input.trim()
        if (text.isEmpty()) return PiAddressResult.Invalid("Enter the Pi's address")

        val withScheme = when {
            text.startsWith("ws://", ignoreCase = true) -> "http://" + text.substring(5)
            text.startsWith("wss://", ignoreCase = true) -> "https://" + text.substring(6)
            "://" in text -> text
            else -> "http://$text"
        }
        val url = withScheme.toHttpUrlOrNull()
            ?: return PiAddressResult.Invalid("Not a valid address")

        // OkHttp reports the scheme's default port (80, 443) when none was typed, so look at the text.
        val portTyped = Regex("""^[a-z]+://(\[[^\]]+\]|[^/:?#]+):\d+""", RegexOption.IGNORE_CASE)
            .containsMatchIn(withScheme)
        val secure = url.scheme == "https"
        val port = when {
            portTyped -> url.port
            secure -> url.port
            else -> DEFAULT_PORT
        }
        val host = if (':' in url.host) "[${url.host}]" else url.host
        val authority = if (!portTyped && secure) host else "$host:$port"
        return PiAddressResult.Valid(
            apiBaseUrl = "${url.scheme}://$authority/",
            wsBaseUrl = "${if (secure) "wss" else "ws"}://$authority",
        )
    }
}

/**
 * The connection the app uses: the address and key the user entered, or the build's defaults when
 * no address was entered or the stored one no longer parses. A key without an address is ignored,
 * because the key must only go where the user sent it.
 */
fun resolvePiConnection(address: String, apiKey: String, defaults: PiConnection): PiConnection {
    if (address.isBlank()) return defaults
    val valid = PiAddress.parse(address) as? PiAddressResult.Valid ?: return defaults
    return PiConnection(valid.apiBaseUrl, valid.wsBaseUrl, apiKey.trim())
}
