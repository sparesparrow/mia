"""Dataclasses of ``voice_fsm.types`` to and from the FlatBuffers envelope (REQ-NET-008).

``encode_command`` / ``decode_command`` carry what a peer sends to the machine, ``encode_event`` /
``decode_event`` what the machine sends to peers. Effects that only the machine's own executors need
(``Execute``, ``Abort``, ``StopSpeaking``, ``MuteMic``) are not on the wire: ``encode_event`` returns
None for them. A malformed buffer raises ``CodecError`` and nothing else, so a transport can answer
with a status instead of crashing.
"""

from __future__ import annotations

import os
import re
import sys
from enum import Enum
from struct import error as struct_error
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

import flatbuffers

_GENERATED = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "../../../../../../schemas/generated/python"
    )
)
if _GENERATED not in sys.path:
    sys.path.append(_GENERATED)

from MiaVoice import ActionClass as _WActionClass  # noqa: E402
from MiaVoice import Arg as _WArg  # noqa: E402
from MiaVoice import ArgKind as _WArgKind  # noqa: E402
from MiaVoice import Cancel as _WCancel  # noqa: E402
from MiaVoice import Confirm as _WConfirm  # noqa: E402
from MiaVoice import CueName as _WCueName  # noqa: E402
from MiaVoice import Deny as _WDeny  # noqa: E402
from MiaVoice import DictationText as _WDictationText  # noqa: E402
from MiaVoice import EndDictation as _WEndDictation  # noqa: E402
from MiaVoice import Envelope as _WEnvelope  # noqa: E402
from MiaVoice import ExecutionDone as _WExecutionDone  # noqa: E402
from MiaVoice import FeedbackCue as _WFeedbackCue  # noqa: E402
from MiaVoice import GoNow as _WGoNow  # noqa: E402
from MiaVoice import IncomingMessage as _WIncomingMessage  # noqa: E402
from MiaVoice import Intent as _WIntent  # noqa: E402
from MiaVoice import Led as _WLed  # noqa: E402
from MiaVoice import Part as _WPart  # noqa: E402
from MiaVoice import SafetyWarning as _WSafetyWarning  # noqa: E402
from MiaVoice import SetVerbosity as _WSetVerbosity  # noqa: E402
from MiaVoice import Source as _WSource  # noqa: E402
from MiaVoice import SpeakingDone as _WSpeakingDone  # noqa: E402
from MiaVoice import Spoken as _WSpoken  # noqa: E402
from MiaVoice import State as _WState  # noqa: E402
from MiaVoice import StateChanged as _WStateChanged  # noqa: E402
from MiaVoice import Tone as _WTone  # noqa: E402
from MiaVoice import Transcript as _WTranscript  # noqa: E402
from MiaVoice import Verbosity as _WVerbosity  # noqa: E402
from MiaVoice import VoiceBody as _Body  # noqa: E402
from MiaVoice import VoiceMessage as _WVoiceMessage  # noqa: E402
from MiaVoice import Wake as _WWake  # noqa: E402

from ..types import (  # noqa: E402
    ActionClass,
    Cancel,
    Command,
    Confirm,
    CueName,
    Deny,
    DictationText,
    Effect,
    EndDictation,
    ExecutionDone,
    Feedback,
    GoNow,
    IncomingMessage,
    Intent,
    Part,
    SafetyWarning,
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    StateChanged,
    Verbosity,
    Wake,
)
from .messages import FILE_IDENTIFIER, WIRE_VERSION, Envelope, Transcript  # noqa: E402

# vtable slot of field id 6 (`payload`) in voice.fbs; a test pins it to the generated accessor
_PAYLOAD_VTABLE_OFFSET = 4 + 2 * 6

Event = Union[StateChanged, Feedback, Speak, Transcript]


class CodecError(ValueError):
    """The buffer is not a valid envelope or voice message, or a value cannot be put on the wire."""


# ── Enum mapping ──────────────────────────────────────────────────────────


def _camel(word: str) -> str:
    return "".join(part.capitalize() for part in word.split("_"))


def _snake(word: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", word).lower()


def _wire_members(module: Any) -> Dict[str, int]:
    """Members of the generated enum class inside a generated module (``MiaVoice.Led.Led``)."""
    wire_cls = getattr(module, module.__name__.rsplit(".", 1)[-1])
    return {
        k: v
        for k, v in vars(wire_cls).items()
        if not k.startswith("_") and isinstance(v, int)
    }


def _enum_maps(
    py_enum: Type[Enum], wire_cls: Any
) -> Tuple[Dict[Enum, int], Dict[int, Enum]]:
    members = _wire_members(wire_cls)
    to_wire: Dict[Enum, int] = {}
    for member in py_enum:
        wire_name = _camel(member.name)
        if wire_name not in members:
            raise ImportError(
                f"{py_enum.__name__}.{member.name} has no {wire_cls.__name__}.{wire_name} in voice.fbs"
            )
        to_wire[member] = members[wire_name]
    return to_wire, {v: k for k, v in to_wire.items()}


def _string_maps(wire_cls: Any, silent: str) -> Tuple[Dict[str, int], Dict[int, str]]:
    """Maps for LED colours and tones, which are plain strings in ``feedback.py``."""
    to_wire = {
        (_snake(name) if name != silent else "none"): value
        for name, value in _wire_members(wire_cls).items()
    }
    return to_wire, {v: k for k, v in to_wire.items()}


_SOURCE = _enum_maps(Source, _WSource)
_CLASS = _enum_maps(ActionClass, _WActionClass)
_VERBOSITY = _enum_maps(Verbosity, _WVerbosity)
_STATE = _enum_maps(State, _WState)
_CUE = _enum_maps(CueName, _WCueName)
_LED = _string_maps(_WLed, silent="")
_TONE = _string_maps(_WTone, silent="NoTone")


def _lookup(table: Mapping, key: Any, what: str) -> Any:
    try:
        return table[key]
    except KeyError:
        raise CodecError(f"{what} {key!r} is not in the schema") from None


# ── Builders ──────────────────────────────────────────────────────────────


def _str(b: flatbuffers.Builder, value: Optional[str]) -> int:
    return b.CreateString(value) if value else 0


def _vector(b: flatbuffers.Builder, offsets: Sequence[int]) -> int:
    b.StartVector(4, len(offsets), 4)
    for offset in reversed(offsets):
        b.PrependUOffsetTRelative(offset)
    return b.EndVector()


def _build_args(b: flatbuffers.Builder, args: Mapping[str, Any]) -> int:
    offsets: List[int] = []
    for key, value in args.items():
        key_off = b.CreateString(str(key))
        text_off = 0
        texts_off = 0
        int_value = 0
        real_value = 0.0
        if isinstance(value, bool):
            kind, int_value = _WArgKind.ArgKind.Flag, int(value)
        elif isinstance(value, int):
            kind, int_value = _WArgKind.ArgKind.Int, value
        elif isinstance(value, float):
            kind, real_value = _WArgKind.ArgKind.Real, value
        elif isinstance(value, str):
            kind, text_off = _WArgKind.ArgKind.Text, _str(b, value)
        elif isinstance(value, (list, tuple)) and all(
            isinstance(v, str) for v in value
        ):
            kind = _WArgKind.ArgKind.TextList
            texts_off = _vector(b, [b.CreateString(v) for v in value])
        else:
            raise CodecError(
                f"argument {key!r}: {type(value).__name__} cannot be put on the wire"
            )
        _WArg.ArgStart(b)
        _WArg.ArgAddKey(b, key_off)
        _WArg.ArgAddKind(b, kind)
        if text_off:
            _WArg.ArgAddText(b, text_off)
        _WArg.ArgAddIntValue(b, int_value)
        _WArg.ArgAddRealValue(b, real_value)
        if texts_off:
            _WArg.ArgAddTexts(b, texts_off)
        offsets.append(_WArg.ArgEnd(b))
    return _vector(b, offsets)


def _build_part(b: flatbuffers.Builder, part: Part) -> int:
    name = b.CreateString(part.name)
    args = _build_args(b, part.args) if part.args else 0
    _WPart.PartStart(b)
    _WPart.PartAddName(b, name)
    _WPart.PartAddActionClass(b, _lookup(_CLASS[0], part.action_class, "action class"))
    if args:
        _WPart.PartAddArgs(b, args)
    _WPart.PartAddCertain(b, part.certain)
    return _WPart.PartEnd(b)


def _simple_command(
    wire, body_type: int
) -> Callable[[flatbuffers.Builder, Any], Tuple[int, int]]:
    name = wire.__name__.rsplit(".", 1)[-1]

    def build(b: flatbuffers.Builder, cmd) -> Tuple[int, int]:
        getattr(wire, f"{name}Start")(b)
        getattr(wire, f"{name}AddSource")(b, _lookup(_SOURCE[0], cmd.source, "source"))
        return body_type, getattr(wire, f"{name}End")(b)

    return build


def _build_intent(b, cmd: Intent):
    parts = _vector(b, [_build_part(b, p) for p in cmd.parts])
    _WIntent.IntentStart(b)
    _WIntent.IntentAddParts(b, parts)
    _WIntent.IntentAddSource(b, _lookup(_SOURCE[0], cmd.source, "source"))
    return _Body.VoiceBody.Intent, _WIntent.IntentEnd(b)


def _build_dictation_text(b, cmd: DictationText):
    text = _str(b, cmd.text)
    _WDictationText.DictationTextStart(b)
    if text:
        _WDictationText.DictationTextAddText(b, text)
    return _Body.VoiceBody.DictationText, _WDictationText.DictationTextEnd(b)


def _build_speaking_done(b, cmd: SpeakingDone):
    _WSpeakingDone.SpeakingDoneStart(b)
    _WSpeakingDone.SpeakingDoneAddUtteranceId(b, cmd.id or 0)
    return _Body.VoiceBody.SpeakingDone, _WSpeakingDone.SpeakingDoneEnd(b)


def _build_execution_done(b, cmd: ExecutionDone):
    phrase = _str(b, cmd.phrase)
    params = _build_args(b, cmd.params) if cmd.params else 0
    _WExecutionDone.ExecutionDoneStart(b)
    if phrase:
        _WExecutionDone.ExecutionDoneAddPhrase(b, phrase)
    if params:
        _WExecutionDone.ExecutionDoneAddParams(b, params)
    _WExecutionDone.ExecutionDoneAddBatchId(b, cmd.batch_id or 0)
    return _Body.VoiceBody.ExecutionDone, _WExecutionDone.ExecutionDoneEnd(b)


def _build_warning(b, cmd: SafetyWarning):
    phrase = _str(b, cmd.phrase)
    params = _build_args(b, cmd.params) if cmd.params else 0
    _WSafetyWarning.SafetyWarningStart(b)
    if phrase:
        _WSafetyWarning.SafetyWarningAddPhrase(b, phrase)
    if params:
        _WSafetyWarning.SafetyWarningAddParams(b, params)
    return _Body.VoiceBody.SafetyWarning, _WSafetyWarning.SafetyWarningEnd(b)


def _build_message(b, cmd: IncomingMessage):
    sender, text = _str(b, cmd.sender), _str(b, cmd.text)
    _WIncomingMessage.IncomingMessageStart(b)
    if sender:
        _WIncomingMessage.IncomingMessageAddSender(b, sender)
    if text:
        _WIncomingMessage.IncomingMessageAddText(b, text)
    return _Body.VoiceBody.IncomingMessage, _WIncomingMessage.IncomingMessageEnd(b)


def _build_verbosity(b, cmd: SetVerbosity):
    _WSetVerbosity.SetVerbosityStart(b)
    _WSetVerbosity.SetVerbosityAddLevel(
        b, _lookup(_VERBOSITY[0], cmd.level, "verbosity")
    )
    _WSetVerbosity.SetVerbosityAddSource(b, _lookup(_SOURCE[0], cmd.source, "source"))
    return _Body.VoiceBody.SetVerbosity, _WSetVerbosity.SetVerbosityEnd(b)


_COMMAND_BUILDERS: Dict[type, Callable[[flatbuffers.Builder, Any], Tuple[int, int]]] = {
    Wake: _simple_command(_WWake, _Body.VoiceBody.Wake),
    Intent: _build_intent,
    GoNow: _simple_command(_WGoNow, _Body.VoiceBody.GoNow),
    Cancel: _simple_command(_WCancel, _Body.VoiceBody.Cancel),
    Confirm: _simple_command(_WConfirm, _Body.VoiceBody.Confirm),
    Deny: _simple_command(_WDeny, _Body.VoiceBody.Deny),
    EndDictation: _simple_command(_WEndDictation, _Body.VoiceBody.EndDictation),
    DictationText: _build_dictation_text,
    SpeakingDone: _build_speaking_done,
    ExecutionDone: _build_execution_done,
    SafetyWarning: _build_warning,
    IncomingMessage: _build_message,
    SetVerbosity: _build_verbosity,
}


def _build_state_changed(b, ev: StateChanged):
    _WStateChanged.StateChangedStart(b)
    _WStateChanged.StateChangedAddPrevious(b, _lookup(_STATE[0], ev.previous, "state"))
    _WStateChanged.StateChangedAddCurrent(b, _lookup(_STATE[0], ev.current, "state"))
    return _Body.VoiceBody.StateChanged, _WStateChanged.StateChangedEnd(b)


def _build_feedback(b, ev: Feedback):
    state = 0
    cue = 0
    try:
        state = _STATE[0][State(ev.state)]
    except ValueError:
        try:
            cue = _CUE[0][CueName(ev.state)]
        except ValueError:
            raise CodecError(
                f"feedback state {ev.state!r} is neither a state nor a cue"
            ) from None
    _WFeedbackCue.FeedbackCueStart(b)
    _WFeedbackCue.FeedbackCueAddState(b, state)
    _WFeedbackCue.FeedbackCueAddCue(b, cue)
    _WFeedbackCue.FeedbackCueAddLed(b, _lookup(_LED[0], ev.led, "LED colour"))
    _WFeedbackCue.FeedbackCueAddTone(b, _lookup(_TONE[0], ev.tone, "tone"))
    return _Body.VoiceBody.FeedbackCue, _WFeedbackCue.FeedbackCueEnd(b)


def _build_spoken(b, ev: Speak):
    phrase = _str(b, ev.phrase)
    params = _build_args(b, ev.params) if ev.params else 0
    _WSpoken.SpokenStart(b)
    if phrase:
        _WSpoken.SpokenAddPhrase(b, phrase)
    if params:
        _WSpoken.SpokenAddParams(b, params)
    _WSpoken.SpokenAddPriority(b, ev.priority)
    _WSpoken.SpokenAddUtteranceId(b, ev.id)
    return _Body.VoiceBody.Spoken, _WSpoken.SpokenEnd(b)


def _build_transcript(b, ev: Transcript):
    text = _str(b, ev.text)
    _WTranscript.TranscriptStart(b)
    if text:
        _WTranscript.TranscriptAddText(b, text)
    _WTranscript.TranscriptAddUtteranceId(b, ev.utterance_id)
    return _Body.VoiceBody.Transcript, _WTranscript.TranscriptEnd(b)


_EVENT_BUILDERS: Dict[type, Callable[[flatbuffers.Builder, Any], Tuple[int, int]]] = {
    StateChanged: _build_state_changed,
    Feedback: _build_feedback,
    Speak: _build_spoken,
    Transcript: _build_transcript,
}


def _voice_message(builder_fn: Callable, obj: Any) -> bytes:
    b = flatbuffers.Builder(128)
    try:
        body_type, body = builder_fn(b, obj)
    except (
        OverflowError,
        TypeError,
        struct_error,
    ) as exc:  # value out of range for its field
        raise CodecError(f"{type(obj).__name__}: {exc}") from exc
    _WVoiceMessage.VoiceMessageStart(b)
    _WVoiceMessage.VoiceMessageAddBodyType(b, body_type)
    _WVoiceMessage.VoiceMessageAddBody(b, body)
    b.Finish(_WVoiceMessage.VoiceMessageEnd(b))
    return bytes(b.Output())


# ── Readers ───────────────────────────────────────────────────────────────


def _str_of(value: Optional[bytes]) -> str:
    return value.decode("utf-8") if value else ""


def _read_args(table, length_fn: str, item_fn: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for i in range(getattr(table, length_fn)()):
        arg = getattr(table, item_fn)(i)
        key = _str_of(arg.Key())
        kind = arg.Kind()
        if kind == _WArgKind.ArgKind.Text:
            out[key] = _str_of(arg.Text())
        elif kind == _WArgKind.ArgKind.Int:
            out[key] = arg.IntValue()
        elif kind == _WArgKind.ArgKind.Real:
            out[key] = arg.RealValue()
        elif kind == _WArgKind.ArgKind.Flag:
            out[key] = bool(arg.IntValue())
        elif kind == _WArgKind.ArgKind.TextList:
            out[key] = [_str_of(arg.Texts(j)) for j in range(arg.TextsLength())]
        else:
            raise CodecError(f"argument {key!r} has unknown kind {kind}")
    return out


def _read_part(part) -> Part:
    return Part(
        _str_of(part.Name()),
        _lookup(_CLASS[1], part.ActionClass(), "action class"),
        _read_args(part, "ArgsLength", "Args"),
        part.Certain(),
    )


def _init(cls, body) -> Any:
    obj = cls()
    obj.Init(body.Bytes, body.Pos)
    return obj


def _read_body(body_type: int, body_table) -> Any:
    S = _SOURCE[1]
    if body_type == _Body.VoiceBody.Wake:
        return Wake(_lookup(S, _init(_WWake.Wake, body_table).Source(), "source"))
    if body_type == _Body.VoiceBody.Intent:
        t = _init(_WIntent.Intent, body_table)
        return Intent(
            tuple(_read_part(t.Parts(i)) for i in range(t.PartsLength())),
            _lookup(S, t.Source(), "source"),
        )
    if body_type == _Body.VoiceBody.GoNow:
        return GoNow(_lookup(S, _init(_WGoNow.GoNow, body_table).Source(), "source"))
    if body_type == _Body.VoiceBody.Cancel:
        return Cancel(_lookup(S, _init(_WCancel.Cancel, body_table).Source(), "source"))
    if body_type == _Body.VoiceBody.Confirm:
        return Confirm(
            _lookup(S, _init(_WConfirm.Confirm, body_table).Source(), "source")
        )
    if body_type == _Body.VoiceBody.Deny:
        return Deny(_lookup(S, _init(_WDeny.Deny, body_table).Source(), "source"))
    if body_type == _Body.VoiceBody.EndDictation:
        return EndDictation(
            _lookup(
                S, _init(_WEndDictation.EndDictation, body_table).Source(), "source"
            )
        )
    if body_type == _Body.VoiceBody.DictationText:
        return DictationText(
            _str_of(_init(_WDictationText.DictationText, body_table).Text())
        )
    if body_type == _Body.VoiceBody.SpeakingDone:
        return SpeakingDone(
            _init(_WSpeakingDone.SpeakingDone, body_table).UtteranceId() or None
        )
    if body_type == _Body.VoiceBody.ExecutionDone:
        t = _init(_WExecutionDone.ExecutionDone, body_table)
        return ExecutionDone(
            _str_of(t.Phrase()),
            _read_args(t, "ParamsLength", "Params"),
            t.BatchId() or None,
        )
    if body_type == _Body.VoiceBody.SafetyWarning:
        t = _init(_WSafetyWarning.SafetyWarning, body_table)
        return SafetyWarning(
            _str_of(t.Phrase()), _read_args(t, "ParamsLength", "Params")
        )
    if body_type == _Body.VoiceBody.IncomingMessage:
        t = _init(_WIncomingMessage.IncomingMessage, body_table)
        return IncomingMessage(_str_of(t.Sender()), _str_of(t.Text()))
    if body_type == _Body.VoiceBody.SetVerbosity:
        t = _init(_WSetVerbosity.SetVerbosity, body_table)
        return SetVerbosity(
            _lookup(_VERBOSITY[1], t.Level(), "verbosity"),
            _lookup(S, t.Source(), "source"),
        )
    if body_type == _Body.VoiceBody.StateChanged:
        t = _init(_WStateChanged.StateChanged, body_table)
        return StateChanged(
            _lookup(_STATE[1], t.Previous(), "state"),
            _lookup(_STATE[1], t.Current(), "state"),
        )
    if body_type == _Body.VoiceBody.FeedbackCue:
        t = _init(_WFeedbackCue.FeedbackCue, body_table)
        key = (
            _lookup(_CUE[1], t.Cue(), "cue")
            if t.Cue()
            else _lookup(_STATE[1], t.State(), "state")
        )
        return Feedback(
            key.value,
            _lookup(_LED[1], t.Led(), "LED colour"),
            _lookup(_TONE[1], t.Tone(), "tone"),
        )
    if body_type == _Body.VoiceBody.Spoken:
        t = _init(_WSpoken.Spoken, body_table)
        return Speak(
            _str_of(t.Phrase()),
            _read_args(t, "ParamsLength", "Params"),
            t.Priority(),
            t.UtteranceId(),
        )
    if body_type == _Body.VoiceBody.Transcript:
        t = _init(_WTranscript.Transcript, body_table)
        return Transcript(_str_of(t.Text()), t.UtteranceId())
    raise CodecError(f"unknown voice message type {body_type}")


def _decode_voice_message(data: bytes) -> Any:
    try:
        message = _WVoiceMessage.VoiceMessage.GetRootAs(data, 0)
        body_type = message.BodyType()
        if body_type == _Body.VoiceBody.NONE:
            raise CodecError("voice message has no body")
        body = message.Body()
        if body is None:
            raise CodecError("voice message has no body")
        return _read_body(body_type, body)
    except CodecError:
        raise
    except (
        IndexError,
        ValueError,
        TypeError,
        AttributeError,
        UnicodeDecodeError,
        struct_error,
    ) as exc:
        raise CodecError(f"malformed voice message: {exc}") from exc


# ── Public API ────────────────────────────────────────────────────────────


def encode_command(command: Command) -> bytes:
    """A command as the payload of an envelope."""
    builder = _COMMAND_BUILDERS.get(type(command))
    if builder is None:
        raise CodecError(f"{type(command).__name__} is not a command")
    return _voice_message(builder, command)


def decode_command(payload: bytes) -> Command:
    obj = _decode_voice_message(payload)
    if type(obj) not in _COMMAND_BUILDERS:
        raise CodecError(f"{type(obj).__name__} is an event, not a command")
    return obj


def encode_event(event: Union[Effect, Transcript]) -> Optional[bytes]:
    """An effect or transcript as an envelope payload, or None if it is not for peers.

    ``Execute``, ``Abort``, ``StopSpeaking`` and ``MuteMic`` talk to the machine's own executors and
    microphone, not to a console or an LED node.
    """
    builder = _EVENT_BUILDERS.get(type(event))
    if builder is None:
        return None
    return _voice_message(builder, event)


def decode_event(payload: bytes) -> Event:
    obj = _decode_voice_message(payload)
    if type(obj) not in _EVENT_BUILDERS:
        raise CodecError(f"{type(obj).__name__} is a command, not an event")
    return obj


def encode_envelope(envelope: Envelope) -> bytes:
    b = flatbuffers.Builder(64 + len(envelope.payload))
    session = _str(b, envelope.session_id)
    payload = b.CreateByteVector(envelope.payload) if envelope.payload else 0
    try:
        _WEnvelope.EnvelopeStart(b)
        _WEnvelope.EnvelopeAddVersion(b, envelope.version)
        _WEnvelope.EnvelopeAddService(b, envelope.service)
        if session:
            _WEnvelope.EnvelopeAddSessionId(b, session)
        _WEnvelope.EnvelopeAddOp(b, envelope.op)
        _WEnvelope.EnvelopeAddStatus(b, envelope.status)
        _WEnvelope.EnvelopeAddSeq(b, envelope.seq)
        if payload:
            _WEnvelope.EnvelopeAddPayload(b, payload)
        b.Finish(_WEnvelope.EnvelopeEnd(b), FILE_IDENTIFIER)
    except (OverflowError, TypeError, struct_error) as exc:
        raise CodecError(f"envelope field out of range: {exc}") from exc
    return bytes(b.Output())


def decode_envelope(data: bytes) -> Envelope:
    """Parse an envelope. The version is returned as sent; checking it is the router's job."""
    if len(data) < 8 or not _WEnvelope.Envelope.EnvelopeBufferHasIdentifier(data, 0):
        raise CodecError("not a MIAV envelope")
    try:
        e = _WEnvelope.Envelope.GetRootAs(data, 0)
        # The generated accessor for a byte vector needs numpy, which the Pi does not install.
        length = e.PayloadLength()
        offset = e._tab.Offset(_PAYLOAD_VTABLE_OFFSET)
        payload_bytes = b""
        if length and offset:
            start = e._tab.Vector(offset)
            payload_bytes = bytes(e._tab.Bytes[start : start + length])
            if len(payload_bytes) != length:
                raise CodecError("envelope payload runs past the end of the buffer")
        return Envelope(
            service=e.Service(),
            session_id=_str_of(e.SessionId()),
            op=e.Op(),
            status=e.Status(),
            seq=e.Seq(),
            payload=payload_bytes,
            version=e.Version(),
        )
    except (
        IndexError,
        ValueError,
        TypeError,
        AttributeError,
        UnicodeDecodeError,
        struct_error,
    ) as exc:
        raise CodecError(f"malformed envelope: {exc}") from exc


__all__ = [
    "CodecError",
    "Event",
    "FILE_IDENTIFIER",
    "WIRE_VERSION",
    "decode_command",
    "decode_envelope",
    "decode_event",
    "encode_command",
    "encode_envelope",
    "encode_event",
]
