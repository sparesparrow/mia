package cz.mia.app.core.networking

import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.Response

/**
 * Sends the REST calls Retrofit built for the build's default host to the Pi the user entered, and
 * adds the API key to calls that end up at the connection's host. Calls to any other host pass
 * through untouched and never carry the key.
 */
class PiRequestInterceptor(
    private val defaultBaseUrl: String,
    private val connection: () -> PiConnection,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val target = connection()
        val targetUrl = target.apiBaseUrl.toHttpUrl()
        val defaultHost = defaultBaseUrl.toHttpUrl().host

        val original = chain.request()
        val builder = original.newBuilder()
        var url = original.url
        if (url.host == defaultHost) {
            url = url.newBuilder().scheme(targetUrl.scheme).host(targetUrl.host).port(targetUrl.port).build()
            builder.url(url)
        }
        if (url.host == targetUrl.host && target.apiKey.isNotBlank()) {
            builder.header(PiConnection.API_KEY_HEADER, target.apiKey)
        }
        return chain.proceed(builder.build())
    }
}
