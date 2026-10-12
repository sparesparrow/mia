# Voice interface

Contract for the voice state machine (ADR-0011), its commands and effects, the feedback cues and the
message envelope (ADR-0013). Names here are the names in `apps/rpi-backend/py-api/services/voice_fsm/`.
Each item is marked **implemented** (code and tests exist) or **planned** (design only).

## Commands (input)

Every input is reduced to one typed command before it reaches the machine. A command does not depend on
its `source`: a go-now from a button, from speech or from the console has the same effect. No button or
console adapter exists yet, so the end-to-end claim belongs to REQ-VOICE-015, not to the machine.

| Command | Meaning | Status |
|---|---|---|
| `Wake(source)` | wake word or button accepted | implemented |
| `Intent(parts, source)` | a split utterance: parts with a name, class, arguments and certainty | implemented |
| `GoNow(source)` | run the pending part now; in `confirming` an explicit yes; in `dictating` end it | implemented |
| `Cancel(source)` | drop the chain; silences MIA; during a warning drops the paused chain only | implemented |
| `Confirm`, `Deny` | an explicit yes or no to a message or call question; `Deny` in `window` is a cancel | implemented |
| `EndDictation`, `DictationText(text)` | finish a note; text recognised while dictating | implemented |
| `SafetyWarning(phrase, params)` | a safety warning from the car | implemented |
| `IncomingMessage(sender, text)` | a phone message | implemented (no source of messages exists on the Pi) |
| `SetVerbosity(level, source)` | quiet, normal or chatty | implemented |
| `SpeakingDone(id)` | TTS finished utterance `id` | implemented |
| `ExecutionDone(phrase, params, batch_id)` | an executor batch finished | implemented |
| `SwitchPersona`, `Event(kind, data)` for ignition, parking and rules | | planned |

## Effects (output)

| Effect | Meaning | Status |
|---|---|---|
| `Execute(parts, batch_id)` | run these parts; answer with `ExecutionDone(batch_id=...)` | implemented |
| `Abort(batch_id)` | stop the batch if it still runs; its `ExecutionDone` is ignored | implemented |
| `Speak(phrase, params, priority, id)` | say a phrase key; a persona turns it into words | implemented |
| `StopSpeaking` | stop the current utterances | implemented (`tts_service` cannot yet stop mid-sentence) |
| `MuteMic(muted)` | emitted when the microphone state changes | implemented |
| `Feedback(state, led, tone)` | LED colour and tone for a state or a transient cue | implemented |
| `StateChanged(previous, current)` | a resting state changed | implemented |
| `Spoken` (a `Speak` for peers), `Transcript` | on the wire as events for the console | implemented |
| `QueueEntry`, `WindowTick` for the console | | planned |

### Speech contract

`Speak` effects play first in, first out. Each one ends with exactly one `SpeakingDone(id)` carrying its
`id`, and none after `StopSpeaking`. The machine ignores a `SpeakingDone` whose id is not outstanding, so
a "finished" callback from an utterance that was stopped changes nothing. A `SpeakingDone` without an id
means the oldest outstanding utterance. TTS echoes the id that the router sends in `utterance_id`.

### Executor contract

Each `Execute` carries a `batch_id`. The machine stays busy until every outstanding batch has reported
done, drops a result for an aborted or unknown batch, and emits `Abort` for each outstanding batch when
the chain is cancelled.

## States and cues

The table is the code's `FEEDBACK` in `voice_fsm/feedback.py`; a test checks that the two agree. Colours
and tones are defaults to be tuned in the car. A colour must also differ by brightness or pattern, not
only hue, and the two states where silence means opposite things (`window` runs, `confirming` drops) must
look and sound different.

| State or cue | Meaning | LED | Tone |
|---|---|---|---|
| `idle` | nothing in progress | `off` | `none` |
| `listening` | the microphone is capturing a command | `blue` | `none` |
| `executing` | actions are running | `green` | `confirm_beep` |
| `window` | uncertain part announced; silence runs it after 5 s | `yellow_countdown` | `double_beep` |
| `confirming` | a message or call waits for an explicit yes; silence drops it | `yellow_solid` | `question_tone` |
| `speaking` | MIA is talking, microphone muted | `purple` | `none` |
| `dictating` | a note is being recorded | `red` | `start_end_beep` |
| `warning` | a safety warning is being announced | `orange_flash` | `warning_tone` |
| `wake_caught` | cue only: wake word or button accepted | `white_brief` | `rising_beep` |
| `analysing` | cue only: the transcript is being split | `blue_pulse` | `none` |
| `cancelled` | cue only: the chain was cancelled | `off` | `falling_beep` |

Cues are shown and played but are never a state the machine rests in and emit no `StateChanged`. A
`Feedback` with the tone `busy_beep` means an utterance arrived while the machine could not take it.

## Rules for the buttons

| State | go now | cancel |
|---|---|---|
| `window` | run the pending part now | drop it |
| `speaking` during an announcement | stop speaking and run the part now | stop speaking and drop the chain |
| `speaking` during a question | skip the question; a message still needs a second, explicit press | stop speaking and drop the chain |
| `confirming` | explicit yes | drop the message or call |
| `dictating` | end and save the note | discard it |
| `warning` | nothing (the warning keeps playing) | drop the chain the warning paused |

## Spoken answers

In `window` and `confirming` the router bridge treats only a short reply (at most three words) as a yes or a
no. A longer sentence that contains one, such as "okay so send it to Jana instead", is a correction and is
routed as a new utterance. A no wins over a yes in the same short reply.

## Priority and queues

A `SafetyWarning` interrupts dictation, listening, the window and speech. What it cut off is said again
before the machine goes on, so a part never runs and a message is never confirmed on a question the driver
did not hear in full. An incoming phone message waits in a queue until the machine is idle, and the queue
keeps the newest 20 (the oldest is dropped). Quiet mode drops both new and waiting messages. After a
cancel, queued messages wait for the next time the machine becomes idle. An utterance that arrives while
MIA is executing, or while a part is announced, waits its turn or corrects it; during dictation or a
warning it gets the busy cue.

## Action classes

See ADR-0012. The class of an action comes from a fixed table in `voice_fsm/classes.py`: a label can only
make a part stricter, and an unknown action is forbidden. Read, comfort and note parts that are uncertain
run after the shared window. Message and call parts need an explicit yes. Forbidden parts are refused.

## ZeroMQ topics on the Pi

| Topic | Port | Publisher | Content |
|---|---|---|---|
| `mia/voice/wake` | 5559 | `wake_word` | wake word detected |
| `mia/voice/transcript` | 5560 | `stt_service` | recognised text and language |
| `mia/voice/response` | 5561 | `voice_command_router` | text for TTS, with an `utterance_id` in FSM mode |
| `mia/voice/feedback` | 5561 | `voice_command_router` (FSM mode) | `{state, led, tone}` for the LED node |
| `mia/voice/speaking` | 5563 | `tts_service` | `{event: started or finished, ok, timestamp, utterance_id}` |

Audio capture mutes the microphone while an utterance plays and for a short tail after the last one. The gate
never stays closed more than 30 s after the last speaking event, so a lost `finished` cannot leave it muted. The
router runs the machine only when `VOICE_FSM=1` (off by default). (REQ-VOICE-016)

## Envelope and channel

Defined by ADR-0013 in `schemas/voice.fbs` (namespace `MiaVoice`, file identifier `MIAV`); bindings are committed
in `schemas/generated/` and compared with a fresh `flatc` run in CI. (REQ-NET-008, REQ-NET-009)

An **envelope** routes a message and never looks inside it:

| Field | Meaning |
|---|---|
| `version` | wire version, now 1; any other value is answered `UnsupportedVersion` |
| `service` | which service owns the payload: `Voice`; a missing or unknown value is answered `UnknownService` |
| `session_id` | chosen by the peer on `Open`; `Data` and `Close` must name a session that peer opened |
| `op` | `Data`, `Open` or `Close` |
| `status` | `Ok` on requests; on a reply `Ok`, `UnknownService`, `UnsupportedVersion`, `Malformed`, `NotPermitted` or `UnknownSession` |
| `seq` | chosen by the sender and echoed in the reply; events carry the router's own counter |
| `payload` | a nested `VoiceMessage` (one `VoiceBody` union member) |

A request is answered with one reply to the sender. Events (the machine's effects) go to every open session
of the service and to no other. A garbled buffer, a wrong version or an unknown service is answered with a
status; nothing raises. Messages are at most 64 KiB.

### Voice messages

| Message | Direction | Dataclass |
|---|---|---|
| `Wake`, `GoNow`, `Cancel`, `Confirm`, `Deny`, `EndDictation`, `SetVerbosity` | peer to machine, allowed from a console | the command of the same name |
| `Intent`, `DictationText` | peer to machine, in-process only | the command of the same name |
| `SpeakingDone`, `ExecutionDone`, `SafetyWarning`, `IncomingMessage` | peer to machine, in-process only | the command of the same name |
| `StateChanged`, `FeedbackCue`, `Spoken` | machine to peers | `StateChanged`, `Feedback`, `Speak` |
| `Transcript` | machine side to peers | `wire.Transcript` (not consumed by the machine) |

`Execute`, `Abort`, `StopSpeaking` and `MuteMic` talk to the machine's own executors and microphone and are not on
the wire. `WindowTick` and a queue-entry event are planned; the machine does not emit them yet.

A console can send only the commands in `PEER_COMMANDS`: the two button roles, the answer buttons, wake, end of
dictation and the verbosity setting. The rest is refused with `NotPermitted`, so a socket cannot report a safety
warning, a finished utterance or a result. **The channel, not the peer, sets `source`**: a console message is
stamped `console` whatever it claims.

Enum names in the schema are the CamelCase form of the strings in the code (`State.WINDOW = "window"` is `Window`).
`FeedbackCue` carries the resting `state`, or a transient `cue` when it is not `NoCue`, with the LED colour and the
tone as enums. `tools/schemas/extract_enums.py` writes `schemas/generated/cpp/voice_enums.h`, which holds only these
enums, for firmware that cannot use FlatBuffers. Both sides are checked by tests.

### Channels

A channel reads and writes whole messages; a listener hands out one channel per connection. Stream transports
carry a 4-byte big-endian length before each message; datagram transports do not.

| Channel | Status |
|---|---|
| in-memory pair (`LoopbackChannel`) | implemented |
| length-framed stream over TCP or a unix socket (`FramedChannel`, `SocketListener`) | implemented; a serial line is the same class over a stream with `recv` and `sendall` |
| UDP to one peer (`UdpChannel`), datagrams from other addresses dropped | implemented; may lose or reorder messages |
| WebSocket `/ws/voice` | implemented, off unless `VOICE_CONSOLE=1`, API key required; talks to a machine simulated in the API process |
| ZeroMQ, BLE, a real serial line | planned |

The stream and UDP channels do not authenticate their peers: bind their listeners to loopback or a trusted link.
`/ws/voice` requires the `X-API-Key` header when API keys are configured (a read-scope key is enough) and drops a
console whose queue of 256 unsent frames fills up.

## Interaction log record (planned)

Fields stored per interaction (REQ-VOICE-021, ADR-0014): time, chain id, transcript, speech recognition
figures, context (ignition, moving, roof), rule-based result, model result, what ran, the user's reaction
in the window, a link to the short audio clip and later a manual "correct split" label. Stored only on
the Pi.
