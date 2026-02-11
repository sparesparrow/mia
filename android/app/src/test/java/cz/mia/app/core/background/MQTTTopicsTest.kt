package cz.mia.app.core.background

import org.junit.Assert.assertEquals
import org.junit.Test

class MQTTTopicsTest {
	@Test
	fun telemetryTopic_isCorrect() {
		assertEquals("vehicle/telemetry/VIN123/obd", MQTTTopics.telemetry("VIN123"))
	}

	@Test
	fun alertsTopic_isCorrect() {
		assertEquals("vehicle/alerts/VIN123", MQTTTopics.alerts("VIN123"))
	}

	@Test
	fun anprTopic_isCorrect() {
		assertEquals("vehicle/events/VIN123/anpr", MQTTTopics.anpr("VIN123"))
	}
}
