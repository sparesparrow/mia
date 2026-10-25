package cz.mia.app.core.background

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Binder
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import cz.mia.app.MIAApplication.Companion.CHANNEL_DRIVING_SERVICE
import cz.mia.app.MainActivity
import cz.mia.app.R
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import cz.mia.app.core.rules.AlertSink
import cz.mia.app.core.rules.CarRules
import cz.mia.app.core.rules.CarWarningAnnouncer
import cz.mia.app.core.voice.VoiceManager
import cz.mia.app.data.remote.websocket.Cycle1TelemetrySource
import cz.mia.app.data.repositories.EventRepository
import cz.mia.app.core.networking.ConnectivityObserver

class DrivingService : LifecycleService(), AlertSink {

	lateinit var bleManager: BLEManager

	lateinit var mqttManager: MQTTManager

	lateinit var obdManager: OBDManager

	lateinit var anprManager: ANPRManager

	lateinit var dvrManager: DVRManager

	lateinit var voiceManager: VoiceManager

	lateinit var carWarnings: CarWarningAnnouncer

	lateinit var cycle1Source: Cycle1TelemetrySource

	lateinit var events: EventRepository

	lateinit var connectivityObserver: ConnectivityObserver

	lateinit var systemPolicyManager: SystemPolicyManager

	private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
	private val binder = DrivingServiceBinder()

	private val _serviceState = MutableStateFlow(ServiceState.STOPPED)
	val serviceState: StateFlow<ServiceState> = _serviceState.asStateFlow()

	private val _vehicleData = MutableStateFlow(VehicleData())
	val vehicleData: StateFlow<VehicleData> = _vehicleData.asStateFlow()

	@Volatile
	private var appliedSamplingMode: SamplingMode? = null

	/** The collectors run while the service runs; each is its own coroutine so one never blocks another. */
	private var collectors: Job? = null

	override fun onCreate() {
		super.onCreate()
		val entryPoint = EntryPointAccessors.fromApplication(
			applicationContext,
			DrivingServiceEntryPoint::class.java,
		)
		bleManager = entryPoint.bleManager()
		mqttManager = entryPoint.mqttManager()
		obdManager = entryPoint.obdManager()
		anprManager = entryPoint.anprManager()
		dvrManager = entryPoint.dvrManager()
		voiceManager = entryPoint.voiceManager()
		carWarnings = entryPoint.carWarnings()
		cycle1Source = entryPoint.cycle1Source()
		events = entryPoint.events()
		connectivityObserver = entryPoint.connectivityObserver()
		systemPolicyManager = entryPoint.systemPolicyManager()
		enterForeground()
	}

	/**
	 * Promote to foreground with only the service types whose permissions are granted.
	 * Declaring the camera type without CAMERA makes Android 14+ throw SecurityException
	 * from startForeground and kills the app (seen on the device test run of v2.0.0-dev).
	 */
	private fun enterForeground() {
		var type = ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC or
			ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE
		if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
			PackageManager.PERMISSION_GRANTED
		) {
			type = type or ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA
		} else {
			Log.w(TAG, "CAMERA not granted: starting foreground service without camera type")
		}
		ServiceCompat.startForeground(this, NOTIFICATION_ID, createNotification(), type)
	}

	override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
		super.onStartCommand(intent, flags, startId)
		
		when (intent?.action) {
			ACTION_START -> startService()
			ACTION_STOP -> stopService()
			ACTION_PAUSE -> pauseService()
			ACTION_RESUME -> resumeService()
		}
		
		return START_STICKY
	}

	override fun onBind(intent: Intent): IBinder {
		super.onBind(intent)
		return binder
	}

	override fun onDestroy() {
		super.onDestroy()
		collectors?.cancel()
		collectors = null
		serviceScope.cancel()
		if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.N) {
			stopForeground(STOP_FOREGROUND_REMOVE)
		} else {
			@Suppress("DEPRECATION")
			stopForeground(true)
		}
	}

	private fun startService() {
		_serviceState.value = ServiceState.STARTING
		enterForeground()
		
		connectivityObserver.start(
			onAvailable = {
				serviceScope.launch { mqttManager.connect() }
			},
			onLost = { /* optional: update state or schedule retry */ }
		)
		
		startCollectors()
		serviceScope.launch {
			// One manager failing to start (no Bluetooth, no camera) must not stop the others or the collectors.
			val starters = listOf(
				"BLE" to suspend { bleManager.initialize() },
				"MQTT" to suspend { mqttManager.connect() },
				"OBD" to suspend { obdManager.startMonitoring() },
				"ANPR" to suspend { anprManager.startDetection() },
				"DVR" to suspend { dvrManager.startRecording() },
			)
			val failures = starters.mapNotNull { (name, start) ->
				try {
					start()
					null
				} catch (e: Exception) {
					Log.e(TAG, "$name failed to start", e)
					name
				}
			}
			_serviceState.value = if (failures.size == starters.size) ServiceState.ERROR else ServiceState.RUNNING
		}
	}

	private fun startCollectors() {
		if (collectors?.isActive == true) return
		collectors = serviceScope.launch {
			launch { collectVehicleData() }
			launch { collectCycle1Warnings() }
			launch { collectAnprEvents() }
			launch { collectPolicy() }
		}
	}

	private fun stopService() {
		_serviceState.value = ServiceState.STOPPING
		
		connectivityObserver.stop()
		collectors?.cancel()
		collectors = null
		
		serviceScope.launch {
			try {
				bleManager.disconnect()
				mqttManager.disconnect()
				obdManager.stopMonitoring()
				anprManager.stopDetection()
				dvrManager.stopRecording()
				
				_serviceState.value = ServiceState.STOPPED
				stopSelf()
				
			} catch (e: Exception) {
				_serviceState.value = ServiceState.ERROR
			}
		}
	}

	private suspend fun collectPolicy() {
		systemPolicyManager.state.collect { newState ->
			applyPolicy(newState.samplingMode)
		}
	}

	private fun applyPolicy(mode: SamplingMode) {
		if (appliedSamplingMode == mode) return
		appliedSamplingMode = mode
		when (mode) {
			SamplingMode.NORMAL -> {
				serviceScope.launch { anprManager.startDetection() }
				dvrManager.startRecording()
				obdManager.setSamplingMode(SamplingMode.NORMAL)
			}
			SamplingMode.REDUCED -> {
				// Keep essential features, avoid heavy spikes
				serviceScope.launch { anprManager.startDetection() }
				dvrManager.startRecording()
				obdManager.setSamplingMode(SamplingMode.REDUCED)
			}
			SamplingMode.MINIMAL -> {
				serviceScope.launch { anprManager.stopDetection() }
				dvrManager.stopRecording()
				obdManager.setSamplingMode(SamplingMode.MINIMAL)
			}
		}
	}

	private fun pauseService() {
		_serviceState.value = ServiceState.PAUSED
		// Pause data collection but keep connections alive
	}

	private fun resumeService() {
		_serviceState.value = ServiceState.RUNNING
		// Resume data collection
	}

	private suspend fun collectVehicleData() {
		// Collect OBD data
		obdManager.obdData.collect { obdData ->
			_vehicleData.value = _vehicleData.value.copy(
				fuelLevel = obdData.fuelLevel,
				engineRpm = obdData.engineRpm,
				vehicleSpeed = obdData.vehicleSpeed,
				coolantTemp = obdData.coolantTemp,
				engineLoad = obdData.engineLoad,
				dtcCodes = obdData.dtcCodes
			)
			
			// Persist & publish
			serviceScope.launch { events.recordTelemetry(obdData) }
			mqttManager.publishVehicleTelemetry(obdData)

			carWarnings.update(CarRules.fromObd(obdData), this@DrivingService)
		}
	}

	/**
	 * Evaluates the Pi's Cycle 1 telemetry once a second (REQ-AND-019). A tick rather than per message, because
	 * a limit must hold for its dwell time and a stale envelope must count as unknown even when nothing arrives.
	 */
	private suspend fun collectCycle1Warnings() {
		val lease = cycle1Source.acquire()
		try {
			while (serviceScope.isActive) {
				val readings = CarRules.fromCycle1(cycle1Source.envelope.value, cycle1Source.isStale())
				carWarnings.update(readings, this@DrivingService)
				delay(CYCLE1_EVALUATION_MS)
			}
		} finally {
			lease.release()
		}
	}

	private suspend fun collectAnprEvents() {
		anprManager.events.collect { event ->
			serviceScope.launch { events.recordAnpr(event) }
			mqttManager.publishAnprEvent(event)
			dvrManager.triggerEventClip("anpr_${event.plateHash.take(8)}")
		}
	}

	override suspend fun raise(alert: VehicleAlert, notificationId: Int) {
		serviceScope.launch { events.recordAlert(alert) }
		serviceScope.launch { mqttManager.publishAlert(alert) }
		showAlertNotification(alert, notificationId)
		dvrManager.triggerEventClip("alert_${alert.code}")
	}

	override fun remind(alert: VehicleAlert, notificationId: Int) {
		showAlertNotification(alert, notificationId)
	}

	override fun withdraw(notificationId: Int) {
		(getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).cancel(notificationId)
	}

	private fun showAlertNotification(alert: VehicleAlert, notificationId: Int) {
		val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
		
		val intent = Intent(this, MainActivity::class.java).apply {
			flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
		}
		
		val pendingIntent = PendingIntent.getActivity(
			this, 0, intent,
			PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
		)
		
		val notification = NotificationCompat.Builder(this, CHANNEL_ALERTS)
			.setContentTitle("AI-SERVIS Alert")
			.setContentText(alert.message)
			.setSmallIcon(R.drawable.ic_alert)
			.setPriority(NotificationCompat.PRIORITY_HIGH)
			.setContentIntent(pendingIntent)
			.setAutoCancel(true)
			.build()
		
		notificationManager.notify(notificationId, notification)
	}

	private fun createNotification(): Notification {
		val intent = Intent(this, MainActivity::class.java).apply {
			flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
		}
		
		val pendingIntent = PendingIntent.getActivity(
			this, 0, intent,
			PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
		)
		
		return NotificationCompat.Builder(this, CHANNEL_DRIVING_SERVICE)
			.setContentTitle("AI-SERVIS Active")
			.setContentText("Driving assistance is running")
			.setSmallIcon(R.drawable.ic_car)
			.setContentIntent(pendingIntent)
			.setOngoing(true)
			.build()
	}

	inner class DrivingServiceBinder : Binder() {
		fun getService(): DrivingService = this@DrivingService
	}

	companion object {
		private const val TAG = "DrivingService"
		private const val NOTIFICATION_ID = 1001
		private const val CHANNEL_ALERTS = "alerts"
		private const val CYCLE1_EVALUATION_MS = 1_000L
		
		const val ACTION_START = "cz.mia.app.START_DRIVING_SERVICE"
		const val ACTION_STOP = "cz.mia.app.STOP_DRIVING_SERVICE"
		const val ACTION_PAUSE = "cz.mia.app.PAUSE_DRIVING_SERVICE"
		const val ACTION_RESUME = "cz.mia.app.RESUME_DRIVING_SERVICE"
	}
}

@EntryPoint
@InstallIn(SingletonComponent::class)
interface DrivingServiceEntryPoint {
	fun bleManager(): BLEManager
	fun mqttManager(): MQTTManager
	fun obdManager(): OBDManager
	fun anprManager(): ANPRManager
	fun dvrManager(): DVRManager
	fun voiceManager(): VoiceManager
	fun carWarnings(): CarWarningAnnouncer
	fun cycle1Source(): Cycle1TelemetrySource
	fun events(): EventRepository
	fun connectivityObserver(): ConnectivityObserver
	fun systemPolicyManager(): SystemPolicyManager
}

enum class ServiceState {
	STOPPED, STARTING, RUNNING, PAUSED, STOPPING, ERROR
}

enum class AlertSeverity {
	LOW, WARNING, ERROR, CRITICAL
}

data class VehicleData(
	val fuelLevel: Int = 0,
	val engineRpm: Int = 0,
	val vehicleSpeed: Int = 0,
	val coolantTemp: Int = 0,
	val engineLoad: Int = 0,
	val dtcCodes: List<String> = emptyList()
)

data class VehicleAlert(
	val severity: AlertSeverity,
	val code: String,
	val message: String,
	val timestamp: Long = System.currentTimeMillis()
)

data class OBDData(
	val fuelLevel: Int,
	val engineRpm: Int,
	val vehicleSpeed: Int,
	val coolantTemp: Int,
	val engineLoad: Int,
	val dtcCodes: List<String>
)

