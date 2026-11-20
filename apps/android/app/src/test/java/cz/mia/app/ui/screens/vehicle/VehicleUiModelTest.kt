package cz.mia.app.ui.screens.vehicle

// @req REQ-ONB-008

import cz.mia.app.core.onboarding.OnboardingState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class VehicleUiModelTest {
	private val every: List<OnboardingState> = listOf(
		OnboardingState.Welcome,
		OnboardingState.EnterActivationKey,
		OnboardingState.FindingPi,
		OnboardingState.Authorizing,
		OnboardingState.FirstSetup,
		OnboardingState.Installing(0, 0),
		OnboardingState.Installing(3, 12),
		OnboardingState.PairingPhone,
		OnboardingState.PairAdapter,
		OnboardingState.Done,
		OnboardingState.Failed("finding_pi", true, "The server could not be reached."),
		OnboardingState.Failed("authorizing", false, "The activation key was refused."),
	)

	@Test
	fun everyStateHasTitleAndBody() {
		for (s in every) {
			val ui = uiModelFor(s)
			assertTrue("$s", ui.title.isNotBlank() && ui.body.isNotBlank())
		}
	}

	@Test
	fun welcomeAndKeyButtons() {
		assertEquals("Start", uiModelFor(OnboardingState.Welcome).primaryLabel)
		assertEquals("Continue", uiModelFor(OnboardingState.EnterActivationKey).primaryLabel)
		assertEquals("Install", uiModelFor(OnboardingState.FirstSetup).primaryLabel)
	}

	@Test
	fun pairingStepsUsePairVehicleTitleAndExplainDialogsFirst() {
		val phone = uiModelFor(OnboardingState.PairingPhone)
		assertEquals("Pair vehicle", phone.title)
		assertEquals("Continue", phone.primaryLabel)
		assertTrue(phone.body.contains("Android will ask you to confirm Bluetooth pairing and to add the MIA Wi-Fi network"))
		assertTrue(phone.body.contains("If you cancel one you can try again here."))
		val adapter = uiModelFor(OnboardingState.PairAdapter)
		assertEquals("Pair vehicle", adapter.title)
		assertEquals("Skip", adapter.secondaryLabel)
		assertEquals("Install MIA on a car", uiModelFor(OnboardingState.Welcome).title)
	}

	@Test
	fun retryableFailureOffersTryAgainOtherwiseStartOver() {
		val retry = uiModelFor(OnboardingState.Failed("installing", true, "m"))
		assertEquals("Try again", retry.primaryLabel)
		assertEquals("Start over", retry.secondaryLabel)
		val fatal = uiModelFor(OnboardingState.Failed("authorizing", false, "m"))
		assertEquals("Start over", fatal.primaryLabel)
		assertNull(fatal.secondaryLabel)
		assertEquals("m", fatal.body)
	}

	@Test
	fun installingShowsPlainProgress() {
		val ui = uiModelFor(OnboardingState.Installing(3, 12))
		assertEquals("Sent 3 of 12", ui.body)
		assertEquals(0.25f, ui.fraction!!, 0.0001f)
		assertTrue(ui.busy)
		assertNull(uiModelFor(OnboardingState.Installing(0, 0)).fraction)
		assertEquals(1f, uiModelFor(OnboardingState.Installing(9, 4)).fraction!!, 0f)
	}

	@Test
	fun waitingStatesHaveNoMainButtonAndShowProgress() {
		for (s in listOf(OnboardingState.FindingPi, OnboardingState.Authorizing)) {
			val ui = uiModelFor(s)
			assertNull("$s", ui.primaryLabel)
			assertTrue("$s", ui.busy)
		}
		assertEquals("Looking for your Pi on this network", uiModelFor(OnboardingState.FindingPi).body)
		assertNotNull(uiModelFor(OnboardingState.FindingPi).secondaryLabel)
		assertEquals("Your car is set up", uiModelFor(OnboardingState.Done).body)
	}

	@Test
	fun noModelStringContainsAKeyPlaceholder() {
		val secret = "MIA-ACTIVATION-SECRET-0123"
		for (s in every) {
			val ui = uiModelFor(s)
			for (t in listOfNotNull(ui.title, ui.body, ui.primaryLabel, ui.secondaryLabel)) {
				assertFalse("$s: $t", t.contains(secret) || t.contains("grant", ignoreCase = true) || t.contains("{key}"))
			}
		}
	}
}
