"""Typed commands in, typed effects out (ADR-0011, spec/interfaces/voice.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Tuple, Union


class State(str, Enum):
    """Resting states: the machine stays in one of these until a command or the clock moves it."""

    IDLE = "idle"
    LISTENING = "listening"
    EXECUTING = "executing"
    WINDOW = "window"
    CONFIRMING = "confirming"
    SPEAKING = "speaking"
    DICTATING = "dictating"
    WARNING = "warning"


class CueName(str, Enum):
    """Transient cues: shown on the LED and played as a tone, never a state the machine rests in."""

    WAKE_CAUGHT = "wake_caught"
    ANALYSING = "analysing"
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
    """One action inside a chain.

    ``certain`` comes from the splitter. The class is checked against the machine's fixed table, so a
    wrong label can only make a part stricter, never looser (see classes.py).
    """

    name: str
    action_class: ActionClass
    args: Mapping[str, Any] = field(default_factory=dict, hash=False)
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
    """One utterance finished. ``id`` echoes ``Speak.id``; None means the oldest outstanding one."""

    id: Optional[int] = None


@dataclass(frozen=True)
class ExecutionDone:
    """An executor batch finished. ``batch_id`` echoes ``Execute.batch_id``; None means the oldest.

    ``phrase`` is what MIA should say about the result, if anything.
    """

    phrase: str = ""
    params: Mapping[str, Any] = field(default_factory=dict, hash=False)
    batch_id: Optional[int] = None


@dataclass(frozen=True)
class SafetyWarning:
    phrase: str
    params: Mapping[str, Any] = field(default_factory=dict, hash=False)


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
    SafetyWarning,
    IncomingMessage,
    SetVerbosity,
]


# ── Effects ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Execute:
    """Run these parts. The executor answers with ``ExecutionDone(batch_id=...)``."""

    parts: Tuple[Part, ...]
    batch_id: int = 0


@dataclass(frozen=True)
class Abort:
    """Stop the batch if it is still running; its ``ExecutionDone`` will be ignored."""

    batch_id: int


@dataclass(frozen=True)
class Speak:
    """Speech is a phrase key plus parameters; the persona turns it into words (ADR-0015).

    Utterances play first in, first out and each one ends with exactly one ``SpeakingDone(id)``,
    none after ``StopSpeaking``.
    """

    phrase: str
    params: Mapping[str, Any] = field(default_factory=dict, hash=False)
    priority: int = 0  # 1 = warning
    id: int = 0


@dataclass(frozen=True)
class StopSpeaking:
    pass


@dataclass(frozen=True)
class MuteMic:
    muted: bool


@dataclass(frozen=True)
class Feedback:
    """LED colour and tone for a state or a transient cue, named by its string value."""

    state: str
    led: str
    tone: str


@dataclass(frozen=True)
class StateChanged:
    previous: State
    current: State


Effect = Union[Execute, Abort, Speak, StopSpeaking, MuteMic, Feedback, StateChanged]
