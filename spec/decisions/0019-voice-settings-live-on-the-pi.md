# 0019. Voice settings live on the Pi, are read back by peers and persist

- Status: Proposed
- Date: 2026-10-26
- Requirements: REQ-VOICE-017, REQ-NET-008, REQ-AND-016

## Context
The voice machine (ADR-0011) has a verbosity setting: quiet, normal or chatty. A console could send
`SetVerbosity`, but nothing came back except the reply to the request. The Android console therefore showed
"the last one it sent", which was wrong in three cases:

- after another console changed it;
- after a restart reset it to normal;
- when the console opened while the machine was already quiet.

Nothing stored the setting, so every restart of the voice router lost the driver's choice. REQ-VOICE-017 asks
for the modes to be switchable by voice and button and remembered across drives.

ADR-0015 adds a persona, and the language follows. Both are settings of the same kind, so they need one place to
live.

## Decision
- **The machine owns its settings.** Peers show what the machine reports, never what they last asked for.
- **A `Settings` event carries them.** It is appended to `VoiceBody` in `schemas/voice.fbs`. The machine emits it
  on every change, in any state, and every open session receives it. A session that has just opened receives
  one `Settings` event on its own, right after the `Ok` to its `Open`, so it starts from the real values. The
  envelope router stays service-agnostic: a service may offer an `on_open` snapshot, and the router delivers it.
- **The Pi persists them.** `services/voice_fsm/settings_store.py` writes `$MIA_STATE_DIR/voice_settings.json`
  (`/var/lib/mia` by default) on every change, replacing the file in one step. A missing or damaged file, or a
  value this version does not know, gives the defaults. A failed write is logged and never stops the voice loop.
- **Spoken commands.** "Quiet mode", "normal mode" and "chatty mode", alone or after "switch to", "go to",
  "set to" or "be", set the verbosity. A longer sentence that only mentions a mode is a request like any other.
- **Extension.** The persona and the language (ADR-0015) become fields of the same table and the same file,
  under the same rules.

## Consequences
- Every console of a machine shows the settings that machine uses, whichever console changed them.
- The voice router and the console's simulated machine run in different processes. Each reads the file when it
  starts and writes it on every change, but they do not tell each other while running. Joining them is the
  open step from ADR-0013; until then a change made in one reaches the other only at its next start.
- The settings file is not personal data, but it lives outside the repository on the Pi.
  `mia-api.service` declares `StateDirectory=mia`, so systemd creates `/var/lib/mia` for its user `mia`. The
  voice router runs as root and can write there anyway.
- No steering-wheel button adapter exists yet; the console's controls stand in for the button.

## Sources
`schemas/voice.fbs`, `apps/rpi-backend/py-api/services/voice_fsm/` (`settings_store.py`, `machine.py`,
`bridge.py`, `wire/router.py`), `apps/rpi-backend/py-api/api/voice_console.py`,
`apps/android/app/src/main/java/cz/mia/app/core/voice/console/`, `spec/interfaces/voice.md`.
