"""The one table from state to LED colour and tone (spec/interfaces/voice.md).

Colours and tones are defaults to be tuned in the car. A colour must also differ by
brightness or pattern, not only hue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .types import State


@dataclass(frozen=True)
class Cue:
    led: str
    tone: str


FEEDBACK: Dict[State, Cue] = {
    State.IDLE: Cue("off", "none"),
    State.WAKE_CAUGHT: Cue("white_brief", "rising_beep"),
    State.LISTENING: Cue("blue", "none"),
    State.ANALYSING: Cue("blue_pulse", "none"),
    State.EXECUTING: Cue("green", "confirm_beep"),
    State.WINDOW: Cue("yellow_countdown", "double_beep"),
    State.CONFIRMING: Cue("yellow", "double_beep"),
    State.SPEAKING: Cue("purple", "none"),
    State.DICTATING: Cue("red", "start_end_beep"),
    State.WARNING: Cue("orange_flash", "warning_tone"),
    State.CANCELLED: Cue("off", "falling_beep"),
}
