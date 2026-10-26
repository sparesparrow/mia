#!/usr/bin/env python3
"""Write tests/fixtures/voice/envelopes.json: voice envelopes as the Pi encodes them.

    python tools/schemas/gen_voice_fixtures.py           # (re)write the fixture
    python tools/schemas/gen_voice_fixtures.py --check   # exit 1 if the committed file is stale

The Python tests check the file against the codec; the Android unit tests decode the same bytes and
re-encode the console commands to the same bytes, so the two implementations cannot drift apart
unnoticed (REQ-NET-008, REQ-AND-016).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "tests" / "fixtures" / "voice" / "envelopes.json"
SESSION = "console-test"

sys.path.insert(0, str(REPO_ROOT / "apps" / "rpi-backend" / "py-api"))

from services.voice_fsm import (  # noqa: E402
    Cancel,
    Confirm,
    Deny,
    EndDictation,
    Feedback,
    GoNow,
    Settings,
    SetVerbosity,
    Source,
    Speak,
    State,
    StateChanged,
    Verbosity,
    Wake,
)
from services.voice_fsm.wire import (  # noqa: E402
    Envelope,
    Op,
    Service,
    Status,
    Transcript,
    encode_command,
    encode_envelope,
    encode_event,
)


def _hex(envelope: Envelope) -> str:
    return encode_envelope(envelope).hex()


def build() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    seq = 0

    def add(entry: Dict[str, Any]) -> None:
        cases.append(entry)

    seq += 1
    add(
        {
            "name": "open",
            "type": "open",
            "session": SESSION,
            "seq": seq,
            "hex": _hex(Envelope(Service.VOICE, SESSION, Op.OPEN, Status.OK, seq)),
        }
    )
    commands = [
        ("wake", Wake(Source.CONSOLE)),
        ("go_now", GoNow(Source.CONSOLE)),
        ("cancel", Cancel(Source.CONSOLE)),
        ("confirm", Confirm(Source.CONSOLE)),
        ("deny", Deny(Source.CONSOLE)),
        ("end_dictation", EndDictation(Source.CONSOLE)),
        ("verbosity_quiet", SetVerbosity(Verbosity.QUIET, Source.CONSOLE)),
        ("verbosity_normal", SetVerbosity(Verbosity.NORMAL, Source.CONSOLE)),
        ("verbosity_chatty", SetVerbosity(Verbosity.CHATTY, Source.CONSOLE)),
    ]
    for name, command in commands:
        seq += 1
        add(
            {
                "name": f"command_{name}",
                "type": "command",
                "command": name,
                "session": SESSION,
                "seq": seq,
                "hex": _hex(
                    Envelope(
                        Service.VOICE,
                        SESSION,
                        Op.DATA,
                        Status.OK,
                        seq,
                        encode_command(command),
                    )
                ),
            }
        )

    events = [
        (
            "state_changed",
            StateChanged(State.IDLE, State.WINDOW),
            {"kind": "state_changed", "previous": "idle", "current": "window"},
        ),
        (
            "feedback_window",
            Feedback("window", "yellow_countdown", "double_beep"),
            {
                "kind": "feedback",
                "state": "window",
                "led": "yellow_countdown",
                "tone": "double_beep",
            },
        ),
        (
            "feedback_cue",
            Feedback("cancelled", "off", "falling_beep"),
            {
                "kind": "feedback",
                "state": "cancelled",
                "led": "off",
                "tone": "falling_beep",
            },
        ),
        (
            "feedback_idle",
            Feedback("idle", "off", "none"),
            {"kind": "feedback", "state": "idle", "led": "off", "tone": "none"},
        ),
        (
            "spoken_announce",
            Speak(
                "chain.announce",
                {"parts": ["lights.on", "read.voltage"], "seconds": 5.0},
                0,
                2,
            ),
            {
                "kind": "spoken",
                "phrase": "chain.announce",
                "params": {"parts": "lights.on, read.voltage", "seconds": "5.0"},
                "priority": 0,
                "utterance_id": 2,
            },
        ),
        (
            "spoken_warning",
            Speak("warn.coolant", {"value": 112, "unit": "C", "moving": True}, 1, 7),
            {
                "kind": "spoken",
                "phrase": "warn.coolant",
                "params": {"value": "112", "unit": "C", "moving": "true"},
                "priority": 1,
                "utterance_id": 7,
            },
        ),
        (
            "transcript",
            Transcript("zapni světla a řekni napětí", 3),
            {
                "kind": "transcript",
                "text": "zapni světla a řekni napětí",
                "utterance_id": 3,
            },
        ),
        (
            "settings_quiet",
            Settings(Verbosity.QUIET),
            {"kind": "settings", "verbosity": "quiet"},
        ),
        (
            "settings_chatty",
            Settings(Verbosity.CHATTY),
            {"kind": "settings", "verbosity": "chatty"},
        ),
    ]
    for name, event, expect in events:
        seq += 1
        payload = encode_event(event)
        assert payload is not None
        add(
            {
                "name": f"event_{name}",
                "type": "event",
                "event": expect,
                "session": SESSION,
                "seq": seq,
                "hex": _hex(
                    Envelope(Service.VOICE, SESSION, Op.DATA, Status.OK, seq, payload)
                ),
            }
        )

    for status in (Status.OK, Status.NOT_PERMITTED, Status.UNKNOWN_SESSION):
        seq += 1
        add(
            {
                "name": f"reply_{status.name.lower()}",
                "type": "reply",
                "status": status.name.lower(),
                "session": SESSION,
                "seq": seq,
                "hex": _hex(Envelope(Service.VOICE, SESSION, Op.DATA, status, seq)),
            }
        )
    return cases


def render() -> str:
    return (
        json.dumps({"version": 1, "cases": build()}, indent=2, ensure_ascii=False)
        + "\n"
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; fail if the fixture is stale",
    )
    args = parser.parse_args(argv)
    expected = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != expected:
            print(
                f"{OUT.relative_to(REPO_ROOT)} is out of date; run tools/schemas/gen_voice_fixtures.py"
            )
            return 1
        print("voice fixtures are up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(expected, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
