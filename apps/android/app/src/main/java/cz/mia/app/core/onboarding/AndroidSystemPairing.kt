package cz.mia.app.core.onboarding

import android.annotation.SuppressLint
import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The real system dialogs of the PairingPhone step. Bluetooth: [BluetoothDevice.createBond] makes Android show its own
 * pairing dialog; the outcome is read from ACTION_BOND_STATE_CHANGED. The BLUETOOTH_CONNECT runtime permission (Android 12+)
 * is requested through [requestConnectPermission], which the screen implements with its permission launcher.
 *
 * [piBluetoothAddress] is where the Pi's Bluetooth address comes from. Nothing delivers it to the phone yet (ADR-0025
 * is silent), so the screen passes a source that answers null and the step then reports Unavailable instead of guessing.
 * Wi-Fi: the password the Pi generated is not delivered to the phone either, so [suggestWifi] is Unavailable.
 */
class AndroidSystemPairing(
	private val context: Context,
	private val requestConnectPermission: suspend () -> Boolean,
	private val piBluetoothAddress: () -> String? = { null },
) : SystemPairing {

	@SuppressLint("MissingPermission") // checked in hasConnectPermission() before any call
	override suspend fun bondBluetooth(): StepOutcome {
		// No address, no permission prompt: the prompt would not be used.
		val address = piBluetoothAddress() ?: return StepOutcome.Unavailable("The Pi's Bluetooth address is not delivered to the phone yet")
		if (!hasConnectPermission() && !requestConnectPermission()) return StepOutcome.Cancelled("permission")
		if (!hasConnectPermission()) return StepOutcome.Cancelled("permission")
		val adapter: BluetoothAdapter = ContextCompat.getSystemService(context, BluetoothManager::class.java)?.adapter
			?: return StepOutcome.Unavailable("This phone has no Bluetooth")
		if (!adapter.isEnabled) return StepOutcome.Failed("Bluetooth is turned off")
		val device = try {
			adapter.getRemoteDevice(address)
		} catch (e: IllegalArgumentException) {
			return StepOutcome.Failed("The Pi's Bluetooth address is not valid")
		}
		if (device.bondState == BluetoothDevice.BOND_BONDED) return StepOutcome.Done
		return withTimeoutOrNull(BOND_TIMEOUT_MS) { awaitBond(device) } ?: StepOutcome.Failed("Pairing timed out")
	}

	override suspend fun suggestWifi(): StepOutcome = StepOutcome.Unavailable("The Wi-Fi password is not delivered to the phone yet")

	private fun hasConnectPermission(): Boolean =
		Build.VERSION.SDK_INT < Build.VERSION_CODES.S ||
			ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED

	@SuppressLint("MissingPermission")
	private suspend fun awaitBond(device: BluetoothDevice): StepOutcome = suspendCancellableCoroutine { cont ->
		var sawBonding = false
		val receiver = object : BroadcastReceiver() {
			override fun onReceive(c: Context?, intent: Intent?) {
				if (intent == null || intent.action != BluetoothDevice.ACTION_BOND_STATE_CHANGED) return
				@Suppress("DEPRECATION")
				val changed = intent.getParcelableExtra<BluetoothDevice>(BluetoothDevice.EXTRA_DEVICE)
				if (changed?.address != device.address) return
				val now = intent.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE, BluetoothDevice.ERROR)
				val outcome = when {
					now == BluetoothDevice.BOND_BONDED -> StepOutcome.Done
					now == BluetoothDevice.BOND_BONDING -> { sawBonding = true; null }
					now == BluetoothDevice.BOND_NONE && sawBonding -> StepOutcome.Cancelled("the pairing was not confirmed")
					else -> null
				}
				if (outcome != null && cont.isActive) {
					runCatching { context.unregisterReceiver(this) }
					cont.resume(outcome)
				}
			}
		}
		context.registerReceiver(receiver, IntentFilter(BluetoothDevice.ACTION_BOND_STATE_CHANGED))
		cont.invokeOnCancellation { runCatching { context.unregisterReceiver(receiver) } }
		if (!device.createBond() && cont.isActive) {
			runCatching { context.unregisterReceiver(receiver) }
			cont.resume(StepOutcome.Failed("Android could not start pairing"))
		}
	}

	private companion object {
		const val BOND_TIMEOUT_MS = 90_000L
	}
}
