package cz.mia.app.ui.screens.vehicle

import cz.mia.app.core.onboarding.OnboardingState

/** What the wizard shows for one state: pure text and button labels, so it can be tested on the JVM (no secret ever goes in). */
data class VehicleUi(
	val title: String,
	val body: String,
	/** Label of the main button; null when the step has none (it is waiting for work to finish). */
	val primaryLabel: String?,
	val secondaryLabel: String?,
	/** True while work runs and a progress bar belongs on screen. */
	val busy: Boolean,
	/** 0..1 when the progress is known, otherwise null (an indeterminate bar). */
	val fraction: Float? = null,
)

const val INSTALL_TITLE = "Install MIA on a car"
const val PAIR_TITLE = "Pair vehicle"

/** The text of every wizard state. [Failed][OnboardingState.Failed] carries the machine's own secret-free message. */
fun uiModelFor(state: OnboardingState): VehicleUi = when (state) {
	OnboardingState.Welcome -> VehicleUi(
		INSTALL_TITLE,
		"This sets up MIA on the Raspberry Pi in your car. You need your MIA activation key and the Pi powered on in your car.",
		"Start", null, busy = false,
	)
	OnboardingState.EnterActivationKey -> VehicleUi(
		INSTALL_TITLE,
		"Enter the activation key you received from MIA. It is used once to authorize this phone and is not stored.",
		"Continue", null, busy = false,
	)
	OnboardingState.FindingPi -> VehicleUi(
		INSTALL_TITLE,
		"Looking for your Pi on this network",
		null, "Start over", busy = true,
	)
	OnboardingState.Authorizing -> VehicleUi(
		INSTALL_TITLE,
		"Authorizing this phone with your Pi",
		null, null, busy = true,
	)
	OnboardingState.FirstSetup -> VehicleUi(
		INSTALL_TITLE,
		"Choose the first settings for your Pi. You can leave a field empty to use the default.",
		"Install", null, busy = false,
	)
	is OnboardingState.Installing -> VehicleUi(
		INSTALL_TITLE,
		if (state.total > 0) "Sent ${state.sent} of ${state.total}" else "Preparing the package",
		null, null, busy = true,
		fraction = if (state.total > 0) (state.sent.toFloat() / state.total).coerceIn(0f, 1f) else null,
	)
	OnboardingState.PairingPhone -> VehicleUi(
		PAIR_TITLE,
		"Android may ask for permission or confirmation to pair Bluetooth and to add the MIA Wi-Fi network. " +
			"These prompts come from Android. If you cancel one you can try again here. " +
			"If the Pi has not provided its Bluetooth or Wi-Fi details yet, that step is skipped with a note.",
		"Continue", null, busy = false,
	)
	OnboardingState.PairAdapter -> VehicleUi(
		PAIR_TITLE,
		"Optional: pair your car's OBD adapter now. You can also do it later from More, OBD pairing.",
		"Pair the OBD adapter", "Skip", busy = false,
	)
	OnboardingState.Done -> VehicleUi(
		INSTALL_TITLE,
		"Your car is set up",
		null, "Set up another car", busy = false,
	)
	is OnboardingState.Failed -> VehicleUi(
		INSTALL_TITLE,
		state.message,
		if (state.retryable) "Try again" else "Start over",
		if (state.retryable) "Start over" else null,
		busy = false,
	)
}
