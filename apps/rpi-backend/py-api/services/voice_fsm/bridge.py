"""Bridge between the voice router's I/O and the state machine (ADR-0011, REQ-VOICE-011).

The router stays a thin shell: it feeds transcripts, wake events and TTS events in and publishes what
comes out. All decisions are the machine's. Every dependency is injected so the bridge is tested with
fakes and a fake clock, with no ZeroMQ and no audio.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .events import FINISHED
from .machine import VoiceMachine
from .types import (
    Abort,
    ActionClass,
    Cancel,
    Command,
    Confirm,
    Deny,
    Effect,
    Execute,
    ExecutionDone,
    Feedback,
    GoNow,
    Intent,
    Part,
    Settings,
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    Verbosity,
    Wake,
)

YES_WORDS = (
    "yes",
    "yeah",
    "yep",
    "correct",
    "do it",
    "go ahead",
    "confirm",
    "sure",
    "ok",
    "okay",
    "affirmative",
)
NO_WORDS = (
    "no",
    "nope",
    "cancel",
    "never mind",
    "nevermind",
    "stop",
    "don't",
    "negative",
)

# Default wording. The persona layer (ADR-0015) replaces this table; the machine only knows keys.
DEFAULT_PHRASES: Dict[str, str] = {
    "chain.announce": "I will {parts} in {seconds:.0f} seconds. Say stop or press cancel.",
    "chain.refused": "I can't do that: {part}.",
    "message.confirm": "Send it? Say yes or no.",
    "confirm.timeout": "No answer, so I did not send it.",
    "intent.unknown": "Sorry, I didn't understand.",
    "note.empty": "The note was empty.",
    "message.arrived": "New message from {sender}.",
    "message.read": "Message from {sender}: {text}",
    "verbosity.set": "Okay, {level}.",
}

logger = logging.getLogger(__name__)

# The longest reply that still counts as a yes or a no.
MAX_ANSWER_WORDS = 3

# "quiet mode", "switch to chatty mode": the verbosity setting by voice (REQ-VOICE-017). Only a short
# sentence that is nothing but the setting counts, so "read the quiet mode settings of the radio" is a request.
_MODE_COMMAND = re.compile(
    r"^(?:(?:switch|change|go|set)(?: it)? (?:to|into) |be )?(quiet|normal|chatty) mode[.!]?$"
)

Route = Optional[Tuple[str, Dict[str, Any], float]]


def render_phrase(
    phrase: str, params: Dict[str, Any], table: Optional[Dict[str, str]] = None
) -> str:
    """Turn a phrase key and parameters into text. ``raw`` carries ready text from an executor."""
    if phrase == "raw":
        return str(params.get("text", ""))
    template = (table or DEFAULT_PHRASES).get(phrase)
    if template is None:
        return phrase
    values = dict(params)
    if isinstance(values.get("parts"), (list, tuple)):
        values["parts"] = ", ".join(str(p) for p in values["parts"])
    try:
        return template.format(**values)
    except (KeyError, ValueError, IndexError):
        return template


def parts_from_route(match: Route, confirm_threshold: float) -> Tuple[Part, ...]:
    """One router match becomes one part; the match confidence decides if it is certain."""
    if match is None:
        return ()
    label, action, confidence = match
    klass = (
        ActionClass.COMFORT
        if str(action.get("endpoint", "")).startswith("/led")
        else ActionClass.READ
    )
    return (
        Part(label, klass, {"action": action}, certain=confidence >= confirm_threshold),
    )


def _says(text: str, words: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lowered) for w in words)


class RouterBridge:
    def __init__(
        self,
        machine: VoiceMachine,
        classify: Callable[[str], Tuple[Part, ...]],
        execute: Callable[[Part], str],
        publish_text: Callable[[str, int], None],
        publish_feedback: Callable[[Feedback], None] = lambda fb: None,
        phrases: Optional[Dict[str, str]] = None,
        on_settings: Callable[[Settings], None] = lambda settings: None,
    ) -> None:
        self.machine = machine
        self._classify = classify
        self._execute = execute
        self._publish_text = publish_text
        self._publish_feedback = publish_feedback
        self._phrases = phrases
        self._on_settings = on_settings

    # ── Inputs ─────────────────────────────────────────────────────────────

    def on_wake(self) -> None:
        self._apply(self.machine.handle(Wake(Source.VOICE)))

    def on_transcript(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        state = self.machine.state
        # Only a short reply is an answer to a question or to the window. A longer sentence that happens to
        # contain "yes" or "no" is a correction ("okay so send it to Jana instead") and is routed anew.
        if len(text.split()) <= MAX_ANSWER_WORDS:
            if state is State.CONFIRMING:
                if _says(text, NO_WORDS):
                    return self._apply(self.machine.handle(Deny(Source.VOICE)))
                if _says(text, YES_WORDS):
                    return self._apply(self.machine.handle(Confirm(Source.VOICE)))
            elif state is State.WINDOW:
                if _says(text, NO_WORDS):
                    return self._apply(self.machine.handle(Cancel(Source.VOICE)))
                if _says(text, YES_WORDS):
                    return self._apply(self.machine.handle(GoNow(Source.VOICE)))
        mode = _MODE_COMMAND.match(" ".join(text.lower().split()))
        if mode:
            level = Verbosity(mode.group(1))
            return self._apply(self.machine.handle(SetVerbosity(level, Source.VOICE)))
        self._apply(self.machine.handle(Intent(self._classify(text), Source.VOICE)))

    def on_speaking(
        self, event: Optional[str], utterance_id: Optional[int] = None
    ) -> None:
        if event == FINISHED:
            self._apply(self.machine.handle(SpeakingDone(utterance_id)))

    def poll(self) -> None:
        self._apply(self.machine.tick())

    # ── Effects ────────────────────────────────────────────────────────────

    def _apply(self, effects: List[Effect]) -> None:
        # Publish everything this step produced before feeding anything back: a command fed back
        # mid-list would make the machine emit newer effects that older ones in this list then overtake.
        follow_up: List[Command] = []
        for effect in effects:
            if isinstance(effect, Speak):
                text = render_phrase(effect.phrase, dict(effect.params), self._phrases)
                if text:
                    self._publish_text(text, effect.id)
                else:  # nothing to say, so nothing will announce that speech ended
                    follow_up.append(SpeakingDone(effect.id))
            elif isinstance(effect, Feedback):
                self._publish_feedback(effect)
            elif isinstance(effect, Settings):
                self._on_settings(effect)
            elif isinstance(effect, Execute):
                results = [self._execute(part) for part in effect.parts]
                text = " ".join(r for r in results if r)
                follow_up.append(
                    ExecutionDone(
                        "raw" if text else "", {"text": text}, effect.batch_id
                    )
                )
            elif isinstance(effect, Abort):
                # The router's executor is synchronous, so the batch has already finished by now.
                logger.info(
                    "Abort for batch %s ignored: already finished", effect.batch_id
                )
        for command in follow_up:
            self._apply(self.machine.handle(command))
