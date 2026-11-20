package cz.mia.app.ui.components

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.core.content.ContextCompat
import cz.mia.app.core.voice.mic.MicLink
import cz.mia.app.core.voice.mic.MicStreamController
import cz.mia.app.core.voice.mic.MicStreamService

/**
 * The switch that sends the phone's microphone to the Pi (ADR-0021, REQ-AND-027). Off by default and per session:
 * switching on asks for the microphone permission, starts the foreground service (it shows a notification with
 * Stop) and from then on audio leaves the phone only while the Pi's machine is listening.
 */
@Composable
fun PhoneMicSection(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val enabled by MicStreamController.enabled.collectAsState()
    val talking by MicStreamController.talking.collectAsState()
    val link by MicStreamController.link.collectAsState()

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) startMic(context)
    }

    SectionCard(title = "Phone microphone") {
        Row(
            modifier = modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Use this phone as MIA's microphone", modifier = Modifier.weight(1f))
            Switch(
                checked = enabled,
                onCheckedChange = { on ->
                    when {
                        !on -> stopMic(context)
                        hasMicPermission(context) -> startMic(context)
                        else -> permission.launch(Manifest.permission.RECORD_AUDIO)
                    }
                },
                modifier = Modifier.testTag("phone_mic_switch"),
            )
        }
        Text(
            text = micStatusText(enabled, link, talking),
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.testTag("phone_mic_status"),
        )
    }
}

/** What the switch's state means, in words; also the only place the three facts are put together. */
fun micStatusText(enabled: Boolean, link: MicLink, talking: Boolean): String = when {
    !enabled -> "Off. Nothing leaves the phone."
    link == MicLink.CONNECTING -> "Connecting to the Pi..."
    link == MicLink.OFF -> "Starting..."
    talking -> "Sending: MIA is listening"
    else -> "Ready: sends only while MIA is listening"
}

private fun hasMicPermission(context: Context): Boolean =
    ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

private fun startMic(context: Context) {
    ContextCompat.startForegroundService(
        context,
        Intent(context, MicStreamService::class.java).setAction(MicStreamService.ACTION_START),
    )
}

private fun stopMic(context: Context) {
    context.startService(Intent(context, MicStreamService::class.java).setAction(MicStreamService.ACTION_STOP))
}
