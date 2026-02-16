package cz.mia.app.core.background

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import cz.mia.app.MIAApplication.Companion.CHANNEL_DRIVING_SERVICE
import cz.mia.app.MainActivity
import cz.mia.app.R
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import cz.mia.app.core.rules.RulesEngine
import cz.mia.app.core.voice.VoiceManager
import cz.mia.app.data.repositories.EventRepository
import cz.mia.app.core.networking.ConnectivityObserver

@AndroidEntryPoint
class DrivingService : LifecycleService() {

	@Inject
	lateinit var bleManager: BLEManager

	@Inject
	lateinit var mqttManager: MQTTManager

	@Inject
	lateinit var obdManager: OBDManager

	@Inject
	lateinit var anprManager: ANPRManager

	@Inject
	lateinit var dvrManager: DVRManager

	@Inject
	lateinit var voiceManager: VoiceManager

	@Inject
	lateinit var rulesEngine: RulesEngine

	@Inject
	lateinit var events: EventRepository

	@Inject
	lateinit var connectivityObserver: ConnectivityObserver

	@Inject
	lateinit var systemPolicyManager: SystemPolicyManager

	private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
	private val binder = DrivingServiceBinder()

	private val _serviceState = MutableStateFlow(ServiceState.STOPPED)
	val serviceState: StateFlow<ServiceState> = _serviceState.asStateFlow()

	private val _vehicleData = MutableStateFlow(VehicleData())
	val vehicleData: StateFlow<VehicleData> = _vehicleData.asStateFlow()

	@Volatile
	private var appliedSamplingMode: SamplingMode? = null

	override fun onCreate() {
		super.onCreate()
		startForeground(NOTIFICATION_ID, createNotification())
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
		startForeground(NOTIFICATION_ID, createNotification())
		
		connectivityObserver.start(
			onAvailable = {
				serviceScope.launch { mqttManager.connect() }
			},
			onLost = { /* optional: update state or schedule retry */ }
		)
		
		serviceScope.launch {
			try {
				// Initialize managers
				bleManager.initialize()
				mqttManager.connect()
				obdManager.startMonitoring()
				anprManager.startDetection()
				dvrManager.startRecording()
				
				_serviceState.value = ServiceState.RUNNING
				
				// Start data collection
				collectVehicleData()
				collectAnprEvents()
				collectPolicy()
				
			} catch (e: Exception) {
				_serviceState.value = ServiceState.ERROR
			}
		}
	}

	private fun stopService() {
		_serviceState.value = ServiceState.STOPPING
		
		connectivityObserver.stop()
		
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

	private fun collectPolicy() {
		serviceScope.launch {
			systemPolicyManager.state.collect { newState ->
				applyPolicy(newState.samplingMode)
			}
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
			
			// Check for alerts
			checkAlerts(obdData)
		}
	}

	private suspend fun collectAnprEvents() {
		anprManager.events.collect { event ->
			serviceScope.launch { events.recordAnpr(event) }
			mqttManager.publishAnprEvent(event)
			dvrManager.triggerEventClip("anpr_${event.plateHash.take(8)}")
		}
	}

	private fun checkAlerts(obdData: OBDData) {
		val alerts = rulesEngine.evaluate(obdData)
		if (alerts.isNotEmpty()) {
			alerts.forEach { alert ->
				serviceScope.launch { events.recordAlert(alert) }
				serviceScope.launch { mqttManager.publishAlert(alert) }
				showAlertNotification(alert)
				serviceScope.launch { voiceManager.speak(alert.message) }
				dvrManager.triggerEventClip("alert_${alert.code}")
			}
		}
	}

	private fun showAlertNotification(alert: VehicleAlert) {
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
		
		notificationManager.notify(alert.hashCode(), notification)
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
		private const val NOTIFICATION_ID = 1001
		private const val CHANNEL_ALERTS = "alerts"
		
		const val ACTION_START = "cz.mia.app.START_DRIVING_SERVICE"
		const val ACTION_STOP = "cz.mia.app.STOP_DRIVING_SERVICE"
		const val ACTION_PAUSE = "cz.mia.app.PAUSE_DRIVING_SERVICE"
		const val ACTION_RESUME = "cz.mia.app.RESUME_DRIVING_SERVICE"
	}
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

