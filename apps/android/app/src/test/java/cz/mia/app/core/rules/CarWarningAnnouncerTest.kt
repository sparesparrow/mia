package cz.mia.app.core.rules

// @req REQ-AND-019

import cz.mia.app.core.background.AlertSeverity
import cz.mia.app.core.background.VehicleAlert
import cz.mia.app.core.voice.SpeechPriority
import cz.mia.app.core.voice.SpeechRequest
import cz.mia.app.core.voice.VoiceManager
import cz.mia.app.core.voice.VoiceState
import java.util.Locale
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

private class FakeVoice(var locale: Locale = Locale("cs", "CZ")) : VoiceManager {
	val queued = mutableListOf<SpeechRequest>()
	val immediate = mutableListOf<Pair<String, SpeechPriority>>()

	override val state: StateFlow<VoiceState> = MutableStateFlow(VoiceState.Ready)
	override val queueSize: StateFlow<Int> = MutableStateFlow(0)
	override suspend fun speak(text: String) = speak(SpeechRequest(text))
	override suspend fun speak(request: SpeechRequest) {
		queued += request
	}
	override suspend fun speakNow(text: String, priority: SpeechPriority) {
		immediate += text to priority
	}
	override fun stop() = Unit
	override fun clearQueue() = Unit
	override fun setLocale(locale: Locale): Boolean = true
	override fun setSpeechRate(rate: Float) = Unit
	override fun setPitch(pitch: Float) = Unit
	override fun isAvailable(): Boolean = true
	override fun getAvailableLocales(): Set<Locale> = setOf(locale)
	override fun activeLocale(): Locale = locale
}

private class FakeSink : AlertSink {
	val raised = mutableListOf<Pair<VehicleAlert, Int>>()
	val withdrawn = mutableListOf<Int>()

	override suspend fun raise(alert: VehicleAlert, notificationId: Int) {
		raised += alert to notificationId
	}

	override fun withdraw(notificationId: Int) {
		withdrawn += notificationId
	}
}

class CarWarningAnnouncerTest {
	private var time = 0L
	private val voice = FakeVoice()
	private val sink = FakeSink()
	private val announcer = CarWarningAnnouncer(voice, AlertThrottle(now = { time }))

	private fun at(ms: Long, vararg readings: ConditionReading) = runBlocking {
		time = ms
		announcer.update(readings.toList(), sink)
	}

	@Test
	fun `a critical warning interrupts current speech and raises one alert with a stable notification`() {
		at(0, ConditionReading.of(CarCondition.ENGINE_OVERHEAT, 112.0))
		at(10_000, ConditionReading.of(CarCondition.ENGINE_OVERHEAT, 112.0))
		at(11_000, ConditionReading.of(CarCondition.ENGINE_OVERHEAT, 113.0))

		assertEquals(1, voice.immediate.size)
		assertEquals(SpeechPriority.CRITICAL, voice.immediate.single().second)
		assertTrue(voice.immediate.single().first.startsWith("Teplota motoru 112 stupňů."))
		assertTrue(voice.queued.isEmpty())

		val (alert, id) = sink.raised.single()
		assertEquals("ENGINE_OVERHEAT", alert.code)
		assertEquals(AlertSeverity.CRITICAL, alert.severity)
		assertEquals(CarWarningAnnouncer.notificationId(CarCondition.ENGINE_OVERHEAT), id)
	}

	@Test
	fun `a warning is queued with high priority`() {
		at(0, ConditionReading.of(CarCondition.RPM_HIGH, 6400.0))
		at(3_000, ConditionReading.of(CarCondition.RPM_HIGH, 6400.0))

		assertTrue(voice.immediate.isEmpty())
		assertEquals(SpeechPriority.HIGH, voice.queued.single().priority)
		assertEquals("RPM_HIGH", sink.raised.single().first.code)
	}

	@Test
	fun `clearing withdraws the notification of that condition`() {
		at(0, ConditionReading.of(CarCondition.RPM_HIGH, 6400.0))
		at(3_000, ConditionReading.of(CarCondition.RPM_HIGH, 6400.0))
		at(4_000, ConditionReading.of(CarCondition.RPM_HIGH, 3000.0))
		at(9_000, ConditionReading.of(CarCondition.RPM_HIGH, 3000.0))

		assertEquals(listOf(CarWarningAnnouncer.notificationId(CarCondition.RPM_HIGH)), sink.withdrawn)
	}

	@Test
	fun `the wording follows the voice that is actually speaking`() {
		voice.locale = Locale.US
		at(0, ConditionReading.of(CarCondition.BATTERY_LOW, 11.2))
		at(60_000, ConditionReading.of(CarCondition.BATTERY_LOW, 11.2))

		assertEquals("Battery at 11.2 volts. Have the battery and charging checked.", voice.queued.single().text)
	}

	@Test
	fun `notification ids differ per condition`() {
		val ids = CarCondition.values().map { CarWarningAnnouncer.notificationId(it) }
		assertEquals(ids.size, ids.toSet().size)
	}
}
