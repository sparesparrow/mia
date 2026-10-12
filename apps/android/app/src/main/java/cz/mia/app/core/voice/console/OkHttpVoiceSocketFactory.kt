package cz.mia.app.core.voice.console

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import okio.ByteString.Companion.toByteString
import java.util.concurrent.TimeUnit

/** [VoiceSocketFactory] on OkHttp. The shared client's 30 s read timeout would drop an idle console, so it is lifted. */
class OkHttpVoiceSocketFactory(client: OkHttpClient) : VoiceSocketFactory {
    private val client = client.newBuilder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    override fun open(url: String, headers: Map<String, String>, listener: VoiceSocketListener): VoiceSocket {
        val request = Request.Builder().url(url).apply { headers.forEach { (name, value) -> header(name, value) } }.build()
        val socket = client.newWebSocket(
            request,
            object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) = listener.onOpen()

                override fun onMessage(webSocket: WebSocket, bytes: ByteString) = listener.onMessage(bytes.toByteArray())

                // Envelopes are binary; a text frame is not one of ours and is ignored.
                override fun onMessage(webSocket: WebSocket, text: String) = Unit

                override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                    webSocket.close(code, reason)
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = listener.onClosed()

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) =
                    listener.onFailure(t.message ?: t.javaClass.simpleName)
            },
        )
        return object : VoiceSocket {
            override fun send(data: ByteArray): Boolean = socket.send(data.toByteString())
            override fun close() {
                socket.close(1000, "console closed")
            }
        }
    }
}
