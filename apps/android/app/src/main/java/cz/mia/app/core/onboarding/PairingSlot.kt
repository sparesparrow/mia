package cz.mia.app.core.onboarding

/**
 * Holds the Activity-bound Bluetooth and Wi-Fi dialogs the screen attaches. While nothing is attached the steps answer
 * [StepOutcome.NotReady], so the wizard waits at PairingPhone instead of skipping them; an attached implementation
 * may still answer [StepOutcome.Unavailable], which the wizard skips with a note.
 */
class PairingSlot : SystemPairing {
	@Volatile private var target: SystemPairing? = null

	fun attach(pairing: SystemPairing?) {
		target = pairing
	}

	override suspend fun bondBluetooth(): StepOutcome = target?.bondBluetooth() ?: StepOutcome.NotReady

	override suspend fun suggestWifi(): StepOutcome = target?.suggestWifi() ?: StepOutcome.NotReady
}
