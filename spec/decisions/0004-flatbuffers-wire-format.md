# 0004. FlatBuffers wire format with committed bindings

- Status: Accepted
- Date: 2026-09-25 (recording an existing decision)
- Requirements: REQ-AUTO-008, REQ-ORCH-009

## Context
Messages cross Python, C++, Kotlin and ESP32 code. JSON is slow to parse on the MCU and
untyped; per-language hand-written structs drift.

## Decision
- FlatBuffers schemas in `schemas/` are the source of truth for binary messages; every table
  declares explicit field IDs and evolves additively.
- Generated bindings are committed under `schemas/generated/` and never edited by hand;
  `schemas/generate.py` regenerates them and CI flags drift.
- Baseline copies in `schemas/baseline/` guard compatibility.

## Consequences
- A schema change is cross-platform work: regenerate bindings and update the interface
  specs in `spec/interfaces/`.
- JSON remains acceptable at the edges (REST, the Cycle 1 envelope) where readability wins.

## Sources
`spec/architecture/flatbuffers-schema-guide.md`, `spec/architecture/lean-architecture.md`,
`schemas/README.md`, CI job `schema-validation`.
