# 0011. One voice state machine is the single source of commands and feedback

- Status: Proposed
- Date: 2026-10-12
- Requirements: REQ-VOICE-011, REQ-VOICE-015, REQ-HW-009

## Context
The Pi voice services (`audio_capture`, `wake_word`, `stt_service`, `voice_command_router`,
`tts_service`) each decide for themselves what happens next. The router keeps its own
confirmation state inline in `main()`, TTS never says when it has finished, and no service
tells the LED strip what the assistant is doing. A steering-wheel button, the Android app and
a spoken command would each need their own path to the same action.

## Decision
- A single state machine in MIA owns the voice session. It consumes **commands** and emits
  **effects**: an action to execute, text to speak, an LED colour and a tone.
- Every input is normalised to the same typed command before it reaches the machine: a
  recognised phrase, a button press, a car event or a rule firing. Voice and button therefore
  produce the same command and the same effects.
- LED and tone are effects of the machine, driven by one table (state to colour to tone). No
  service lights an LED or plays a cue on its own.
- The machine is pure logic with an injected clock, so it is tested without audio, a car or
  a sleep (ADR-0007).
- Long-running work, such as a chain waiting in its confirmation window, is a job with status,
  abort and "go now" operations. Executor batches and utterances carry ids, so the machine drops the
  result of an aborted batch and a stale "finished" from a stopped utterance.
- Resting states and transient cues are different things: `wake_caught`, `analysing` and `cancelled`
  are shown on the LED and played as tones but the machine never rests in them.

## Consequences
- The router stops owning confirmation state; it hands intents to the machine.
- TTS must announce when speech ends, and the microphone must be muted while MIA speaks.
- One state table is the contract for the Android console, the LED firmware and the tests.
- A new input (for example the CD-changer button emulator) only needs an adapter that produces
  commands.

## Sources
`apps/rpi-backend/py-api/services/voice_command_router.py`, `tts_service.py`,
`docs/cs/automotive/zapojeni-audi-a4-8h.md`, `spec/interfaces/voice.md`.
