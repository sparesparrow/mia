# 0020. The voice router owns the machine; mia-api relays /ws/voice to it over ZeroMQ

- Status: Proposed
- Date: 2026-10-31
- Requirements: REQ-VOICE-024, REQ-VOICE-025, REQ-VOICE-026, REQ-VOICE-028, REQ-AND-026

## Context
The Android Voice console talks to `/ws/voice` (ADR-0013). Behind that endpoint sits a voice machine that lives in
the `mia-api` process and is driven by a simulated speaker. The real pipeline (audio capture, wake word, speech to
text, `voice_command_router`, text to speech) has its own machine in the router process (ADR-0011). So a button
pressed in the app moves a machine that hears nothing and speaks to nobody, and a spoken command never reaches the
app's console. ADR-0019 already named this: two processes, two machines, one settings file, no talk between them.

The product decisions behind this ADR:

- The console must drive the real pipeline now.
- There is no wake word; a console or steering-wheel Wake is the push-to-talk route.
- Typed commands and steering-wheel presets are required (later PRs; this ADR fixes where they enter).
- Tests simulate the user's speech with text to speech injected digitally.

## Decision
1. **One owner.** `services/voice_command_router.py` (`VOICE_FSM=1`) is the only process that holds a `VoiceMachine`.
   `mia-api` holds none. The simulated machine stays only as a development backend, `VOICE_CONSOLE_BACKEND=sim`.
2. **A loopback door on the router.** The router binds a ZeroMQ ROUTER socket on `127.0.0.1:5565`
   (`VOICE_CONSOLE_PORT`) that hosts the existing `EnvelopeRouter`. Each peer identity is one `Connection`; envelope
   bytes (MIAV FlatBuffers) pass through unchanged. An EMPTY frame from a peer means it is gone. The frames `ping`
   and `pong` are liveness only; no envelope is that short.
3. **The API is a dumb relay.** `/ws/voice` authenticates (`X-API-Key`, as before), opens one DEALER per WebSocket and
   forwards binary frames both ways without decoding them. When the WebSocket ends it sends one empty frame. It
   pings every 2 s; after 6 s without a word from the router it closes the WebSocket with 1013 "voice router
   offline". The 256-frame outbox and the close codes 1008, 1003 and 1013 stay. Code: `api/voice_relay.py`;
   `voice_console.serve` picks the backend. The default stays `sim` until the router backend has run on a Pi, then
   it moves to `router`.
4. **The router side is event driven.** A `BridgeVoiceService` takes a decoded, permitted command and calls
   `bridge.submit(command)`, which applies the effects once (speech, cues, settings, actions) and returns them.
   `RouterBridge.observers` are told about every effect list and transcript, whatever started it (speech, a console,
   text to speech, the clock). The service encodes them and the hub broadcasts them, so every console sees the
   effects of every origin. The service never ticks the machine; the router loop's `bridge.poll()` does.
5. **Console commands.** `PEER_COMMANDS` is unchanged, and the channel stamps `Source.CONSOLE`. Settings changes go
   through the machine in the router, the only writer of `voice_settings.json`; the settings snapshot on `Open` comes
   from that machine.
6. **Typed text enters at transcript level (PR-B).** A new peer message `TypedText{text}` with no source field is
   allowed only through a separate allowlist `PEER_TEXT`. The service calls
   `bridge.on_transcript(text, source=Source.TYPED)`, the path a recognised utterance takes (yes and no rules,
   spoken settings, classification, the action classes of ADR-0012). `Intent` and `DictationText` stay refused from
   peers (ADR-0011, ADR-0013).
7. **Steering wheel (PR-B).** The existing buttons (Wake, GoNow, Cancel, Confirm, Deny) plus `Preset{name}`. The Pi
   resolves a preset from a fixed table (`services/voice_fsm/presets.py`) to an English phrase and runs it through
   `on_transcript(phrase, Source.BUTTON)`. The phone sends only the name; the list comes in `Settings`.
8. **Wake and recognition.** With no wake word, the router publishes `mia/voice/listen` on its existing PUB (5561)
   when a Wake whose source is not `voice` puts the machine into `listening`. `stt_service` subscribes to it as well
   as to `mia/voice/wake`, so a console or wheel Wake starts a recording.
9. **Authorization (PR-B).** Connecting and observing needs a `read` key; sending any command needs `write`; `TypedText`
   and `Preset` need `write`; a read key gets `NotPermitted`. Typed text is capped at 200 characters, control
   characters are stripped, at most 5 per 10 s per connection, and logged as length and hash (the text itself only
   with `VOICE_LOG_TEXT=1`, ADR-0014). The key crosses the car Wi-Fi in clear text (ADR-0016); accepted for the prototype.

Rejected: a machine in `mia-api`; Android straight to a WebSocket on the router; two machines synced over ZeroMQ;
relaying the JSON topics; accepting `Intent` from a console; publishing typed text on `mia/voice/transcript` (port
5560 is bound by `stt_service`, and it would forge the voice source).

## Consequences
- One machine and one settings writer. The two-process caveat of ADR-0019 ends for the router backend.
- Router down means console down (1013). The `sim` backend remains for development.
- A new local port, 5565, listed in `spec/interfaces/voice.md`. It binds to loopback and the API is the only client.
- The router's `_execute_action` is a synchronous HTTP call of up to 5 s inside the loop, so a console is silent
  while an action runs. A follow-up must move it to a worker thread.
- This PR changes no schema. Typed text, presets and the scope check need `schemas/voice.fbs` and the generated
  Python, Kotlin and C++ bindings (PR-B), so REQ-VOICE-025 and 026 stay `planned`.
- A relay that dies without an empty frame leaves its connection in the hub until it has been silent for 10 s.

## Sources
`apps/rpi-backend/py-api/services/voice_command_router.py`, `services/voice_fsm/bridge.py`,
`services/voice_fsm/wire/` (`router.py`, `bridge_service.py`, `zmq_hub.py`), `api/voice_console.py`,
`api/voice_relay.py`, `services/stt_service.py`, `spec/interfaces/voice.md`, ADR-0011, ADR-0012, ADR-0013, ADR-0014,
ADR-0016, ADR-0019.
