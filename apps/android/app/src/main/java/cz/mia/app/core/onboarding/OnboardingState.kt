package cz.mia.app.core.onboarding

/**
 * Where the "Install MIA on a car" wizard is (ADR-0025, REQ-ONB-008). The order is
 * Welcome, EnterActivationKey, FindingPi, Authorizing, FirstSetup, Installing, PairingPhone, PairAdapter, Done.
 * FirstSetup comes before Installing so a single .miapkg carries config.yaml (ADR-0023). No state or message ever
 * holds the activation key, the grant or a secret.
 */
sealed interface OnboardingState {
	object Welcome : OnboardingState
	object EnterActivationKey : OnboardingState
	object FindingPi : OnboardingState

	/** Asking the auth server for a grant, then enrolling the phone key on the Pi with it. */
	object Authorizing : OnboardingState
	object FirstSetup : OnboardingState
	data class Installing(val sent: Int, val total: Int) : OnboardingState

	/** Bluetooth bond and Wi-Fi suggestion: each needs a system dialog the user approves. */
	object PairingPhone : OnboardingState
	object PairAdapter : OnboardingState
	object Done : OnboardingState

	/** [step] names the phase that failed; [message] is readable and free of secrets; [retryable] says retry() helps. */
	data class Failed(val step: String, val retryable: Boolean, val message: String) : OnboardingState
}
