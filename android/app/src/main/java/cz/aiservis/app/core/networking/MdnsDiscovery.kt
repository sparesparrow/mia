package cz.aiservis.app.core.networking

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import android.net.wifi.WifiManager
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.withTimeoutOrNull
import java.util.concurrent.Executors

@Singleton
class MdnsDiscovery @Inject constructor(
	@ApplicationContext private val context: Context
) {
	private var lastResults: List<String> = emptyList()

	fun discoverServices(serviceType: String = "_mqtt._tcp.local."): List<String> = lastResults

	suspend fun discoverMqtt(timeoutMs: Long = 2000L): List<String> {
		val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
		val lock = wifi.createMulticastLock("ai-servis-mdns").apply { setReferenceCounted(true); acquire() }
		val nsd = context.getSystemService(Context.NSD_SERVICE) as NsdManager
		val out = Channel<String>(capacity = Channel.UNLIMITED)

		val resolveListener = object : NsdManager.ResolveListener {
			override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {}
			override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
				val host = serviceInfo.host?.hostAddress ?: return
				val port = serviceInfo.port
				out.trySend("$host:$port")
			}
		}

		val discoveryListener = object : NsdManager.DiscoveryListener {
			override fun onStartDiscoveryFailed(serviceType: String?, errorCode: Int) {}
			override fun onStopDiscoveryFailed(serviceType: String?, errorCode: Int) {}
			override fun onDiscoveryStarted(serviceType: String?) {}
			override fun onDiscoveryStopped(serviceType: String?) {}
			override fun onServiceFound(serviceInfo: NsdServiceInfo) {
				// Only resolve MQTT
				if (serviceInfo.serviceType?.contains("_mqtt._tcp") == true) {
					if (Build.VERSION.SDK_INT >= 34) {
						nsd.registerServiceInfoCallback(
							serviceInfo,
							Executors.newSingleThreadExecutor(),
							object : NsdManager.ServiceInfoCallback {
								override fun onServiceInfoCallbackRegistrationFailed(errorCode: Int) {}
								override fun onServiceUpdated(info: NsdServiceInfo) {
									resolveListener.onServiceResolved(info)
									try {
										nsd.unregisterServiceInfoCallback(this)
									} catch (e: Exception) {
										// Ignore if already unregistered
									}
								}
								override fun onServiceLost() {}
								override fun onServiceInfoCallbackUnregistered() {}
							}
						)
					} else {
						@Suppress("DEPRECATION")
						nsd.resolveService(serviceInfo, resolveListener)
					}
				}
			}
			override fun onServiceLost(serviceInfo: NsdServiceInfo) {}
		}

		return try {
			val serviceType = "_mqtt._tcp"
			nsd.discoverServices(serviceType, NsdManager.PROTOCOL_DNS_SD, discoveryListener)
			val results = mutableSetOf<String>()
			withTimeoutOrNull(timeoutMs) {
				for (i in 0 until 10) {
					out.receiveCatching().getOrNull()?.let { results.add(it) }
				}
			}
			lastResults = results.toList()
			lastResults
		} catch (_: Exception) {
			emptyList()
		} finally {
			try { nsd.stopServiceDiscovery(object : NsdManager.DiscoveryListener {
				override fun onStartDiscoveryFailed(serviceType: String?, errorCode: Int) {}
				override fun onStopDiscoveryFailed(serviceType: String?, errorCode: Int) {}
				override fun onDiscoveryStarted(serviceType: String?) {}
				override fun onDiscoveryStopped(serviceType: String?) {}
				override fun onServiceFound(serviceInfo: NsdServiceInfo) {}
				override fun onServiceLost(serviceInfo: NsdServiceInfo) {}
			}) } catch (_: Exception) {}
			try { lock.release() } catch (_: Exception) {}
		}
	}
}
