# 0021. The phone supplies internet and microphone audio over USB tethering

- Status: Accepted
- Date: 2026-11-20
- Requirements: REQ-VOICE-027, REQ-AND-027, REQ-AND-028

## Context

The Pi 4B has no built-in microphone. It already runs the voice pipeline locally and can play speech through its
ALSA output. The Android phone has a microphone and mobile data, and is physically connected to the Pi's USB 3 port.
The intended test path is one cable for the Pi's internet connection and for the app's microphone stream, with the Pi
speakers playing MIA's replies.

The app cannot silently start recording. Android requires the user to grant microphone permission and makes
background microphone use visible. USB tethering is also a system network setting, so the user enables it on the
phone and the Pi's network manager obtains an address by DHCP. The app then connects to the Pi's USB-network address
from Settings. Speech recognition and synthesis remain on the Pi; the phone's mobile connection is available to
other configured services.

## Decision

**USB network.** The phone is the USB tether host and provides internet access to the Pi. The user enables USB
tethering in Android settings. The Pi accepts DHCP on the USB network interface (`usb0` or its `enx...` name), and
the app uses the Pi's address on that link. The app does not attempt to enable tethering.

**Phone microphone.** The Voice tab has a Start/Stop microphone control. Starting it requests `RECORD_AUDIO` and
launches a foreground `MicStreamService` with `foregroundServiceType=microphone` and a persistent Stop notification.
The service captures 16 kHz mono PCM16 in 30 ms frames. It sends audio only while running and bounds its outgoing
WebSocket queue to six frames, dropping frames when the USB link falls behind. Reconnect delays grow from 1, 2 and
4 seconds, capped at 30 seconds.

**Wire and Pi ingest.** `/ws/audio` is enabled only with `VOICE_PHONE_MIC=1`. It requires a `write`-scope API key and
one active phone session. The first text frame declares `{"v":1,"fmt":"s16le","rate":16000,"ch":1,"frame_ms":30}`;
the server acknowledges it before accepting binary PCM frames. The API uses a bounded ZeroMQ PUSH socket to
`127.0.0.1:5564`. `audio_capture.py` owns the PULL socket and remains the only publisher of `mia/audio/raw` on port
5558. Invalid or late frames are dropped and only counts are logged.

**Audio source and speaker.** `AUDIO_SOURCE=auto|usb|phone` selects the input. `auto` uses a fresh phone frame when
one arrived in the last 500 ms, otherwise the local USB microphone, otherwise silence. `phone` uses silence when the
phone stream is stale; sources are never mixed. The existing speaking gate mutes the chosen source while MIA speaks,
uses an 800 ms tail for phone input and clears queued phone frames when the gate closes. TTS continues to play from
the Pi's configured ALSA output (`AUDIO_OUTPUT_DEVICE`); the user connects speakers to the Pi and selects the matching
ALSA device if the default is not correct.

**Voice test.** The user starts the phone microphone, presses Wake in the Voice tab, speaks a command and listens to
the Pi's speaker for MIA's response. The real path requires `VOICE_CONSOLE=1`, `VOICE_CONSOLE_BACKEND=router`,
`VOICE_FSM=1`, the voice router/STT/TTS services and working Pi speakers.

**Privacy.** The stream is off by default, user-started and visibly stoppable. The Pi never writes raw microphone
frames. The API accepts no more than one phone stream, uses bounded queues, and records counts and drops only. The
prototype still uses the API's plain HTTP/WebSocket transport (ADR-0016); the API key and audio are visible to peers
on the tether link.

## Consequences

- The phone supplies both the Pi's network uplink and the microphone source through the same physical USB connection.
- The Pi remains responsible for wake, speech recognition, command handling, speech synthesis and speaker playback.
- USB tether interface naming and DHCP depend on the Pi OS network manager. The setup script supports NetworkManager
  and `dhcpcd`; the operator still discovers the Pi's USB address and enters it in the app. Multicast discovery is
  not relied on over tethering.
- A phone disconnect or stalled stream falls back to the local microphone in `auto` mode. The explicit `phone` mode
  outputs silence until frames resume.
- Implementation is present, but the tether, microphone path, echo behaviour and speaker output have not been
  verified on the physical phone and Pi.

## Sources

`apps/android/app/src/main/AndroidManifest.xml`,
`apps/android/app/src/main/java/cz/mia/app/core/voice/MicStreamService.kt`,
`apps/android/app/src/main/java/cz/mia/app/ui/screens/VoiceConsoleScreen.kt`,
`infra/deploy/rpi/setup-usb-tether.sh`, `apps/rpi-backend/py-api/api/audio_ingest.py`, `api/main.py`,
`services/audio_capture.py`, `services/tts_service.py`, `spec/interfaces/voice.md`, ADR-0014 and ADR-0016.
