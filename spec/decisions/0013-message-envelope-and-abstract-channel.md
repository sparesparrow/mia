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
- The design follows common patterns. No third-party source code or identifiers are copied.

## Consequences
- Adding a service means a new schema and a registration, not a new transport.
- Tests use an in-memory channel; hardware uses the real one, with identical messages.
- The envelope is a new layer above `schemas/mia.fbs`; existing messages are unchanged.

## Sources
`spec/decisions/0004-flatbuffers-wire-format.md`, `schemas/mia.fbs`, `spec/interfaces/voice.md`.
