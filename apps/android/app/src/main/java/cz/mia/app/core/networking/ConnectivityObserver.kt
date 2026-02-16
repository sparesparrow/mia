package cz.mia.app.core.networking

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext

@Singleton
class ConnectivityObserver @Inject constructor(
	@ApplicationContext private val context: Context
) {
	private var connectivityManager: ConnectivityManager? = null
	private var networkCallback: ConnectivityManager.NetworkCallback? = null

	fun start(onAvailable: () -> Unit, onLost: (() -> Unit)? = null) {
		if (connectivityManager == null) {
			connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
		}
		if (networkCallback != null) return
		val request = NetworkRequest.Builder()
			.addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
			.build()
		networkCallback = object : ConnectivityManager.NetworkCallback() {
			override fun onAvailable(network: Network) {
				onAvailable()
			}
			override fun onLost(network: Network) {
				onLost?.invoke()
			}
		}
		connectivityManager?.registerNetworkCallback(request, networkCallback!!)
	}

	fun stop() {
		networkCallback?.let { cb -> connectivityManager?.unregisterNetworkCallback(cb) }
		networkCallback = null
	}
}
