package cz.mia.app.core.background

import android.content.Context
import com.google.gson.Gson
import cz.mia.app.core.networking.MdnsDiscovery
import cz.mia.app.core.storage.PreferencesRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import org.eclipse.paho.android.service.MqttAndroidClient
import org.eclipse.paho.client.mqttv3.IMqttActionListener
import org.eclipse.paho.client.mqttv3.IMqttToken
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttException

interface MQTTManager {
	suspend fun connect()
	suspend fun disconnect()
	suspend fun publishVehicleTelemetry(obdData: OBDData)
	suspend fun publishAlert(alert: VehicleAlert)
	suspend fun publishAnprEvent(event: ANPREvent)
	suspend fun publishHealth(ping: HealthPing)
	suspend fun publishMetrics(payload: MetricsPayload)
}

@Singleton
class MQTTManagerImpl @Inject constructor(
	@ApplicationContext private val context: Context,
	private val prefs: PreferencesRepository,
	private val gson: Gson,
	private val mdns: MdnsDiscovery
) : MQTTManager {
	@Volatile private var client: MqttAndroidClient? = null
	private val envBrokerUrl: String? = System.getenv("MIA_MQTT_URL")
	private val defaultBrokerUrl: String = "tcp://test.mosquitto.org:1883"
	private val clientId: String = "mia-android-" + android.os.Build.SERIAL

	override suspend fun connect() = withContext(Dispatchers.IO) {
		if (client?.isConnected == true) return@withContext
		val discoveredPairs = mdns.discoverMqtt(timeoutMs = 2500)
		val mdnsUrls = discoveredPairs.map { pair ->
			val parts = pair.split(":")
			val host = parts.getOrNull(0) ?: return@map defaultBrokerUrl
			val port = (parts.getOrNull(1) ?: "1883")
			"tcp://$host:$port"
		}
		val cached = mdns.discoverServices("_mqtt._tcp.local.").map { host -> "tcp://$host:1883" }
		val candidates = buildList {
			envBrokerUrl?.let { add(it) }
			addAll(mdnsUrls)
			addAll(cached)
			add(defaultBrokerUrl)
		}.distinct()

		val options = MqttConnectOptions().apply {
			isAutomaticReconnect = true
			isCleanSession = true
			connectionTimeout = 10
			keepAliveInterval = 30
		}

		val backoffMs = listOf(0L, 2000L, 5000L, 10000L)
		var connected = false

		loop@ for (delayMs in backoffMs) {
			if (delayMs > 0) delay(delayMs)
			for (url in candidates) {
				try {
					val c = MqttAndroidClient(context, url, clientId)
					val token: IMqttToken = c.connect(options)
					token.actionCallback = object : IMqttActionListener {
						override fun onSuccess(asyncActionToken: IMqttToken?) { }
						override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) { }
					}
					client = c
					connected = true
					break@loop
				} catch (e: MqttException) {
					// try next candidate or back off
				}
			}
		}
	}

	override suspend fun disconnect() = withContext(Dispatchers.IO) {
		try { client?.disconnect(); client = null } catch (_: Exception) {}
	}

	private suspend fun vin(): String = prefs.vin().first()

	private suspend fun publish(topic: String, payload: String, retained: Boolean) = withContext(Dispatchers.IO) {
		val bytes = payload.toByteArray(Charsets.UTF_8)
		try { client?.publish(topic, bytes, /*qos*/0, retained) } catch (_: Exception) {}
	}

	override suspend fun publishVehicleTelemetry(obdData: OBDData) {
		val v = vin()
		val topic = MQTTTopics.telemetry(v)
		val json = gson.toJson(obdData)
		publish(topic, json, retained = false)
	}

	override suspend fun publishAlert(alert: VehicleAlert) {
		val v = vin()
		val topic = MQTTTopics.alerts(v)
		val json = gson.toJson(alert)
		publish(topic, json, retained = false)
	}

	override suspend fun publishAnprEvent(event: ANPREvent) {
		val v = vin()
		val topic = MQTTTopics.anpr(v)
		val json = gson.toJson(event)
		publish(topic, json, retained = false)
	}

	override suspend fun publishHealth(ping: HealthPing) {
		val v = vin()
		val topic = MQTTTopics.health(v)
		val json = gson.toJson(ping)
		publish(topic, json, retained = false)
	}

	override suspend fun publishMetrics(payload: MetricsPayload) {
		val v = vin()
		val topic = MQTTTopics.metrics(v)
		val json = gson.toJson(payload)
		publish(topic, json, retained = false)
	}
}
