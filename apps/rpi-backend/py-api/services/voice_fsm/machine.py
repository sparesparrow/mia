"""The voice state machine (ADR-0011).

``handle(command)`` and ``tick()`` return a list of effects. Time comes from the injected ``clock`` so a
test drives the five second window without sleeping.

Rules implemented here (ADR-0012):
  * Certain parts of a chain run at once; uncertain read, comfort and note parts share one window that
    starts when MIA has finished announcing them.
  * Message and call parts never run on silence; they need an explicit confirmation.
  * Forbidden parts (writes to a control unit) are refused. The class of a part comes from a fixed table,
    so a wrong label can only make a part stricter and an unknown action is forbidden (classes.py).
  * Cancel works without speech recognition. A warning interrupts dictation, listening, the window and
    speech; whatever it cut off is said again before the machine goes on.
  * Utterances and executor batches carry ids, so a stale "done" or an aborted batch changes nothing.
"""

from __future__ import annotations

from collections import deque
from dataclasses import replace
from enum import Enum
from typing import Callable, Deque, Dict, List, Mapping, Optional, Tuple, Union

from .classes import ACTION_CLASSES, effective_class
from .feedback import BUSY_TONE, FEEDBACK
from .types import (
    DICTATE,
    SAVE_NOTE,
    Abort,
    ActionClass,
    Cancel,
    Command,
    Confirm,
    CueName,
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
    SafetyWarning,
    SetVerbosity,
    Speak,
    SpeakingDone,
    State,
    StateChanged,
    StopSpeaking,
    Verbosity,
    Wake,
)

# The oldest queued message is dropped when this many are waiting.
MAX_QUEUED_MESSAGES = 20
MAX_QUEUED_INTENTS = 3


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
        action_classes: Optional[Mapping[str, ActionClass]] = None,
    ) -> None:
        self._clock = clock
        self.window_sec = window_sec
        self.confirm_timeout_sec = confirm_timeout_sec
        self.listen_timeout_sec = listen_timeout_sec
        self.verbosity = verbosity
        self._classes = ACTION_CLASSES if action_classes is None else action_classes

        self._state = State.IDLE
        self._deadline: Optional[float] = None
        # Uncertain parts waiting in the window.
        self._pending: List[Part] = []
        # Message and call parts waiting for an explicit yes.
        self._confirm: List[Part] = []
        self._dictation: List[str] = []
        # Result phrases held back so the microphone stays open while the driver dictates.
        self._held: List[Tuple[str, Dict]] = []

        # Utterances handed to TTS and not yet reported done, oldest first.
        self._playing: List[Speak] = []
        self._next_speak = 1
        self._muted = False
        self._after = _After.NONE
        # State to return to once speech is over (window, confirmation, dictation, listening).
        self._resume: Optional[State] = None
        # Speech a warning cut off, said again before the machine goes on.
        self._repeat: List[Speak] = []

        # Executor batches handed out and not yet reported done.
        self._inflight: List[int] = []
        self._next_batch = 1

        self._intents: Deque[Intent] = deque(maxlen=MAX_QUEUED_INTENTS)
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
            SafetyWarning: self._on_warning,
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
            self._after = _After.NONE
            self._say("confirm.timeout", {}, out)
        elif self._state is State.LISTENING:
            self._go_idle(out)
        return out

    # ── Transitions ────────────────────────────────────────────────────────

    def _cue(self, name: Union[State, CueName], out: List[Effect]) -> None:
        cue = FEEDBACK[name.value]
        out.append(Feedback(name.value, cue.led, cue.tone))

    def _enter(self, state: State, out: List[Effect]) -> None:
        if state is not self._state:
            out.append(StateChanged(self._state, state))
            self._state = state
        self._cue(state, out)

    def _set_mic(self, muted: bool, out: List[Effect]) -> None:
        if muted is not self._muted:
            out.append(MuteMic(muted))
            self._muted = muted

    def _go_idle(self, out: List[Effect], drain: bool = True) -> None:
        self._deadline = None
        if not self._playing:
            self._set_mic(False, out)
        self._enter(State.IDLE, out)
        if not drain:
            return
        if self._intents:
            self._process(self._intents.popleft().parts, out)
        elif self._queue and self.verbosity is not Verbosity.QUIET:
            self._announce_message(self._queue.popleft(), out)

    def _say(
        self, phrase: str, params: Mapping, out: List[Effect], priority: int = 0
    ) -> None:
        speak = Speak(phrase, dict(params), priority, self._next_speak)
        self._next_speak += 1
        self._playing.append(speak)
        out.append(speak)
        self._set_mic(True, out)
        warning_playing = any(s.priority > 0 for s in self._playing[:-1])
        if priority > 0:
            self._enter(State.WARNING, out)
        elif not warning_playing:
            self._enter(State.SPEAKING, out)

    def _stop_speaking(self, out: List[Effect], unmute: bool = True) -> None:
        if self._playing:
            out.append(StopSpeaking())
            self._playing.clear()
        if unmute:
            self._set_mic(False, out)

    def _finish_speaking(self, out: List[Effect]) -> None:
        if self._repeat:
            # A warning cut these off; say them again before going on.
            again, self._repeat = self._repeat, []
            for speak in again:
                self._say(speak.phrase, speak.params, out)
            return
        self._set_mic(False, out)
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
        elif resume is State.LISTENING:
            self._deadline = self._clock() + self.listen_timeout_sec
            self._enter(State.LISTENING, out)
        elif after is _After.WINDOW:
            self._deadline = self._clock() + self.window_sec
            self._enter(State.WINDOW, out)
        elif after is _After.CONFIRM:
            self._deadline = self._clock() + self.confirm_timeout_sec
            self._enter(State.CONFIRMING, out)
        elif after is _After.DICTATE:
            self._enter(State.DICTATING, out)
        elif self._inflight:
            self._enter(State.EXECUTING, out)
        else:
            self._go_idle(out)

    def _drop_chain(self, out: List[Effect]) -> None:
        """Forget everything a chain had pending and abort whatever is running."""
        self._pending.clear()
        self._confirm.clear()
        self._dictation.clear()
        self._held.clear()
        self._intents.clear()
        self._repeat.clear()
        self._after = _After.NONE
        self._resume = None
        for batch_id in self._inflight:
            out.append(Abort(batch_id))
        self._inflight.clear()

    def _cancel_all(self, out: List[Effect]) -> None:
        self._stop_speaking(out)
        self._drop_chain(out)
        self._cue(CueName.CANCELLED, out)
        # Cancel means quiet: queued messages wait for the next time the machine becomes idle.
        self._go_idle(out, drain=False)

    # ── Running parts ──────────────────────────────────────────────────────

    def _class_of(self, part: Part) -> ActionClass:
        return effective_class(part.name, part.action_class, self._classes)

    def _run(self, parts: List[Part], out: List[Effect]) -> None:
        batch = [
            replace(p, action_class=self._class_of(p))
            for p in parts
            if p.name != DICTATE
        ]
        dictate = len(batch) != len(parts)
        if batch:
            batch_id = self._next_batch
            self._next_batch += 1
            self._inflight.append(batch_id)
            out.append(Execute(tuple(batch), batch_id))
            if not self._playing:
                self._enter(State.EXECUTING, out)
        if dictate:
            self._dictation.clear()
            self._held.clear()
            if self._playing:
                self._after = _After.DICTATE
            else:
                self._enter(State.DICTATING, out)

    def _ask_confirm(self, out: List[Effect]) -> None:
        part = self._confirm[0]
        self._say("message.confirm", {"part": part.name, **dict(part.args)}, out)
        self._after = _After.CONFIRM

    def _process(self, parts, out: List[Effect]) -> None:
        self._cue(CueName.ANALYSING, out)
        self._deadline = None
        if not parts:
            self._say("intent.unknown", {}, out)
            return
        if len(parts) > 1 and any(p.name == DICTATE for p in parts):
            # Dictation and other parts cannot be combined: say so rather than lose the dictation.
            self._say("chain.dictation_alone", {}, out)
            return

        runnable: List[Part] = []
        messages: List[Part] = []
        for part in parts:
            klass = self._class_of(part)
            if klass is ActionClass.FORBIDDEN:
                self._say("chain.refused", {"part": part.name}, out)
            elif klass is ActionClass.MESSAGE:
                messages.append(part)
            else:
                runnable.append(part)
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
        elif not (immediate or self._playing):
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
            self._cue(CueName.WAKE_CAUGHT, out)
            self._enter(State.LISTENING, out)
        if self._state is State.LISTENING:
            self._deadline = self._clock() + self.listen_timeout_sec

    def _on_intent(self, cmd: Intent, out: List[Effect]) -> None:
        state = self._state
        if state in (State.IDLE, State.LISTENING):
            self._process(cmd.parts, out)
        elif state in (State.WINDOW, State.CONFIRMING) or (
            state is State.SPEAKING and self._after in (_After.WINDOW, _After.CONFIRM)
        ):
            # A new utterance corrects what was waiting: it replaces it.
            self._pending.clear()
            self._confirm.clear()
            self._after = _After.NONE
            self._stop_speaking(out, unmute=False)
            self._process(cmd.parts, out)
            if not self._playing:
                self._set_mic(False, out)
        elif state in (State.EXECUTING, State.SPEAKING):
            self._intents.append(cmd)
        else:
            # Dictating or in a warning: the utterance cannot be taken, so tell the driver.
            cue = FEEDBACK[state.value]
            out.append(Feedback(state.value, cue.led, BUSY_TONE))

    def _on_go_now(self, cmd: GoNow, out: List[Effect]) -> None:
        if self._state is State.WINDOW:
            self._fire_window(out)
        elif self._state is State.CONFIRMING:
            self._on_confirm(Confirm(cmd.source), out)
        elif self._state is State.SPEAKING:
            self._repeat.clear()
            self._stop_speaking(out, unmute=False)
            if self._after is _After.WINDOW and self._pending:
                # Go now during the announcement runs the part at once.
                self._after = _After.NONE
                self._set_mic(False, out)
                self._fire_window(out)
            else:
                # For a question this skips it; a message then still needs a second, explicit press.
                self._finish_speaking(out)
        elif self._state is State.DICTATING:
            self._on_end_dictation(EndDictation(cmd.source), out)

    def _on_cancel(self, cmd: Cancel, out: List[Effect]) -> None:
        if self._state is State.WARNING:
            # The warning keeps playing; the chain it paused is dropped.
            self._drop_chain(out)
            return
        if self._state is not State.IDLE:
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
        if self._state is State.WINDOW:
            self._on_cancel(Cancel(cmd.source), out)
        elif self._state is State.CONFIRMING:
            # A no drops that message only; the next one is asked about.
            self._confirm.pop(0)
            if self._confirm:
                self._ask_confirm(out)
            else:
                self._cancel_all(out)

    def _on_end_dictation(self, cmd: EndDictation, out: List[Effect]) -> None:
        if self._state is not State.DICTATING:
            return
        text = " ".join(self._dictation).strip()
        self._dictation.clear()
        if text:
            self._run([Part(SAVE_NOTE, ActionClass.NOTE, {"text": text})], out)
        else:
            self._say("note.empty", {}, out)
        held, self._held = self._held, []
        for phrase, params in held:
            self._say(phrase, params, out)

    def _on_dictation_text(self, cmd: DictationText, out: List[Effect]) -> None:
        if self._state is State.DICTATING:
            self._dictation.append(cmd.text)

    def _on_speaking_done(self, cmd: SpeakingDone, out: List[Effect]) -> None:
        if not self._playing:
            return
        if cmd.id is None:
            index = 0
        else:
            index = next((i for i, s in enumerate(self._playing) if s.id == cmd.id), -1)
            if index < 0:
                # Not outstanding: a stale "done" from an utterance that was stopped.
                return
        del self._playing[index]
        if not self._playing:
            self._finish_speaking(out)

    def _on_execution_done(self, cmd: ExecutionDone, out: List[Effect]) -> None:
        if not self._inflight:
            return
        batch_id = self._inflight[0] if cmd.batch_id is None else cmd.batch_id
        if batch_id not in self._inflight:
            # Aborted or unknown batch: its result is dropped.
            return
        self._inflight.remove(batch_id)
        if cmd.phrase:
            if self._state is State.DICTATING:
                self._held.append((cmd.phrase, dict(cmd.params)))
                return
            if (
                self._state in (State.WINDOW, State.CONFIRMING, State.LISTENING)
                and self._resume is None
            ):
                # Report the result, then come back to what was open.
                self._resume = self._state
                self._deadline = None
            self._say(cmd.phrase, cmd.params, out)
        elif not self._inflight and self._state is State.EXECUTING:
            self._go_idle(out)

    def _on_warning(self, cmd: SafetyWarning, out: List[Effect]) -> None:
        if self._state in (
            State.WINDOW,
            State.CONFIRMING,
            State.DICTATING,
            State.LISTENING,
        ):
            self._resume = self._state
        elif self._state is State.SPEAKING:
            # What was being said is said again once the warning is over.
            self._repeat.extend(s for s in self._playing if s.priority == 0)
            self._stop_speaking(out, unmute=False)
        self._deadline = None
        self._say(cmd.phrase, cmd.params, out, priority=1)

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
        if cmd.level is Verbosity.QUIET:
            # Quiet drops both new and waiting messages.
            self._queue.clear()
        if self._state is State.IDLE:
            self._say("verbosity.set", {"level": cmd.level.value}, out)
