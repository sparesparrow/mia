package cz.mia.app.core.background

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.PowerManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext

enum class SamplingMode { NORMAL, REDUCED, MINIMAL }

enum class ThermalSeverity { NONE, LIGHT, MODERATE, SEVERE, CRITICAL }

data class SystemPolicyState(
	val samplingMode: SamplingMode,
	val thermalSeverity: ThermalSeverity,
	val isPowerSaveMode: Boolean,
	val batteryPercent: Int,
	val advisoryMessage: String?
)

interface SystemPolicyManager {
	val state: Flow<SystemPolicyState>
}

@Singleton
class SystemPolicyManagerImpl @Inject constructor(
	@ApplicationContext private val context: Context
) : SystemPolicyManager {

	private val scope = CoroutineScope(Dispatchers.Default)

	private val thermalSeverityFlow: Flow<ThermalSeverity> = callbackFlow {
		val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
			val listener = PowerManager.OnThermalStatusChangedListener { status ->
				trySend(status.toSeverity())
			}
			pm.addThermalStatusListener(listener)
			// Emit initial status
			trySend(pm.currentThermalStatus.toSeverity())
			awaitClose { pm.removeThermalStatusListener(listener) }
		} else {
			// No thermal callbacks below Q; treat as NONE
			trySend(ThermalSeverity.NONE)
			awaitClose { }
		}
	}.distinctUntilChanged()

	private val powerSaveFlow: Flow<Boolean> = callbackFlow {
		val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
		// No direct callback, approximate via battery saver broadcast
		val filter = IntentFilter().apply {
			addAction(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED)
		}
		val receiver = object : BroadcastReceiver() {
			override fun onReceive(c: Context?, i: Intent?) {
				trySend(pm.isPowerSaveMode)
			}
		}
		context.registerReceiver(receiver, filter)
		trySend(pm.isPowerSaveMode)
		awaitClose { context.unregisterReceiver(receiver) }
	}.distinctUntilChanged()

	private val batteryPercentFlow: Flow<Int> = callbackFlow {
		val filter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
		val receiver = object : BroadcastReceiver() {
			override fun onReceive(c: Context?, intent: Intent?) {
				val i = intent ?: return
				val level = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
				val scale = i.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
				if (level >= 0 && scale > 0) trySend((100f * level / scale).toInt())
			}
		}
		context.registerReceiver(receiver, filter)
		// Emit initial once
		(context.registerReceiver(null, filter))?.let { 
			val level = it.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
			val scale = it.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
			if (level >= 0 && scale > 0) trySend((100f * level / scale).toInt())
		}
		awaitClose { context.unregisterReceiver(receiver) }
	}.distinctUntilChanged()

	override val state: Flow<SystemPolicyState> = combine(
		thermalSeverityFlow,
		powerSaveFlow,
		batteryPercentFlow
	) { thermal, powerSave, percent ->
		val mode = decideSamplingMode(thermal, powerSave, percent)
		val advisory = buildAdvisory(thermal, powerSave, percent, mode)
		SystemPolicyState(
			samplingMode = mode,
			thermalSeverity = thermal,
			isPowerSaveMode = powerSave,
			batteryPercent = percent,
			advisoryMessage = advisory
		)
	}.stateIn(scope, SharingStarted.Eagerly, SystemPolicyState(
		samplingMode = SamplingMode.NORMAL,
		thermalSeverity = ThermalSeverity.NONE,
		isPowerSaveMode = false,
		batteryPercent = 100,
		advisoryMessage = null
	))

	private fun decideSamplingMode(
		thermal: ThermalSeverity,
		powerSave: Boolean,
		percent: Int
	): SamplingMode {
		return when {
			thermal >= ThermalSeverity.SEVERE -> SamplingMode.MINIMAL
			percent <= 15 -> SamplingMode.MINIMAL
			thermal == ThermalSeverity.MODERATE || powerSave || percent <= 30 -> SamplingMode.REDUCED
			else -> SamplingMode.NORMAL
		}
	}

	private fun buildAdvisory(
		thermal: ThermalSeverity,
		powerSave: Boolean,
		percent: Int,
		mode: SamplingMode
	): String? {
		return when (mode) {
			SamplingMode.NORMAL -> null
			SamplingMode.REDUCED -> when {
				thermal >= ThermalSeverity.MODERATE -> "Device warm – reducing processing to prevent heat."
				powerSave -> "Battery saver on – reducing sampling to conserve power."
				percent <= 30 -> "Battery low (${percent}%) – reducing sampling."
				else -> null
			}
			SamplingMode.MINIMAL -> when {
				thermal >= ThermalSeverity.SEVERE -> "Device hot – pausing heavy processing until temperature drops."
				percent <= 15 -> "Battery critical (${percent}%) – pausing heavy processing."
				else -> "Energy/thermal constraints – pausing heavy processing."
			}
		}
	}
}

private fun Int.toSeverity(): ThermalSeverity {
	return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
		when (this) {
			PowerManager.THERMAL_STATUS_NONE -> ThermalSeverity.NONE
			PowerManager.THERMAL_STATUS_LIGHT -> ThermalSeverity.LIGHT
			PowerManager.THERMAL_STATUS_MODERATE -> ThermalSeverity.MODERATE
			PowerManager.THERMAL_STATUS_SEVERE -> ThermalSeverity.SEVERE
			PowerManager.THERMAL_STATUS_CRITICAL,
			PowerManager.THERMAL_STATUS_EMERGENCY,
			PowerManager.THERMAL_STATUS_SHUTDOWN -> ThermalSeverity.CRITICAL
			else -> ThermalSeverity.NONE
		}
	} else {
		ThermalSeverity.NONE
	}
}


