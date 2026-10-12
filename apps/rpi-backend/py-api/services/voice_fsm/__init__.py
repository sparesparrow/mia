"""Voice state machine: the single source of commands and feedback (ADR-0011).

Pure logic with an injected clock. It reads typed commands and returns effects; it does no
audio, network or file I/O, so it runs identically in tests, on the Pi and in simulation.
"""

from .feedback import FEEDBACK, Cue
from .machine import VoiceMachine
from .types import (
    ActionClass,
    Cancel,
    Command,
    Confirm,
    Deny,
    DictationText,
    Effect,
    EndDictation,
    Execute,
    ExecutionDone,
    Feedback,
    GoNow,
    IncomingMessage,
    Intent,
    MuteMic,
    Part,
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    StateChanged,
    StopSpeaking,
    Verbosity,
    Wake,
    Warning,
)

__all__ = [
    "ActionClass",
    "Cancel",
    "Command",
    "Confirm",
    "Cue",
    "Deny",
    "DictationText",
    "Effect",
    "EndDictation",
    "Execute",
    "ExecutionDone",
    "FEEDBACK",
    "Feedback",
    "GoNow",
    "IncomingMessage",
    "Intent",
    "MuteMic",
    "Part",
    "SetVerbosity",
    "Source",
    "Speak",
    "SpeakingDone",
    "State",
    "StateChanged",
    "StopSpeaking",
    "Verbosity",
    "VoiceMachine",
    "Wake",
    "Warning",
]
