# 0013. Message envelope and an abstract channel for voice and console traffic

- Status: Proposed
- Date: 2026-10-12
- Requirements: REQ-NET-008, REQ-NET-009

## Context
The voice state machine (ADR-0011) must talk to the Android console, an ESP32 feedback node and
tests. Those peers are reached by different transports: ZeroMQ on the Pi, WebSocket or BLE to
the phone, a serial line to a microcontroller, a unix socket in tests. Today each pair has its
own format, mostly JSON.

## Decision
- One FlatBuffers **envelope** carries every voice message: a routing type, a version, a
  session id, a flag for create, close or data, and a nested payload that belongs to the
  service named by the type. The envelope does not interpret the payload. ADR-0004 rules
  apply: explicit field ids, additive evolution, committed bindings.
- A service defines its own schema with a request or response union and its own status values.
  Unsolicited events (state change, transcript, spoken text, queue entry, feedback cue) are a
  third kind of message next to request and response.
- Transports sit behind a small **channel** interface (read, write, is-open) and a **listener**
  that creates a channel per incoming connection. Stream transports add a framing layer that
  prefixes the message length; datagram transports do not need one.
- A broker routes by type to a registered service queue. An unknown type is an error reply, not
  a crash. Unsolicited events can be filtered per session.
- The design follows common patterns of a routing envelope with a nested service payload and a
  small channel interface. No third-party source code or identifiers are copied.

### Relation to existing decisions
- **ADR-0003 (ZeroMQ broker on 5555).** That broker routes JSON requests between clients and workers.
  The voice envelope does not replace it. On the Pi the voice services keep their ZeroMQ topics (see
  `spec/interfaces/voice.md`) and the envelope is what a ZeroMQ, WebSocket, BLE or serial *channel*
  carries to the Android console and the ESP32. Whether the 5555 broker later routes the envelope by
  its type is open; it is not needed for phase 1 and would be a new ADR.
- **ADR-0009 (vehicle telemetry envelope).** That envelope is JSON, defined for vehicle signals with
  units, source and confidence. It stays as it is. The voice envelope is binary (ADR-0004) because it
  also goes to a microcontroller, and it carries voice and console traffic, not vehicle signals. The two
  do not share fields, so extending ADR-0009 would mix unrelated concerns.

## Consequences
- Adding a service means a new schema and a registration, not a new transport.
- Tests use an in-memory channel; hardware uses the real one, with identical messages.
- The envelope is a new layer above `schemas/mia.fbs`; existing messages are unchanged.

### What the first implementation settled
- The envelope carries a protocol `version` (1) that is rejected when it differs, a `status` for replies and a
  sender-chosen `seq` that the reply echoes.
- A console may send only button-equivalent commands and the verbosity setting. Results, finished-speech
  reports, warnings, phone messages and typed intents enter the machine from inside the Pi. The channel sets
  the command `source`; the peer cannot claim `car` or `voice`.
- The WebSocket endpoint is off by default (`VOICE_CONSOLE=1`) and, like every other WebSocket of the API,
  needs the API key when keys are configured (REQ-SEC-001). A read-scope key is enough, so a stricter scope
  for commands is open. The stream and UDP channels do not authenticate.
- Phrase parameters are text, integer, real, flag, or a list of text; other types are refused rather than guessed.

## Sources

`spec/decisions/0003-zeromq-control-plane-and-telemetry.md`,
`spec/decisions/0004-flatbuffers-wire-format.md`,
`spec/decisions/0009-canonical-vehicle-telemetry-envelope.md`, `schemas/mia.fbs`,
`spec/interfaces/voice.md`.
