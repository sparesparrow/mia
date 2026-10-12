"""Typed commands in, typed effects out (ADR-0011, spec/interfaces/voice.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Tuple, Union


class State(str, Enum):
    IDLE = "idle"
    WAKE_CAUGHT = "wake_caught"
    LISTENING = "listening"
    ANALYSING = "analysing"
    EXECUTING = "executing"
    WINDOW = "window"
    CONFIRMING = "confirming"
    SPEAKING = "speaking"
    DICTATING = "dictating"
    WARNING = "warning"
    CANCELLED = "cancelled"


class Source(str, Enum):
    VOICE = "voice"
    BUTTON = "button"
    CONSOLE = "console"
    CAR = "car"
    RULE = "rule"


class ActionClass(str, Enum):
    """What silence means for a part of a chain (ADR-0012)."""

    READ = "read"
    COMFORT = "comfort"
    NOTE = "note"
    MESSAGE = "message"  # SMS, e-mail, phone call: never runs on silence
    FORBIDDEN = "forbidden"  # writes to a control unit: refused (ADR-0006)


class Verbosity(str, Enum):
    QUIET = "quiet"
    NORMAL = "normal"
    CHATTY = "chatty"


DICTATE = "note.dictate"
SAVE_NOTE = "note.save"


@dataclass(frozen=True)
class Part:
    """One action inside a chain. ``certain`` is decided by the splitter, not by the machine."""

    name: str
    action_class: ActionClass
    args: Mapping[str, Any] = field(default_factory=dict)
    certain: bool = True


# ── Commands ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Wake:
    source: Source = Source.VOICE


@dataclass(frozen=True)
class Intent:
    parts: Tuple[Part, ...]
    source: Source = Source.VOICE


@dataclass(frozen=True)
class GoNow:
    source: Source = Source.BUTTON


@dataclass(frozen=True)
class Cancel:
    source: Source = Source.BUTTON


@dataclass(frozen=True)
class Confirm:
    source: Source = Source.VOICE


@dataclass(frozen=True)
class Deny:
    source: Source = Source.VOICE


@dataclass(frozen=True)
class EndDictation:
    source: Source = Source.BUTTON


@dataclass(frozen=True)
class DictationText:
    text: str


@dataclass(frozen=True)
class SpeakingDone:
    pass


@dataclass(frozen=True)
class ExecutionDone:
    """The executor finished a batch; ``phrase`` is what MIA should say about it, if anything."""

    phrase: str = ""
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Warning:  # noqa: A001 - mirrors the domain word
    phrase: str
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IncomingMessage:
    sender: str
    text: str


@dataclass(frozen=True)
class SetVerbosity:
    level: Verbosity
    source: Source = Source.VOICE


Command = Union[
    Wake,
    Intent,
    GoNow,
    Cancel,
    Confirm,
    Deny,
    EndDictation,
    DictationText,
    SpeakingDone,
    ExecutionDone,
    Warning,
    IncomingMessage,
    SetVerbosity,
]


# ── Effects ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Execute:
    parts: Tuple[Part, ...]


@dataclass(frozen=True)
class Speak:
    """Speech is a phrase key plus parameters; the persona turns it into words (ADR-0015)."""

    phrase: str
    params: Mapping[str, Any] = field(default_factory=dict)
    priority: int = 0  # 1 = warning


@dataclass(frozen=True)
class StopSpeaking:
    pass


@dataclass(frozen=True)
class MuteMic:
    muted: bool


@dataclass(frozen=True)
class Feedback:
    state: State
    led: str
    tone: str


@dataclass(frozen=True)
class StateChanged:
    previous: State
    current: State


Effect = Union[Execute, Speak, StopSpeaking, MuteMic, Feedback, StateChanged]
