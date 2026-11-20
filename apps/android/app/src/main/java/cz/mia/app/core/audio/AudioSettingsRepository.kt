package cz.mia.app.core.audio

import cz.mia.app.core.networking.PiConnectionProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

/** Reads and changes the audio settings on the Pi (`/audio/settings`). The shared client adds the API key. */
@Singleton
class AudioSettingsRepository @Inject constructor(
    private val client: OkHttpClient,
    private val piConnection: PiConnectionProvider,
) {
    private fun url() = piConnection.current().apiBaseUrl.trimEnd('/') + "/audio/settings"

    suspend fun load(): AudioSettingsResult = call(Request.Builder().url(url()).get().build())

    suspend fun change(mic: MicTransport?, reply: ReplyOutput?): AudioSettingsResult {
        val body = AudioSettingsCodec.updateBody(mic, reply).toRequestBody("application/json".toMediaType())
        return call(Request.Builder().url(url()).put(body).build())
    }

    private suspend fun call(request: Request): AudioSettingsResult = withContext(Dispatchers.IO) {
        try {
            client.newCall(request).execute().use { response ->
                val text = response.body?.string().orEmpty()
                when {
                    response.code == 409 -> AudioSettingsResult.Unavailable
                    !response.isSuccessful -> AudioSettingsResult.Failed("The Pi answered ${response.code}")
                    else -> AudioSettingsCodec.parse(text)?.let { AudioSettingsResult.Ok(it) }
                        ?: AudioSettingsResult.Failed("The Pi's answer was not understood")
                }
            }
        } catch (e: java.io.IOException) {
            AudioSettingsResult.Failed(e.message ?: "Could not reach the Pi")
        }
    }
}
