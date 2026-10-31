# 0021. The car's microphone is the phone's, streamed to the Pi

- Status: Proposed
- Date: 2026-10-31
- Requirements: REQ-VOICE-027, REQ-AND-027

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
- Server to phone, text: `{"mic":"open"|"muted","reason":"speaking"}`, for the indicator only.
- One audio WebSocket at a time: a new one replaces the old, which is closed with 1008.
- `api/audio_ingest.py` pushes to a ZeroMQ PUSH socket (high-water mark 8, no blocking, drop when full).

**Pi side.**
- `audio_capture.py` stays the only holder of the PUB socket on 5558. It reads the ingest PULL into a 10-frame
  deque (drop the oldest, jitter target 3 frames); its existing 30 ms timer is the single pacer.
- `AUDIO_SOURCE=auto|usb|phone`. In `auto` the phone is used if a frame arrived less than 500 ms ago, else the
  local device, else silence. Sources are never mixed.
- The speaking gate (REQ-VOICE-016) applies to the chosen frame, with a longer tail for the phone
  (`MIC_TAIL_SEC` about 0.8 s, because of network delay), and buffered phone frames are flushed when the gate closes.

**Privacy.** Off by default and per session; the notification is mandatory; the Pi never writes raw audio; logs hold
counts and drops only.

## Consequences
- The pipeline from `mia/audio/raw` on is unchanged, so wake word, recognition and the router need no change.
- Audio crosses the car Wi-Fi in clear text with the API key (ADR-0016), accepted for the prototype.
- Latency and echo (the phone hears the Pi's headphone output) are unmeasured; the gate tail is a guess.
- This ADR is design only. Nothing is implemented in the PR that records it, so both requirements stay `planned`.

## Sources
`apps/rpi-backend/py-api/services/audio_capture.py`, `services/stt_service.py`, `services/voice_fsm/mic_gate.py`,
`spec/interfaces/voice.md`, ADR-0014, ADR-0016, ADR-0020.
