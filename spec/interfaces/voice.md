# Voice interface

Contract for the voice state machine (ADR-0011), its inputs and effects, the message envelope
(ADR-0013) and the feedback cues. Status: **design**. Nothing here is implemented yet; each
item is tracked by the requirement named beside it.

## Inputs, all reduced to one command

| Source | Examples | Becomes |
|---|---|---|
| Speech | "zapni světla", "jaké je napětí" | `Intent(name, args, source=voice)` |
| Button | go now, cancel, end dictation, switch persona (long press) | `GoNow`, `Cancel`, `EndDictation`, `SwitchPersona` with `source=button` |
| Car event | ignition on, parked, warning limit crossed | `Event(kind, data)` |
| Rule | a standing rule's condition becomes true | `Event(kind=rule, data)` |
| Console | simulated button, persona or verbosity change from the Android app | same commands with `source=console` |

A command from a button and the same command from speech are indistinguishable to the machine.
(REQ-VOICE-015)

## States

| State | Meaning | LED (default) | Tone |
|---|---|---|---|
| `idle` | nothing in progress | off | none |
| `wake_caught` | wake word or button accepted | white, brief | short rising beep |
| `listening` | microphone is capturing a command | blue | none |
| `analysing` | transcript is being split and classified | blue, pulsing | none |
| `executing` | actions are running | green | short confirm beep |
| `window` | uncertain part announced; 5 s countdown | yellow | two beeps at the start |
| `speaking` | MIA is talking, microphone muted | purple | none |
| `dictating` | a note is being recorded | red | beep at start and end |
| `warning` | safety warning being announced | orange or red, flashing | distinct warning tone |
| `cancelled` | the chain was cancelled | off | falling beep |

The table above is the only place that maps state to colour and tone. Colours and tones are
defaults to be tuned in the car; a colour must also differ by brightness or pattern, not only
hue. (REQ-VOICE-011, REQ-HW-009)

## Priority

`warning` interrupts `dictating` and `window`. An incoming phone message waits in a queue until
the machine is free. (REQ-VOICE-018)

## Action classes

See ADR-0012: read, comfort, note (run after the shared window), message or call (explicit
confirmation), forbidden (refused). (REQ-VOICE-012, 013, 014)

## Verbosity and persona

`quiet`, `normal` and `chatty` decide what MIA announces on its own. A persona decides the
wording and voice of replies and the framing of warnings, not their content. (REQ-VOICE-017,
019)

## Envelope and channel

Defined by ADR-0013. A message has a routing type, a version, a session, a create, close or data
flag and a nested payload for the named service. Request, response and unsolicited event are the
three message kinds. A channel offers read, write and is-open; stream transports add a length
prefix. (REQ-NET-008, REQ-NET-009)

## Events the console and the LED node receive

| Event | Carries |
|---|---|
| `StateChanged` | new state, previous state, chain id |
| `Transcript` | recognised text, language, quality figures |
| `Spoken` | text MIA says and the persona |
| `QueueEntry` | queued item, priority |
| `FeedbackCue` | state, LED colour, tone id |
| `WindowTick` | seconds left in the confirmation window |

## Interaction log record

Fields stored per interaction (REQ-VOICE-021, ADR-0014): time, chain id, transcript, speech
recognition figures, context (ignition, moving, roof), rule-based result, model result, what
ran, the user's reaction in the window, a link to the short audio clip and later a manual
"correct split" label. Stored only on the Pi.
