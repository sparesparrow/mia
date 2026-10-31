"""Bridge between the voice router's I/O and the state machine (ADR-0011, REQ-VOICE-011).

The router stays a thin shell: it feeds transcripts, wake events and TTS events in and publishes what
comes out. All decisions are the machine's. Every dependency is injected so the bridge is tested with
fakes and a fake clock, with no ZeroMQ and no audio.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .events import FINISHED
from .machine import VoiceMachine
from .personas import Phrasebook
from .phrases import (  # noqa: F401  (re-exported for callers and tests)
    DEFAULT_PHRASES,
    render_phrase,
)
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
    SetLanguage,
    Settings,
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    StateChanged,
    SwitchPersona,
    Verbosity,
    Wake,
)
from .wire.messages import Transcript

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

logger = logging.getLogger(__name__)

# The longest reply that still counts as a yes or a no.
MAX_ANSWER_WORDS = 3

# "quiet mode", "switch to chatty mode": the verbosity setting by voice (REQ-VOICE-017). Only a short
# sentence that is nothing but the setting counts, so "read the quiet mode settings of the radio" is a request.
_MODE_COMMAND = re.compile(
    r"^(?:(?:switch|change|go|set)(?: it)? (?:to|into) |be )?(quiet|normal|chatty) mode[.!]?$"
)
# "change persona" takes the next one; "switch to holly" or "persona rimmer" names one (ADR-0015).
_NEXT_PERSONA = re.compile(r"^(?:change|switch|next)(?: the)? persona[.!]?$")
_NAMED_PERSONA = re.compile(r"^(?:switch to|persona|be) ([a-z]+)[.!]?$")
# "speak czech": what MIA says, not what she understands (recognition stays English, #179).
_LANGUAGE_COMMAND = re.compile(r"^(?:speak|switch to|use) (czech|english)[.!]?$")
_LANGUAGE_CODES = {"czech": "cs", "english": "en"}

# What an observer is told: the machine's effects, and the transcript that caused them.
Observed = Union[Effect, Transcript]
Observer = Callable[[Sequence[Observed]], None]

Route = Optional[Tuple[str, Dict[str, Any], float]]


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
        phrasebook: Optional[Phrasebook] = None,
        on_listen: Callable[[], None] = lambda: None,
    ) -> None:
        self.machine = machine
        self._classify = classify
        self._execute = execute
        self._publish_text = publish_text
        self._publish_feedback = publish_feedback
        self._phrases = phrases
        self._on_settings = on_settings
        self._phrasebook = phrasebook
        # Called when a Wake that did not come from speech has put the machine into ``listening``, so the
        # recogniser can start recording although no wake word was heard (ADR-0020).
        self._on_listen = on_listen
        # Told about every effect list and transcript, whatever started it (speech, a console, TTS, the clock).
        self.observers: List[Observer] = []

    # ── Inputs ─────────────────────────────────────────────────────────────

    def on_wake(self) -> None:
        self._apply(self.machine.handle(Wake(Source.VOICE)))

    def submit(self, command: Command) -> List[Effect]:
        """Apply a command that is already trusted and return the effects it produced.

        The effects are applied here exactly once (spoken, published, executed) and observers are told, so the
        caller only has to encode what it gets back; it must not apply them again.
        """
        effects = self.machine.handle(command)
        self._apply(effects)
        if (
            isinstance(command, Wake)
            and command.source is not Source.VOICE
            and any(
                isinstance(e, StateChanged) and e.current is State.LISTENING
                for e in effects
            )
        ):
            self._on_listen()
        return effects

    def on_transcript(self, text: str, source: Source = Source.VOICE) -> None:
        text = text.strip()
        if not text:
            return
        self._notify([Transcript(text)])
        state = self.machine.state
        # Only a short reply is an answer to a question or to the window. A longer sentence that happens to
        # contain "yes" or "no" is a correction ("okay so send it to Jana instead") and is routed anew.
        if len(text.split()) <= MAX_ANSWER_WORDS:
            if state is State.CONFIRMING:
                if _says(text, NO_WORDS):
                    return self._apply(self.machine.handle(Deny(source)))
                if _says(text, YES_WORDS):
                    return self._apply(self.machine.handle(Confirm(source)))
            elif state is State.WINDOW:
                if _says(text, NO_WORDS):
                    return self._apply(self.machine.handle(Cancel(source)))
                if _says(text, YES_WORDS):
                    return self._apply(self.machine.handle(GoNow(source)))
        setting = self._setting(" ".join(text.lower().split()), source)
        if setting is not None:
            return self._apply(self.machine.handle(setting))
        self._apply(self.machine.handle(Intent(self._classify(text), source)))

    def _setting(self, said: str, source: Source = Source.VOICE) -> Optional[Command]:
        """A spoken settings command, or None when the sentence is something else."""
        mode = _MODE_COMMAND.match(said)
        if mode:
            return SetVerbosity(Verbosity(mode.group(1)), source)
        if _NEXT_PERSONA.match(said):
            return SwitchPersona("", source)
        named = _NAMED_PERSONA.match(said)
        if named and named.group(1) in self.machine.personas:
            return SwitchPersona(named.group(1), source)
        language = _LANGUAGE_COMMAND.match(said)
        if language:
            return SetLanguage(_LANGUAGE_CODES[language.group(1)], source)
        return None

    def render(self, effect: Speak) -> str:
        """The words for ``effect`` in the persona and language the machine uses now."""
        if self._phrasebook is not None:
            return self._phrasebook.render(
                effect.phrase,
                dict(effect.params),
                self.machine.persona,
                self.machine.language,
            )
        return render_phrase(effect.phrase, dict(effect.params), self._phrases)

    def on_speaking(
        self, event: Optional[str], utterance_id: Optional[int] = None
    ) -> None:
        if event == FINISHED:
            self._apply(self.machine.handle(SpeakingDone(utterance_id)))

    def poll(self) -> None:
        self._apply(self.machine.tick())

    # ── Effects ────────────────────────────────────────────────────────────

    def _notify(self, items: Sequence[Observed]) -> None:
        if not items:
            return
        for observer in list(self.observers):
            try:
                observer(items)
            except Exception:  # an observer must never stop the voice loop
                logger.exception("voice observer failed")

    def _apply(self, effects: List[Effect]) -> None:
        self._notify(effects)
        # Publish everything this step produced before feeding anything back: a command fed back
        # mid-list would make the machine emit newer effects that older ones in this list then overtake.
        follow_up: List[Command] = []
        for effect in effects:
            if isinstance(effect, Speak):
                text = self.render(effect)
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
