package cz.mia.app

// @req REQ-AND-007

import android.Manifest
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.SystemClock
import androidx.test.core.app.ApplicationProvider
import androidx.test.espresso.IdlingRegistry
import androidx.test.espresso.IdlingResource
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.ServiceTestRule
import cz.mia.app.core.background.DrivingService
import cz.mia.app.core.background.ServiceState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DrivingServiceInstrumentedTest {
    @get:Rule
    val serviceRule = ServiceTestRule()

    @Test
    fun pauseAndResume_updatesObservableStateAndKeepsForegroundNotification() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        grantForegroundServiceRuntimePermissions(context)

        val binder = serviceRule.bindService(Intent(context, DrivingService::class.java))
        val service = (binder as DrivingService.DrivingServiceBinder).getService()

        assertEquals(ServiceState.STOPPED, service.serviceState.value)

        val notifications = context
            .getSystemService(NotificationManager::class.java)
            .activeNotifications
        assertTrue("DrivingService must publish a foreground notification", notifications.isNotEmpty())

        try {
            context.startService(
                Intent(context, DrivingService::class.java).apply {
                    action = DrivingService.ACTION_PAUSE
                },
            )
            awaitState(service, ServiceState.PAUSED)

            context.startService(
                Intent(context, DrivingService::class.java).apply {
                    action = DrivingService.ACTION_RESUME
                },
            )
            awaitState(service, ServiceState.RUNNING)
        } finally {
            context.stopService(Intent(context, DrivingService::class.java))
        }
    }

    private fun awaitState(service: DrivingService, expected: ServiceState) {
        val resource = ServiceStateIdlingResource(service, expected)
        IdlingRegistry.getInstance().register(resource)
        try {
            val deadline = SystemClock.uptimeMillis() + 5_000
            while (!resource.isIdleNow && SystemClock.uptimeMillis() < deadline) {
                SystemClock.sleep(20)
            }
            assertTrue(
                "Timed out waiting for DrivingService state $expected; actual=${service.serviceState.value}",
                resource.isIdleNow,
            )
            assertEquals(expected, service.serviceState.value)
        } finally {
            IdlingRegistry.getInstance().unregister(resource)
        }
    }

    private fun grantForegroundServiceRuntimePermissions(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return

        val automation = InstrumentationRegistry.getInstrumentation().uiAutomation
        automation.grantRuntimePermission(context.packageName, Manifest.permission.CAMERA)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            automation.grantRuntimePermission(context.packageName, Manifest.permission.BLUETOOTH_CONNECT)
            automation.grantRuntimePermission(context.packageName, Manifest.permission.BLUETOOTH_SCAN)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            automation.grantRuntimePermission(context.packageName, Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private class ServiceStateIdlingResource(
        private val service: DrivingService,
        private val expected: ServiceState,
    ) : IdlingResource {
        @Volatile
        private var callback: IdlingResource.ResourceCallback? = null

        override fun getName(): String = "DrivingService[$expected]"

        override fun isIdleNow(): Boolean {
            val idle = service.serviceState.value == expected
            if (idle) {
                callback?.onTransitionToIdle()
            }
            return idle
        }

        override fun registerIdleTransitionCallback(callback: IdlingResource.ResourceCallback) {
            this.callback = callback
            if (isIdleNow) {
                callback.onTransitionToIdle()
            }
        }
    }
}
