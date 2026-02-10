package cz.mia.app

import android.content.Intent
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import cz.mia.app.core.background.DrivingService
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DrivingServiceInstrumentedTest {
	@Test
	fun startAndStopService_skeleton() {
		val context = ApplicationProvider.getApplicationContext<android.content.Context>()
		val start = Intent(context, DrivingService::class.java).apply { action = DrivingService.ACTION_START }
		context.startForegroundService(start)
		val stop = Intent(context, DrivingService::class.java).apply { action = DrivingService.ACTION_STOP }
		context.startService(stop)
		// TODO: add IdlingResource and assertions when build env is ready
	}
}
