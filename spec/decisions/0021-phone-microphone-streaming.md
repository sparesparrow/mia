# 0021. The car's microphone is the phone's, streamed to the Pi

- Status: Accepted
- Date: 2026-10-31
- Requirements: REQ-VOICE-027, REQ-AND-027, REQ-VOICE-030, REQ-AND-028

## Context
The Pi 4B in the car has no microphone and no capture device; it has a headphone jack for playback. The phone
has a good microphone and is already on the Pi's Wi-Fi (ADR-0016). Speech recognition on the Pi (REQ-VOICE-008)
needs 16 kHz mono audio on `mia/audio/raw` (REQ-VOICE-005). Recognition stays English (REQ-VOICE-023).

Streaming a microphone raises privacy questions (ADR-0014) and Android has rules for background microphone use.

## Decision
**Phone side (REQ-AND-027).**
- Permissions `RECORD_AUDIO` and `FOREGROUND_SERVICE_MICROPHONE`; a `MicStreamService` with
  `foregroundServiceType=microphone`, started by the user from the Voice tab toggle while the app is in the
  foreground (an Android 14 rule), with a persistent notification that has a Stop action.
- `AudioRecord` with `VOICE_RECOGNITION`, 16000 Hz, mono, PCM16, frames of 480 samples (960 bytes, 30 ms). Capture
  never blocks: when the WebSocket queue holds more than 6 frames, frames are dropped. Reconnect after 1, 2, 4 s.
- Push-to-talk first: stream only from the console Wake until the machine leaves `listening` (driven by
  `StateChanged`). Always-on streaming comes later.

**Wire.**
- `/ws/audio` in `mia-api`, `X-API-Key` with `write` scope, enabled only with `VOICE_PHONE_MIC=1` (off by default).
- The first frame is text: `{"v":1,"fmt":"s16le","rate":16000,"ch":1,"frame_ms":30}`. The answer is `{"ok":true}`
  or close 1003. Then binary frames, each a whole multiple of 960 bytes (others are dropped and counted).
- Server to phone, text: `{"mic":"open"|"muted","reason":"speaking"}`, for the indicator only. Not sent yet; the phone
  ignores any text other than `{"ok":true}`.
- One audio WebSocket at a time: a new one replaces the old, which is closed with 1008.
- `api/audio_ingest.py` pushes to a ZeroMQ PUSH socket (high-water mark 8, no blocking, drop when full). The
  capture service binds the PULL side on loopback `AUDIO_INGEST_PORT` (default 5566), the API connects.
- `authenticate_websocket(websocket, scope)` takes the scope the key must hold; `/ws/voice` keeps `read`, `/ws/audio`
  asks for `write`. Authentication comes before the `VOICE_PHONE_MIC` check, so a probe cannot tell whether the
  feature is on.

**Pi side.**
- `audio_capture.py` stays the only holder of the PUB socket on 5558. It reads the ingest PULL into a 10-frame
  deque (drop the oldest, jitter target 3 frames); its existing 30 ms timer is the single pacer.
- The logic lives in `services/mic_source.py` (injected clock, no ZeroMQ or sound card), so it is unit tested. The
  30 ms tick is the sound device's callback or, on a Pi with no capture device (the real car Pi), the simulation
  loop; both ask `MicSource.next_frame`. After an underrun the buffer refills to 3 frames before playing again.
- `AUDIO_SOURCE=auto|usb|phone`. In `auto` the phone is used if a frame arrived less than 500 ms ago, else the
  local device, else silence. Sources are never mixed.
- The speaking gate (REQ-VOICE-016) applies to the chosen frame, with a longer tail for the phone
  (`MIC_TAIL_SEC` about 0.8 s, because of network delay), and buffered phone frames are flushed when the gate closes.

**Audio Settings (REQ-VOICE-030, REQ-AND-028).**
- The Pi owns the choice (ADR-0019): `GET /audio/settings` and `PUT /audio/settings` (write scope) in `mia-api`. The
  choice is `mic_transport` (`wifi`, `bluetooth`) and `reply_output` (`pi_speaker`, `bluetooth_phone`,
  `phone_speaker`), kept in `audio_settings.json` in `MIA_STATE_DIR`. It is a file of its own, not fields of
  `voice_settings.json`, because the voice router rewrites that file with only the fields it knows and would erase them.
- `GET` reports the stored choice, the `effective` choice and a `capabilities` map. A request for an unavailable
  option gets 409 `unavailable` and is not stored. The Android screen shows what the Pi reports, greys out what it
  cannot do and writes only through the Pi.
- Only `wifi` and `pi_speaker` are available today.

**Bluetooth audio: the gap.** Checked read-only on the car Pi (BlueZ 5.82, controller powered, name `mia`; only the
BLE GATT units `mia-ble-advertiser` and `mia-ble-obd` use it): there is no bluealsa, no PipeWire or WirePlumber
daemon, no PulseAudio and no `libspa-bluetooth`, so BlueZ has nothing to hand A2DP or HFP audio to. Nothing was
installed and nothing is faked: `bt_audio_available` is false and Bluetooth options are refused. What a real path
needs, as a decision for the owner because it changes the Pi's system: `pipewire-audio` with `wireplumber` (or
`bluealsa` with oFono or hsphfpd for HFP), a BlueZ A2DP sink and HFP policy, a pairing flow in the app, and then the
probe in `api/routers/audio_settings.py` plus the routing itself. `phone_speaker` is unavailable for a different
reason: no reply audio is sent to the phone.

**Privacy.** Off by default and per session; the notification is mandatory; the Pi never writes raw audio; logs hold
counts and drops only.

## Consequences
- The pipeline from `mia/audio/raw` on is unchanged, so wake word, recognition and the router need no change.
- Audio crosses the car Wi-Fi in clear text with the API key (ADR-0016), accepted for the prototype.
- Latency and echo (the phone hears the Pi's headphone output) are unmeasured; the gate tail is a guess.
- Implemented for the Wi-Fi microphone with unit tests only. No phone and no Pi were used, so latency, echo and the
  Android service on a real device are unproven, and the Kotlin was written without an SDK to compile it.
- Only the `listening` state streams. Dictation and a spoken yes/no also need audio; adding their states to
  `PushToTalk` is the next step once the first drive shows the delay.
- Two phones on one Pi take turns closing each other (1008, then reconnect after 1 s); the app does not yet treat 1008
  as "someone else took over".
- Bluetooth audio and replies to the phone are not built; see the gap above.

## Sources
`apps/rpi-backend/py-api/services/audio_capture.py`, `services/stt_service.py`, `services/voice_fsm/mic_gate.py`,
`api/audio_ingest.py`, `api/routers/audio_settings.py`, `services/mic_source.py`, `spec/interfaces/voice.md`, ADR-0014, ADR-0016, ADR-0020.
