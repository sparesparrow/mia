package cz.mia.app.core.networking

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
	private var lastApiResults: List<String> = emptyList()

	fun discoverServices(serviceType: String = "_mqtt._tcp.local."): List<String> = when (serviceType) {
		"_mia-api._tcp", "_mia-api._tcp.local." -> lastApiResults
		else -> lastResults
	}

	/**
	 * Discover MIA REST API via mDNS (_mia-api._tcp).
	 * Returns list of "host:port" strings.
	 */
	suspend fun discoverApi(timeoutMs: Long = 2000L): List<String> {
		val results = discoverServiceType("_mia-api._tcp", timeoutMs)
		lastApiResults = results
		return results
	}

	fun getLastApiResults(): List<String> = lastApiResults

	suspend fun discoverMqtt(timeoutMs: Long = 2000L): List<String> {
		val results = discoverServiceType("_mqtt._tcp", timeoutMs)
		lastResults = results
		return results
	}

	private suspend fun discoverServiceType(type: String, timeoutMs: Long): List<String> {
		val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
		val lock = wifi.createMulticastLock("mia-mdns").apply { setReferenceCounted(true); acquire() }
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
				if (serviceInfo.serviceType?.contains(type) == true) {
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
									} catch (e: Exception) {}
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
			nsd.discoverServices(type, NsdManager.PROTOCOL_DNS_SD, discoveryListener)
			val results = mutableSetOf<String>()
			withTimeoutOrNull(timeoutMs) {
				for (i in 0 until 10) {
					out.receiveCatching().getOrNull()?.let { results.add(it) }
				}
			}
			results.toList()
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
