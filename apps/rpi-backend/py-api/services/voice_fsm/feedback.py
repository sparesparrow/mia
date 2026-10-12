"""The one table from state to LED colour and tone (spec/interfaces/voice.md).

This module is canonical; the table in voice.md is checked against it by a test. Colours and tones
are defaults to be tuned in the car. A colour must also differ by brightness or pattern, not only
hue, and states where silence means opposite things must not look or sound alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .types import CueName, State


@dataclass(frozen=True)
class Cue:
    led: str
    tone: str


FEEDBACK: Dict[str, Cue] = {
    State.IDLE.value: Cue("off", "none"),
    State.LISTENING.value: Cue("blue", "none"),
    State.EXECUTING.value: Cue("green", "confirm_beep"),
    # Silence runs the action: blinking countdown.
    State.WINDOW.value: Cue("yellow_countdown", "double_beep"),
    # Silence drops the action: steady, with a rising two-note question tone.
    State.CONFIRMING.value: Cue("yellow_solid", "question_tone"),
    State.SPEAKING.value: Cue("purple", "none"),
    State.DICTATING.value: Cue("red", "start_end_beep"),
    State.WARNING.value: Cue("orange_flash", "warning_tone"),
    CueName.WAKE_CAUGHT.value: Cue("white_brief", "rising_beep"),
    CueName.ANALYSING.value: Cue("blue_pulse", "none"),
    CueName.CANCELLED.value: Cue("off", "falling_beep"),
}

BUSY_TONE = "busy_beep"  # an utterance arrived while the machine could not take it
