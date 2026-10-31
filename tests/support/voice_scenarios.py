"""Scenario files for the voice harness: load and validate (REQ-VOICE-028).

A scenario is YAML in ``tests/fixtures/voice/scenarios``::

    name: wake_listening              # equals the file name
    description: ...
    layers: [ws, machine]             # optional; default both
    pending: "REQ-VOICE-025: ..."     # optional; the scenario is skipped with this reason
    stimulus: {kind: button, button: Wake}     # one stimulus, or a list run in order
    expect:                                     # ordered subsequence of the trace
      - state: listening
      - {spoken: {contains: "send it"}, timeout: 4}

Stimulus kinds: ``button`` (button), ``setting`` (verbosity | persona | language), ``setup`` (intent: a name from
``voice_rig.INTENTS``, machine layer only because a console may not send an Intent), ``await`` (steps: wait for
those steps before going on) and the not yet live ``typed`` (text), ``transcript`` (text), ``speech_zmq``,
``speech_alsa`` and ``speech_phone`` (phrase: a name from tools/voice/phrases.yaml).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from support.voice_stimuli import BUTTONS
from support.voice_trace import parse_step

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "voice" / "scenarios"
LAYERS = ("ws", "machine")
SETTINGS = ("verbosity", "persona", "language")
LIVE_KINDS = ("button", "setting", "setup", "await")
PENDING_KINDS = ("typed", "transcript", "speech_zmq", "speech_alsa", "speech_phone")
TOP_KEYS = {"name", "description", "layers", "pending", "stimulus", "expect", "timeout"}


class ScenarioError(ValueError):
    """A scenario file that does not follow the format."""


@dataclass(frozen=True)
class Scenario:
    name: str
    stimulus: List[Dict[str, Any]]
    expect: List[Dict[str, Any]]
    layers: tuple = LAYERS
    pending: Optional[str] = None
    timeout: float = 3.0
    description: str = ""
    path: Optional[Path] = field(default=None, compare=False)


def _fail(where: str, message: str) -> None:
    raise ScenarioError(f"{where}: {message}")


def _check_stimulus(where: str, item: Any, pending: bool) -> Dict[str, Any]:
    if not isinstance(item, dict) or not isinstance(item.get("kind"), str):
        _fail(where, f"a stimulus is a mapping with a kind, got {item!r}")
    kind = item["kind"]
    if kind not in LIVE_KINDS + PENDING_KINDS:
        _fail(where, f"unknown stimulus kind {kind!r}; one of {LIVE_KINDS + PENDING_KINDS}")
    if kind in PENDING_KINDS and not pending:
        _fail(where, f"stimulus kind {kind!r} is not live yet; mark the scenario pending with a reason")
    if kind == "button":
        if item.get("button") not in BUTTONS:
            _fail(where, f"button must be one of {BUTTONS}, got {item.get('button')!r}")
    elif kind == "setting":
        keys = [k for k in item if k != "kind"]
        if len(keys) != 1 or keys[0] not in SETTINGS or not isinstance(item[keys[0]], str):
            _fail(where, f"a setting stimulus sets exactly one of {SETTINGS} to a string")
    elif kind == "setup":
        if not isinstance(item.get("intent"), str):
            _fail(where, "setup needs an intent name")
    elif kind == "await":
        steps = item.get("steps")
        if not isinstance(steps, list) or not steps:
            _fail(where, "await needs a non-empty list of steps")
        _check_steps(where, steps)
    elif kind in ("typed", "transcript"):
        if not isinstance(item.get("text"), str) or not item["text"]:
            _fail(where, f"{kind} needs text")
    elif not isinstance(item.get("phrase"), str):
        _fail(where, f"{kind} needs a phrase name")
    return dict(item)


def _check_steps(where: str, steps: List[Any]) -> None:
    for i, step in enumerate(steps):
        try:
            parse_step(step)
        except ValueError as exc:
            _fail(f"{where}: step {i + 1}", str(exc))


def parse_scenario(data: Any, path: Optional[Path] = None) -> Scenario:
    where = str(path) if path else "scenario"
    if not isinstance(data, dict):
        _fail(where, "a scenario is a mapping")
    unknown = set(data) - TOP_KEYS
    if unknown:
        _fail(where, f"unknown keys {sorted(unknown)}")
    name = data.get("name")
    if not isinstance(name, str) or not name:
        _fail(where, "name is required")
    if path is not None and name != path.stem:
        _fail(where, f"name {name!r} must equal the file name {path.stem!r}")
    pending = data.get("pending")
    if pending is not None and (not isinstance(pending, str) or "REQ-" not in pending):
        _fail(where, "pending is a reason that names the requirement it waits for (REQ-...)")
    raw = data.get("stimulus")
    stimuli = raw if isinstance(raw, list) else [raw]
    if not stimuli or stimuli == [None]:
        _fail(where, "stimulus is required")
    stimulus = [_check_stimulus(f"{where}: stimulus {i + 1}", s, pending is not None) for i, s in enumerate(stimuli)]
    expect = data.get("expect")
    if not isinstance(expect, list) or not expect:
        _fail(where, "expect must be a non-empty list of steps")
    _check_steps(where, expect)
    layers = data.get("layers", list(LAYERS))
    if not isinstance(layers, list) or not layers or any(layer not in LAYERS for layer in layers):
        _fail(where, f"layers is a non-empty list of {LAYERS}")
    if "ws" in layers and any(s["kind"] == "setup" for s in stimulus):
        _fail(where, "setup cannot run through /ws/voice: a console may not send an Intent (ADR-0013)")
    timeout = data.get("timeout", 3.0)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        _fail(where, "timeout is a positive number")
    return Scenario(
        name=name,
        stimulus=stimulus,
        expect=expect,
        layers=tuple(layers),
        pending=pending,
        timeout=float(timeout),
        description=str(data.get("description", "")),
        path=path,
    )


def load_scenario(path: Path) -> Scenario:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(f"{path}: not valid YAML: {exc}") from exc
    return parse_scenario(data, Path(path))


def load_all(directory: Path = SCENARIO_DIR) -> List[Scenario]:
    return [load_scenario(p) for p in sorted(Path(directory).glob("*.yaml"))]
