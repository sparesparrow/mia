# 0014. Voice data stays local, with a bounded retention

- Status: Proposed
- Date: 2026-10-12
- Requirements: REQ-VOICE-021, REQ-VOICE-018

## Context
Comparing the rule-based splitter with the language-model analysis (REQ-VOICE-020) needs the
transcripts. Comparing speech-to-text models needs short audio clips. Both are personal data,
and the car carries passengers who did not consent. Reading an incoming phone message aloud in
full also discloses the sender's text to everyone in the car.

## Decision
- Transcripts, analysis results and short audio clips are stored **only on the Pi**, in a path
  outside the repository, with a configured retention period after which they are deleted.
  Defaults: **30 days** for transcripts and analyses, **7 days** for audio clips. A shorter value is
  allowed; a longer one needs an explicit setting.
- The language-model analysis runs in the background and its output is stored; it does not
  decide what runs. Sending a transcript to a cloud model is **opt-in and off by default**, and the
  interaction log records which interactions were sent.
- In the chatty verbosity mode incoming phone messages are read aloud in full, even with a
  passenger present. The owner accepted this risk; the setting can be narrowed later without
  changing the rest.
- DPIA #137 is extended from ANPR to voice and covers transcripts, clips, passengers and
  message content.

## Consequences
- A retention setting and a deletion routine are part of the logging feature.
- Clips must never be added to the repository, test fixtures or CI artifacts.
- The Android console must not display or upload stored clips by default.

## Sources
GitHub issue #137, `spec/requirements/voice.yaml`.
