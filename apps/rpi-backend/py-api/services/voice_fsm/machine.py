"""The voice state machine (ADR-0011).

``handle(command)`` and ``tick()`` return a list of effects. Time comes from the injected
``clock`` so a test drives the five second window without sleeping.

Rules implemented here (ADR-0012):
  * Certain parts of a chain run at once; uncertain read, comfort and note parts share one
    window that starts when MIA has finished announcing them.
  * Message and call parts never run on silence; they need an explicit confirmation.
  * Forbidden parts (writes to a control unit) are refused and never queued.
  * Cancel works without speech recognition; a warning interrupts dictation and the window.
"""

from __future__ import annotations

from collections import deque
from enum import Enum
from typing import Callable, Deque, Dict, List, Optional

from .feedback import FEEDBACK
from .types import (
    DICTATE,
    SAVE_NOTE,
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
    Speak,
    SpeakingDone,
    State,
    StateChanged,
    StopSpeaking,
    Verbosity,
    Wake,
    Warning,
)

MAX_QUEUED_MESSAGES = 20


class _After(Enum):
    """What happens when the current speech is over."""

    NONE = "none"
    WINDOW = "window"
    CONFIRM = "confirm"
    DICTATE = "dictate"


class VoiceMachine:
    def __init__(
        self,
        clock: Callable[[], float],
        window_sec: float = 5.0,
        confirm_timeout_sec: float = 15.0,
        listen_timeout_sec: float = 5.0,
        verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        self._clock = clock
        self.window_sec = window_sec
        self.confirm_timeout_sec = confirm_timeout_sec
        self.listen_timeout_sec = listen_timeout_sec
        self.verbosity = verbosity

        self._state = State.IDLE
        self._pending: List[Part] = []  # uncertain parts waiting in the window
        self._confirm: List[Part] = (
            []
        )  # message and call parts waiting for an explicit yes
        self._dictation: List[str] = []
        self._deadline: Optional[float] = None
        self._speaking = 0
        self._after = _After.NONE
        self._executing = False
        self._resume: Optional[State] = None
        self._queue: Deque[IncomingMessage] = deque(maxlen=MAX_QUEUED_MESSAGES)

        self._handlers: Dict[type, Callable] = {
            Wake: self._on_wake,
            Intent: self._on_intent,
            GoNow: self._on_go_now,
            Cancel: self._on_cancel,
            Confirm: self._on_confirm,
            Deny: self._on_deny,
            EndDictation: self._on_end_dictation,
            DictationText: self._on_dictation_text,
            SpeakingDone: self._on_speaking_done,
            ExecutionDone: self._on_execution_done,
            Warning: self._on_warning,
            IncomingMessage: self._on_message,
            SetVerbosity: self._on_set_verbosity,
        }

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        return self._state

    @property
    def deadline(self) -> Optional[float]:
        return self._deadline

    def handle(self, command: Command) -> List[Effect]:
        out: List[Effect] = []
        handler = self._handlers.get(type(command))
        if handler is not None:
            handler(command, out)
        return out

    def tick(self) -> List[Effect]:
        out: List[Effect] = []
        now = self._clock()
        if self._deadline is None or now < self._deadline:
            return out
        if self._state is State.WINDOW:
            self._fire_window(out)
        elif self._state is State.CONFIRMING:
            self._confirm.clear()
            self._deadline = None
            self._say("confirm.timeout", {}, out)
        elif self._state is State.LISTENING:
            self._go_idle(out)
        return out

    # ── Transitions ────────────────────────────────────────────────────────

    def _cue(self, state: State, out: List[Effect]) -> None:
        cue = FEEDBACK[state]
        out.append(Feedback(state, cue.led, cue.tone))

    def _enter(self, state: State, out: List[Effect]) -> None:
        if state is not self._state:
            out.append(StateChanged(self._state, state))
            self._state = state
        self._cue(state, out)

    def _go_idle(self, out: List[Effect]) -> None:
        self._deadline = None
        self._enter(State.IDLE, out)
        if self._queue and self.verbosity is not Verbosity.QUIET:
            self._announce_message(self._queue.popleft(), out)

    def _say(
        self, phrase: str, params: Dict, out: List[Effect], priority: int = 0
    ) -> None:
        out.append(Speak(phrase, params, priority))
        if self._speaking == 0:
            out.append(MuteMic(True))
        self._speaking += 1
        if priority > 0:
            self._enter(State.WARNING, out)
        elif self._state is not State.WARNING:
            self._enter(State.SPEAKING, out)

    def _finish_speaking(self, out: List[Effect]) -> None:
        out.append(MuteMic(False))
        after, self._after = self._after, _After.NONE
        resume, self._resume = self._resume, None
        if resume is State.WINDOW:
            self._deadline = self._clock() + self.window_sec
            self._enter(State.WINDOW, out)
        elif resume is State.CONFIRMING:
            self._deadline = self._clock() + self.confirm_timeout_sec
            self._enter(State.CONFIRMING, out)
        elif resume is State.DICTATING:
            self._enter(State.DICTATING, out)
        elif after is _After.WINDOW:
            self._deadline = self._clock() + self.window_sec
            self._enter(State.WINDOW, out)
        elif after is _After.CONFIRM:
            self._deadline = self._clock() + self.confirm_timeout_sec
            self._enter(State.CONFIRMING, out)
        elif after is _After.DICTATE:
            self._enter(State.DICTATING, out)
        elif self._executing:
            self._enter(State.EXECUTING, out)
        else:
            self._go_idle(out)

    def _stop_speaking(self, out: List[Effect]) -> None:
        if self._speaking:
            out.append(StopSpeaking())
            out.append(MuteMic(False))
            self._speaking = 0

    def _cancel_all(self, out: List[Effect]) -> None:
        self._stop_speaking(out)
        self._pending.clear()
        self._confirm.clear()
        self._dictation.clear()
        self._after = _After.NONE
        self._resume = None
        self._executing = False
        self._cue(State.CANCELLED, out)
        self._go_idle(out)

    # ── Running parts ──────────────────────────────────────────────────────

    def _run(self, parts: List[Part], out: List[Effect]) -> None:
        batch = [p for p in parts if p.name != DICTATE]
        dictate = len(batch) != len(parts)
        if batch:
            out.append(Execute(tuple(batch)))
            self._executing = True
            if self._speaking == 0:
                self._enter(State.EXECUTING, out)
        if dictate:
            self._dictation.clear()
            if self._speaking:
                self._after = _After.DICTATE
            else:
                self._enter(State.DICTATING, out)

    def _ask_confirm(self, out: List[Effect]) -> None:
        part = self._confirm[0]
        self._say("message.confirm", {"part": part.name, **dict(part.args)}, out)
        self._after = _After.CONFIRM

    def _process(self, parts, out: List[Effect]) -> None:
        self._cue(State.ANALYSING, out)
        self._deadline = None
        if not parts:
            self._say("intent.unknown", {}, out)
            return

        for part in parts:
            if part.action_class is ActionClass.FORBIDDEN:
                self._say("chain.refused", {"part": part.name}, out)
        runnable = [
            p
            for p in parts
            if p.action_class not in (ActionClass.FORBIDDEN, ActionClass.MESSAGE)
        ]
        messages = [p for p in parts if p.action_class is ActionClass.MESSAGE]
        immediate = [p for p in runnable if p.certain]
        uncertain = [p for p in runnable if not p.certain]

        if immediate:
            self._run(immediate, out)
        if uncertain:
            self._pending = uncertain
            self._confirm = messages
            self._say(
                "chain.announce",
                {"parts": [p.name for p in uncertain], "seconds": self.window_sec},
                out,
            )
            self._after = _After.WINDOW
        elif messages:
            self._confirm = messages
            self._ask_confirm(out)
        elif not (immediate or self._speaking):
            self._go_idle(out)

    def _fire_window(self, out: List[Effect]) -> None:
        parts, self._pending = self._pending, []
        self._deadline = None
        self._run(parts, out)
        if self._confirm:
            self._ask_confirm(out)

    # ── Handlers ───────────────────────────────────────────────────────────

    def _on_wake(self, cmd: Wake, out: List[Effect]) -> None:
        if self._state is State.IDLE:
            self._cue(State.WAKE_CAUGHT, out)
            self._enter(State.LISTENING, out)
        if self._state is State.LISTENING:
            self._deadline = self._clock() + self.listen_timeout_sec

    def _on_intent(self, cmd: Intent, out: List[Effect]) -> None:
        if self._state not in (State.IDLE, State.LISTENING, State.WINDOW):
            return
        # A new utterance in the window replaces what was waiting (clarification).
        self._pending.clear()
        self._confirm.clear()
        self._process(cmd.parts, out)

    def _on_go_now(self, cmd: GoNow, out: List[Effect]) -> None:
        if self._state is State.WINDOW:
            self._fire_window(out)
        elif self._state is State.CONFIRMING:
            self._on_confirm(Confirm(cmd.source), out)
        elif self._state is State.SPEAKING:
            self._stop_speaking(out)
            self._finish_speaking(out)
        elif self._state is State.DICTATING:
            self._on_end_dictation(EndDictation(cmd.source), out)

    def _on_cancel(self, cmd: Cancel, out: List[Effect]) -> None:
        if self._state in (
            State.LISTENING,
            State.WINDOW,
            State.CONFIRMING,
            State.SPEAKING,
            State.DICTATING,
            State.EXECUTING,
        ):
            self._cancel_all(out)

    def _on_confirm(self, cmd: Confirm, out: List[Effect]) -> None:
        if self._state is not State.CONFIRMING:
            return
        part = self._confirm.pop(0)
        self._deadline = None
        self._run([part], out)
        if self._confirm:
            self._ask_confirm(out)

    def _on_deny(self, cmd: Deny, out: List[Effect]) -> None:
        if self._state is State.CONFIRMING:
            self._cancel_all(out)

    def _on_end_dictation(self, cmd: EndDictation, out: List[Effect]) -> None:
        if self._state is not State.DICTATING:
            return
        text = " ".join(self._dictation).strip()
        self._dictation.clear()
        if not text:
            self._say("note.empty", {}, out)
            return
        self._run([Part(SAVE_NOTE, ActionClass.NOTE, {"text": text})], out)

    def _on_dictation_text(self, cmd: DictationText, out: List[Effect]) -> None:
        if self._state is State.DICTATING:
            self._dictation.append(cmd.text)

    def _on_speaking_done(self, cmd: SpeakingDone, out: List[Effect]) -> None:
        if self._speaking == 0:
            return
        self._speaking -= 1
        if self._speaking == 0:
            self._finish_speaking(out)

    def _on_execution_done(self, cmd: ExecutionDone, out: List[Effect]) -> None:
        self._executing = False
        if cmd.phrase:
            self._say(cmd.phrase, dict(cmd.params), out)
        elif self._state is State.EXECUTING:
            self._go_idle(out)

    def _on_warning(self, cmd: Warning, out: List[Effect]) -> None:
        if self._state in (State.WINDOW, State.CONFIRMING, State.DICTATING):
            self._resume = self._state
        elif self._state is State.SPEAKING:
            self._stop_speaking(
                out
            )  # the announcement continues after the warning (_after is kept)
        self._deadline = None
        self._say(cmd.phrase, dict(cmd.params), out, priority=1)

    def _on_message(self, cmd: IncomingMessage, out: List[Effect]) -> None:
        if self.verbosity is Verbosity.QUIET:
            return
        if self._state is State.IDLE:
            self._announce_message(cmd, out)
        else:
            self._queue.append(cmd)

    def _announce_message(self, msg: IncomingMessage, out: List[Effect]) -> None:
        if self.verbosity is Verbosity.CHATTY:
            self._say("message.read", {"sender": msg.sender, "text": msg.text}, out)
        else:
            self._say("message.arrived", {"sender": msg.sender}, out)

    def _on_set_verbosity(self, cmd: SetVerbosity, out: List[Effect]) -> None:
        self.verbosity = cmd.level
        if self._state is State.IDLE:
            self._say("verbosity.set", {"level": cmd.level.value}, out)
