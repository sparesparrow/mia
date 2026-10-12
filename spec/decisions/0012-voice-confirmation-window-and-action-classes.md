# 0012. Uncertain voice commands run after a 5 s window, by action class

- Status: Proposed
- Date: 2026-10-12
- Requirements: REQ-VOICE-010, REQ-VOICE-012, REQ-VOICE-013, REQ-VOICE-014

## Context
Today the router asks yes or no when a match is ambiguous and cancels on silence after 8 s
(default-deny). While driving the user cannot always answer, and with the roof open a spoken
"stop" may not be recognised. The first user chose the opposite for harmless commands: announce
what MIA will do and do it after 5 s unless cancelled or corrected.

## Decision
Commands fall into classes; the class decides what silence means.

| Class | Examples | Uncertain part |
|---|---|---|
| Read | vehicle readings (voltage, coolant, RPM, ignition) | announced, runs after 5 s |
| Comfort | lights, volume, music | announced, runs after 5 s |
| Note | store a dictated note | announced, runs after 5 s |
| Message / call | SMS, e-mail, phone call | never runs on silence; needs an explicit "yes" |
| Forbidden | writing to a control unit (clearing DTCs), regenerating the DPF | refused, never queued (ADR-0006) |

- Certain parts of a chain run immediately; uncertain parts share **one** window that starts
  when MIA finishes announcing.
- Two buttons: **go now** shortens the window, **cancel** aborts the chain. Cancel must not
  depend on speech recognition.
- The window needs a "speech finished" signal from TTS and a clock that can be faked in tests.

## Consequences
- REQ-VOICE-010 is reworded: ambiguity no longer always means cancel-on-silence; it depends on
  the class.
- Wrongly executing a Comfort command is possible. The classes are deliberately limited to
  reversible, non-safety actions; new classes need a new ADR.
- Messages and calls stay safe against a mis-recognised transcript.

## Sources
`voice_command_router.py` (`CONFIRMATION_TIMEOUT_SEC`, `pending_confirmation`),
`spec/decisions/0006-passive-vehicle-access-by-default.md`.
