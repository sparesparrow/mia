package cz.mia.app.core.onboarding

/** The result of one step that needs the user's approval in a system dialog. */
sealed interface StepOutcome {
	object Done : StepOutcome

	/** The user dismissed the dialog; the wizard stays on the step and offers it again. */
	data class Cancelled(val why: String) : StepOutcome

	/** The platform cannot do this here (old Android, no adapter). The wizard shows it as skipped and goes on. */
	data class Unavailable(val why: String) : StepOutcome

	data class Failed(val msg: String) : StepOutcome

	/** No dialog implementation is attached yet (the screen is not showing); the wizard waits and does not skip the step. */
	object NotReady : StepOutcome
}

/**
 * The Android system dialogs of the PairingPhone step. Implemented in the screens task (needs an Activity); the
 * wizard only sees outcomes. Known gap: nothing delivers the Wi-Fi password the Pi generated to the phone yet
 * (ADR-0025 is silent and mia-enroll prints none), so [suggestWifi] may legitimately report Unavailable.
 */
interface SystemPairing {
	suspend fun bondBluetooth(): StepOutcome
	suspend fun suggestWifi(): StepOutcome
}
