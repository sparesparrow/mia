# Voice command set review

> **Scope**: a read-only review of the current voice commands against seven design principles. No behaviour
> changes here. **Evidence level**: every statement comes from reading the code and the specs; nothing was run
> on a Pi, in a car or with a real microphone (ADR-0010). The existing unit tests are simulation-level and were
> not extended.

Inputs: `apps/rpi-backend/py-api/services/voice_command_router.py`, `.../voice_fsm/`, `.../stt_service.py`,
[`spec/interfaces/voice.md`](../interfaces/voice.md), `spec/requirements/voice.yaml`, ADR-0011, ADR-0012,
ADR-0014, ADR-0020.

Paths below are relative to `apps/rpi-backend/py-api/services/`.

Context: a car. Push-to-talk through the console or the steering-wheel Wake, no wake word by default
(ADR-0020). The driver cannot look at a screen and cannot easily repeat a command.

## Current command set

Seven routes (`voice_command_router.py:88-164`): system status, processor temperature, engine telemetry,
connected devices, feature list, lights off, lights on. Five are reads, two are comfort. Plus spoken settings
(quiet/normal/chatty mode, persona, language) in `voice_fsm/bridge.py:78-88`, and the yes/no/stop answers. The
machine also knows message, call, note and forbidden actions (`voice_fsm/classes.py:42-51`), but no route or
splitter can produce them yet (REQ-VOICE-020 is `planned`).

## Findings, by severity

### High

**H1. The default router path confirms on substrings and checks "yes" before "no".**
`voice_command_router.py:550-555` uses `any(w in text_lower ...)` over `YES_WORDS`, and tests yes first. "ok"
matches inside "look", "book"; "no" matches inside "know", "not". "No, that's not okay" is read as a yes. The
legacy loop is what runs unless `VOICE_FSM=1` (`:486`, default `"0"`). The FSM bridge already does this right
(word boundaries, at most three words, no wins: `voice_fsm/bridge.py:112-114,176-186`). Principle: confirm
interpretation. Today only a read or a comfort action can be wrongly confirmed, because the legacy loop has no
message or call route, but the same loop would carry any route added later.

**H2. Without a wake word, a spoken yes, no or stop has no recorder in `window` and `confirming`.**
`stt_service.py:236-247` records only after a `mia/voice/wake` or `mia/voice/listen` event. The machine accepts
`Wake` as a state change only from `idle` (`voice_fsm/machine.py:394-399`), so a Wake in `window` or
`confirming` does not start `listening`, and the router publishes `listen` only when it does
(`voice_fsm/bridge.py:157-165`). From the code, a spoken "stop" in the window or a spoken "yes" to a question
cannot reach the machine in push-to-talk mode; only the buttons can (`spec/interfaces/voice.md`, "Rules for the
buttons"). The announcement says "Say stop or press cancel" (`voice_fsm/phrases.py:15`), which promises a
path the pipeline may not have. Unverified: not run end to end; the answer to this needs a scenario in the
harness (REQ-VOICE-028).

**H3. Nothing knows the car is moving.**
There is no ignition, speed or parking input to the machine; `Event(kind, data)` for ignition and parking is
`planned` (`spec/interfaces/voice.md`, Commands). Only the forbidden class is refused, always
(`voice_fsm/machine.py:360`). Dictation, messages and calls are not deferred or refused by motion, and a
message or call can be confirmed by a spoken "okay" or "sure" (`voice_fsm/bridge.py:49-61`) that a passenger
or the radio can also produce. The persona text already depends on `params.moving` (`spec/interfaces/voice.md`,
Personas), so the value is expected from somewhere that does not exist. Principle: safety-critical actions
confirmed or refused while driving. Today this is harmless only because no message, call or note route exists.

### Medium

**M1. Substring keyword matching gives false hits on ordinary speech.**
`_score_route` uses `kw in text` (`voice_command_router.py:179`), not word matching. "led" matches "called",
"installed"; "on" matches "condition"; "temp" matches "attempt"; "hot", "off", "list", "what" all match inside
longer words. "I called the dealer, turn it off" scores 1.0 for lights off (`led` plus `off`) and runs at once.
A one-line fix in the router is small, but it changes behaviour, so it is a follow-up, not part of this review.

**M2. Ties and near-ties are resolved silently, and the wrong route can win.**
`route_command` keeps the first route with the highest score (`:198`, strict `>`) and returns only that one
(`:206`). "What is the temperature" scores 0.5 for processor temperature and 0.33 for engine telemetry, so it
reads the Pi's CPU temperature; in a car the driver almost always means coolant. "How hot is the engine" gives
the same CPU answer. "Lights on or off" ties and lights off wins. No alternative is offered. Principle:
unambiguous commands; ask for clarification when uncertain.

**M3. Anything with "what", "show", "list" or "help" is answered as a command instead of a fallback.**
Connected devices takes `{"list","show","what"}` as one concept (`:123-131`), so "what time is it" scores 0.5
and, in FSM mode, runs after the five second window when the driver says nothing (`voice_fsm/machine.py:371-378`,
REQ-VOICE-012). Silence runs an unrelated read. Principle: graceful fallback. The two-concept scoring means a
single weak word is enough to reach the window.

**M4. "Did you mean" and the announcement name an internal label, and never what was heard.**
Both modes say the route label (`voice_command_router.py:595`, `voice_fsm/phrases.py:15`), and the unknown case
says only "Sorry, I didn't understand" (`voice_fsm/phrases.py:20`, `voice_fsm/machine.py:348`). The legacy
loop instead reads the raw transcript back (`voice_command_router.py:573`), which repeats a misrecognition in
full. Neither says "I heard X" in a short form, and neither offers the second-best choice. Principle: confirm
interpretation; ask for clarification.

**M5. The speech-recognition confidence is not used, and the field is wrong.**
`stt_service.py:119` sets `confidence` to `1 - language_probability`, which is a language-identification score
turned upside down, not recognition confidence. The router reads only `text` (`voice_command_router.py:467`,
`:534`). A noisy cabin (roof down, cabriolet) produces a clean-looking wrong sentence that the keyword scorer
then trusts. Principle: ask for clarification when uncertain.

**M6. Every transcript is written to the system log, outside the retention rules.**
`voice_command_router.py:540` and `:567` log the full transcript; `stt_service.py:284` does the same. ADR-0014
limits transcripts to the Pi with a 30 day retention and an owner-set switch; the journal has neither.
In FSM mode the router adds no transcript logging, but the STT service still does. The legacy response event
also carries `source_transcript` (`:340`). Principle: privacy; nothing sensitive stored without consent. The
log of REQ-VOICE-021 is `planned`, so today nothing implements the consented, bounded store; this is the
unconsented, unbounded one.

**M7. The command set is English only, and the speech is Czech-capable.**
Keywords are English (`voice_command_router.py:88-164`), `WHISPER_LANGUAGE` defaults to `en`
(`stt_service.py:12`). MIA can speak Czech (`spec/interfaces/voice.md`, "Spoken answers") but not understand it
(#179, REQ-VOICE-023 `planned`). A Czech-speaking driver gets answers in a language whose commands they must
still say in English. Principle: natural phrasing.

### Low

**L1. The action table lists actions no route can produce.**
`voice_fsm/classes.py:24-52` has volume, `read.*`, `dtc.read`, message, call and note entries; `ROUTES` has
none of them. Not wrong (fail-closed by design), but the table reads like a vocabulary that does not exist, and
the "help" answer cannot list it.

**L2. "What can you do" lists software features, not voice commands.**
`_format_features` (`voice_command_router.py:248-252`) says "MIA has N features: ..." from the feature
registry. A driver learns nothing about what to say. Principle: natural phrasing; graceful fallback.

**L3. Lights are ambiguous.**
"Turn the lights on" drives the LED node (`:149-163`) with a fixed brightness of 128, with no word for which
lights. A driver may mean the headlights or the cabin light. Principle: unambiguous commands. The action never
touches the vehicle bus (ADR-0006), so the risk is confusion, not actuation of the car.

**L4. The two modes disagree about silence.**
Legacy: silence on a low-confidence match cancels (`voice_command_router.py:522-527`). FSM: silence on an
uncertain read or comfort part runs it (REQ-VOICE-012). Both are documented choices, but the same utterance
behaves oppositely depending on `VOICE_FSM`.

**L5. The public sockets bind on all interfaces.**
Router, wake and TTS publishers use `tcp://*` (`voice_command_router.py:401,508`; `wake_word.py:154`;
`tts_service.py:212`). Responses (and, in legacy mode, transcripts) go to anything that can reach the port. A
firewall may hide this on the Pi; none was checked here.

## What already meets the principles

Fail-closed action classes: a label can only make a part stricter and an unknown name is forbidden
(`voice_fsm/classes.py:55-64`). Message and call parts never run on silence (REQ-VOICE-013). Vehicle writes
are refused aloud (`voice_fsm/machine.py:360`, REQ-VOICE-014). A long reply is treated as a correction, not as
a yes (`voice_fsm/bridge.py:176`). Cancel works by button without recognition (REQ-VOICE-015). Recognition
(faster-whisper, `stt_service.py:1-12`), speech (piper with espeak fallback) and the router's HTTP target
(`localhost`) are all on the Pi; offline operation is by design but was not measured here. All of this is
`implemented_and_ci_tested` at most, with a fake clock and fakes (see `not_proven` in `spec/requirements/voice.yaml`).

## Principle summary

| Principle | State | Findings |
|---|---|---|
| Unambiguous commands | weak | M1, M2, L3 |
| Natural phrasing | weak (English keywords only) | M7, L2 |
| Confirm interpretation | partial | H1, M4 |
| Ask for clarification | partial (go/cancel only) | H2, M2, M5 |
| Graceful fallback | weak | M3, L2 |
| Work offline | by design, unmeasured | none |
| Privacy | partial | M6, L5 |
| Safe while driving | not covered | H3 |

## Follow-ups

Tracked as GitHub issues, not in this file. Each needs a requirement before behaviour code
(`spec/README.md`); none is added here.
