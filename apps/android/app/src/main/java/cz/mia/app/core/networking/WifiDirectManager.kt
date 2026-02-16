package cz.mia.app.core.networking

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.wifi.p2p.WifiP2pManager
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Singleton
class WifiDirectManager @Inject constructor(
	private val context: Context
) {
	private val scope = CoroutineScope(Dispatchers.Main)
	private var receiver: BroadcastReceiver? = null
	private var registered = false
	private var retryJob: Job? = null

	fun startMonitoring(onRetry: () -> Unit) {
		if (registered) return
		val filter = IntentFilter().apply {
			addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION)
		}
		receiver = object : BroadcastReceiver() {
			override fun onReceive(c: Context?, i: Intent?) {
				// On lost, schedule retry with backoff
				scheduleRetry(onRetry)
			}
		}
		context.registerReceiver(receiver, filter)
		registered = true
	}

	fun stopMonitoring() {
		if (!registered) return
		context.unregisterReceiver(receiver)
		receiver = null
		registered = false
		retryJob?.cancel()
	}

	private fun scheduleRetry(onRetry: () -> Unit) {
		retryJob?.cancel()
		retryJob = scope.launch {
			Backoff.exponential(baseMs = 1000, maxMs = 20000, attempts = 5).forEach { d ->
				delay(d)
				onRetry()
			}
		}
	}
}
