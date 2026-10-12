# 0015. Personas are data, not code

- Status: Proposed
- Date: 2026-10-12
- Requirements: REQ-VOICE-019, REQ-AND-017

## Context
The owner wants two switchable personalities, Holly (dry, terse) and Rimmer (anxious,
long-winded), inspired by the sitcom Red Dwarf. The existing `agents/SOUL.md` defines the
tone of three web chat agents and says never to invent facts and never to let the insanity
prevent real help.

## Decision
- A persona is a data package: reply templates per state and event, a TTS voice and speed,
  and a warning style. Selecting a persona changes none of the logic.
- Templates are chosen offline. A language model may add colour only in the chatty mode and
  only when online.
- **Warnings keep their content in every persona, and the content comes first.** Every warning
  starts with a shared safety fragment (value, unit, recommendation) that no persona can change or
  delay. A persona may add one short framing sentence after it, not before, and may skip it while the
  car is moving. A test checks that every persona's warning template starts with the shared fragment.
- Lines are written for MIA. Quotes, scripts and dubbing from the show are not copied, and no
  voice clone of an actor is made. Audio comes from stock voices of the chosen provider.
- Switching works by button, by the voice command "change persona" and in the Android app. The
  choice is remembered.

## Consequences
- Adding a persona needs a data package, not a code change.
- The safety-critical wording lives in one place that every persona must use.

## Sources
`agents/SOUL.md`, `spec/requirements/voice.yaml`.
