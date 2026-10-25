package cz.mia.app.core.rules

import cz.mia.app.core.background.AlertSeverity
import cz.mia.app.core.background.VehicleAlert
import cz.mia.app.core.voice.SpeechPriority
import cz.mia.app.core.voice.SpeechRequest
import cz.mia.app.core.voice.VoiceManager
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** Where a raised warning goes besides speech: the event log, MQTT, a notification and a dashcam clip. */
interface AlertSink {
	suspend fun raise(alert: VehicleAlert, notificationId: Int)

	fun withdraw(notificationId: Int)
}

/**
 * Turns readings into spoken warnings (REQ-AND-019): one warning per occurrence, a critical one interrupts
 * whatever is being said, and a cleared condition withdraws its notification.
 */
@Singleton
class CarWarningAnnouncer(
	private val voice: VoiceManager,
	private val throttle: AlertThrottle,
) {
	@Inject
	constructor(voice: VoiceManager) : this(voice, AlertThrottle(now = System::currentTimeMillis))

	private val lock = Mutex()

	suspend fun update(readings: List<ConditionReading>, sink: AlertSink) {
		val events = lock.withLock { throttle.update(readings) }
		for (event in events) {
			when (event) {
				is ThrottleEvent.Activated -> announce(event, sink)
				is ThrottleEvent.Cleared -> sink.withdraw(notificationId(event.condition))
			}
		}
	}

	private suspend fun announce(event: ThrottleEvent.Activated, sink: AlertSink) {
		val condition = event.condition
		val language = if (voice.activeLocale().language == "cs") "cs" else "en"
		val message = WarningText.render(condition, event.value, language)
		sink.raise(VehicleAlert(condition.severity, condition.code, message.display), notificationId(condition))
		if (condition.severity == AlertSeverity.CRITICAL) {
			voice.speakNow(message.spoken, SpeechPriority.CRITICAL)
		} else {
			voice.speak(SpeechRequest(message.spoken, SpeechPriority.HIGH))
		}
	}

	companion object {
		/** One stable notification per condition, so a repeat replaces it instead of stacking. */
		fun notificationId(condition: CarCondition): Int = 2000 + condition.ordinal
	}
}
