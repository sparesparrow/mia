"""FlatBuffers envelope and voice messages: schema, generated bindings and codec (REQ-NET-008).

Runs without flatc, a socket or a clock. The one test that regenerates the bindings skips when
flatc is not installed; CI's schema-validation job runs the same comparison.
"""

import importlib.util
import random
import shutil
import subprocess
import typing
from pathlib import Path

import pytest
from services.voice_fsm import (
    BUSY_TONE,
    FEEDBACK,
    Abort,
    ActionClass,
    Cancel,
    Command,
    Confirm,
    CueName,
    Deny,
    DictationText,
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
    Settings,
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    StateChanged,
    StopSpeaking,
    Verbosity,
    Wake,
)
from services.voice_fsm.wire import codec
from services.voice_fsm.wire.codec import (
    CodecError,
    decode_command,
    decode_envelope,
    decode_event,
    encode_command,
    encode_envelope,
    encode_event,
)
from services.voice_fsm.wire.messages import (
    WIRE_VERSION,
    Envelope,
    Op,
    Service,
    Status,
    Transcript,
)

pytestmark = pytest.mark.req("REQ-NET-008")

REPO_ROOT = Path(__file__).resolve().parents[3]

COMMANDS = [
    Wake(),
    Wake(Source.BUTTON),
    Intent(
        (
            Part(
                "read.voltage",
                ActionClass.READ,
                {"unit": "V", "count": 3, "ratio": 1.5, "loud": True},
                False,
            ),
            Part("lights.on", ActionClass.COMFORT),
        ),
        Source.CONSOLE,
    ),
    Intent(()),
    GoNow(),
    Cancel(Source.CONSOLE),
    Confirm(),
    Deny(Source.BUTTON),
    EndDictation(),
    DictationText("zapni světla a řekni napětí"),
    DictationText(""),
    SpeakingDone(),
    SpeakingDone(4),
    ExecutionDone("read.result", {"value": 12.4, "name": "voltage"}, 3),
    ExecutionDone(),
    SafetyWarning("warn.coolant", {"value": 112, "unit": "C"}),
    IncomingMessage("Jana", "Přijedu později"),
    SetVerbosity(Verbosity.CHATTY, Source.CONSOLE),
]

EVENTS = [
    StateChanged(State.IDLE, State.WINDOW),
    Feedback("window", "yellow_countdown", "double_beep"),
    Feedback("cancelled", "off", "falling_beep"),
    Feedback("idle", "off", "none"),
    Feedback("confirming", "yellow_solid", BUSY_TONE),
    Speak("announce.part", {"what": "lights"}, 1, 5),
    Speak("greeting"),
    Speak(
        "chain.announce", {"parts": ["lights.on", "read.voltage"], "seconds": 5.0}, 0, 2
    ),
    Speak("empty.list", {"parts": []}),
    Transcript("hello", 2),
    Settings(Verbosity.QUIET),
    Settings(Verbosity.CHATTY),
]


def test_every_command_type_is_covered_by_the_round_trip_list():
    assert {type(c) for c in COMMANDS} == set(typing.get_args(Command))


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: type(c).__name__)
def test_command_round_trips(command):
    assert decode_command(encode_command(command)) == command


@pytest.mark.parametrize("event", EVENTS, ids=lambda e: type(e).__name__)
def test_event_round_trips(event):
    assert decode_event(encode_event(event)) == event


def test_executor_effects_are_not_on_the_wire():
    for internal in (Execute((), 1), Abort(1), StopSpeaking(), MuteMic(True)):
        assert encode_event(internal) is None


def test_a_command_is_not_an_event_and_the_reverse():
    with pytest.raises(CodecError):
        decode_event(encode_command(GoNow()))
    with pytest.raises(CodecError):
        decode_command(encode_event(StateChanged(State.IDLE, State.LISTENING)))
    with pytest.raises(CodecError):
        encode_command(Speak("x"))


def test_the_machines_own_feedback_table_is_fully_on_the_wire():
    for key, cue in FEEDBACK.items():
        event = Feedback(key, cue.led, cue.tone)
        assert decode_event(encode_event(event)) == event


def test_envelope_round_trips_with_its_payload():
    payload = encode_command(Wake(Source.CONSOLE))
    envelope = Envelope(Service.VOICE, "console-1", Op.DATA, Status.OK, 7, payload)
    decoded = decode_envelope(encode_envelope(envelope))
    assert decoded == envelope
    assert decode_command(decoded.payload) == Wake(Source.CONSOLE)


def test_envelope_without_payload_or_session_round_trips():
    empty = Envelope(Service.UNKNOWN, "", Op.OPEN, Status.NOT_PERMITTED, 0)
    assert decode_envelope(encode_envelope(empty)) == empty


def test_envelope_carries_the_file_identifier_and_version():
    data = encode_envelope(Envelope())
    assert data[4:8] == b"MIAV"
    assert decode_envelope(data).version == WIRE_VERSION


def test_a_future_version_is_decoded_as_sent_so_the_router_can_answer_it():
    assert decode_envelope(encode_envelope(Envelope(version=9))).version == 9


@pytest.mark.parametrize(
    "garbage",
    [
        b"",
        b"\x00" * 3,
        b"not a flatbuffer at all",
        encode_command(Wake()),
        encode_envelope(Envelope())[:11],
    ],
)
def test_garbage_is_a_codec_error(garbage):
    with pytest.raises(CodecError):
        decode_envelope(garbage)


def test_values_that_do_not_fit_the_schema_are_codec_errors():
    with pytest.raises(CodecError):
        encode_command(ExecutionDone("x", {"bad": [1, 2]}))
    with pytest.raises(CodecError):
        encode_command(ExecutionDone("x", {"bad": {"nested": "dict"}}))
    with pytest.raises(CodecError):
        encode_envelope(Envelope(seq=2**40))
    with pytest.raises(CodecError):
        encode_event(Feedback("idle", "ultraviolet", "none"))
    with pytest.raises(CodecError):
        encode_event(Feedback("no-such-state", "off", "none"))


def test_flipped_and_truncated_bytes_only_ever_raise_codec_error():
    rng = random.Random(7)
    samples = [
        (
            decode_envelope,
            encode_envelope(
                Envelope(
                    Service.VOICE,
                    "s",
                    Op.DATA,
                    Status.OK,
                    3,
                    encode_command(COMMANDS[2]),
                )
            ),
        ),
        (decode_command, encode_command(COMMANDS[2])),
        (decode_event, encode_event(EVENTS[5])),
    ]
    for decode, good in samples:
        for _ in range(1500):
            data = bytearray(good)
            for _ in range(rng.randint(1, 4)):
                data[rng.randrange(len(data))] = rng.randrange(256)
            if rng.random() < 0.3:
                data = data[: rng.randrange(len(data))]
            try:
                decode(bytes(data))
            except CodecError:
                pass


# ── The schema, the generated bindings and the Python types agree ─────────


def _generated(module_name):
    module = __import__(f"MiaVoice.{module_name}", fromlist=[module_name])
    cls = getattr(module, module_name)
    return {
        k: v
        for k, v in vars(cls).items()
        if not k.startswith("_") and isinstance(v, int)
    }


@pytest.mark.parametrize(
    "py_enum, schema_enum",
    [(Service, "ServiceType"), (Op, "Op"), (Status, "Status")],
)
def test_envelope_enums_match_the_generated_bindings(py_enum, schema_enum):
    generated = _generated(schema_enum)
    assert {codec._camel(m.name): m.value for m in py_enum} == generated


@pytest.mark.parametrize(
    "py_enum, schema_enum, extra",
    [
        (State, "State", {}),
        (CueName, "CueName", {"NoCue": 0}),
        (Source, "Source", {}),
        (ActionClass, "ActionClass", {}),
        (Verbosity, "Verbosity", {}),
    ],
)
def test_every_schema_value_has_a_python_twin_and_the_reverse(
    py_enum, schema_enum, extra
):
    generated = _generated(schema_enum)
    mapped = {
        codec._camel(m.name): codec._enum_maps(
            py_enum, __import__(f"MiaVoice.{schema_enum}", fromlist=["x"])
        )[0][m]
        for m in py_enum
    }
    assert {**mapped, **extra} == generated


def test_led_and_tone_values_are_exactly_those_the_feedback_table_uses():
    leds = {cue.led for cue in FEEDBACK.values()}
    tones = {cue.tone for cue in FEEDBACK.values()} | {BUSY_TONE}
    assert set(codec._LED[0]) == leds
    assert set(codec._TONE[0]) == tones


def test_payload_offset_constant_matches_the_generated_accessor():
    data = encode_envelope(Envelope(payload=b"\x01\x02\x03"))
    from MiaVoice.Envelope import Envelope as Generated

    root = Generated.GetRootAs(data, 0)
    assert root._tab.Offset(codec._PAYLOAD_VTABLE_OFFSET) != 0
    assert root.PayloadLength() == 3


def _load_extractor():
    spec = importlib.util.spec_from_file_location(
        "extract_enums", REPO_ROOT / "tools" / "schemas" / "extract_enums.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enum_only_header_is_current_and_matches_the_generated_bindings():
    extractor = _load_extractor()
    assert extractor.HEADER.read_text(encoding="utf-8") == extractor.build()
    for name, _, members in extractor.parse_enums(
        extractor.SCHEMA.read_text(encoding="utf-8")
    ):
        if name == "VoiceBody":
            continue
        assert dict(members) == _generated(name), name


@pytest.mark.skipif(shutil.which("flatc") is None, reason="flatc not installed")
def test_committed_bindings_are_what_flatc_generates(tmp_path):
    subprocess.run(
        [
            "flatc",
            "--python",
            "-o",
            str(tmp_path),
            str(REPO_ROOT / "schemas" / "voice.fbs"),
        ],
        check=True,
    )
    committed = REPO_ROOT / "schemas" / "generated" / "python" / "MiaVoice"
    fresh = tmp_path / "MiaVoice"
    assert {p.name for p in fresh.glob("*.py")} == {
        p.name for p in committed.glob("*.py")
    }
    for path in fresh.glob("*.py"):
        assert path.read_text() == (committed / path.name).read_text(), path.name


def _voice_messages_section():
    text = (REPO_ROOT / "spec" / "interfaces" / "voice.md").read_text(encoding="utf-8")
    start = text.index("### Voice messages")
    end = text.index("\n### ", start + 1)
    return text[start:end]


def test_the_interface_spec_lists_exactly_the_messages_in_the_schema():
    import re

    rows = [
        line
        for line in _voice_messages_section().splitlines()
        if line.startswith("| `")
    ]
    listed = {
        name for row in rows for name in re.findall(r"`(\w+)`", row.split("|")[1])
    }
    assert listed == set(_generated("VoiceBody")) - {"NONE"}


def test_the_interface_spec_names_the_commands_a_console_may_send():
    import re

    from services.voice_fsm.wire import PEER_COMMANDS

    (row,) = [
        line
        for line in _voice_messages_section().splitlines()
        if "allowed from a console" in line
    ]
    assert set(re.findall(r"`(\w+)`", row.split("|")[1])) == {
        c.__name__ for c in PEER_COMMANDS
    }


# ── Fixtures shared with the Android unit tests ───────────────────────────


def _load_fixture_tool():
    spec = importlib.util.spec_from_file_location(
        "gen_voice_fixtures", REPO_ROOT / "tools" / "schemas" / "gen_voice_fixtures.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_voice_fixtures_are_what_the_codec_encodes_today():
    tool = _load_fixture_tool()
    assert tool.OUT.read_text(encoding="utf-8") == tool.render()


def _snake_case(name):
    import re

    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def test_every_committed_voice_fixture_decodes_to_what_it_claims():
    import json

    cases = json.loads(_load_fixture_tool().OUT.read_text(encoding="utf-8"))["cases"]
    assert {c["type"] for c in cases} == {"open", "command", "event", "reply"}
    for case in cases:
        envelope = decode_envelope(bytes.fromhex(case["hex"]))
        assert (envelope.session_id, envelope.seq) == (
            case["session"],
            case["seq"],
        ), case["name"]
        if case["type"] == "open":
            assert envelope.op == Op.OPEN
        elif case["type"] == "reply":
            assert (
                envelope.status == Status[case["status"].upper()]
                and not envelope.payload
            )
        elif case["type"] == "command":
            command = decode_command(envelope.payload)
            assert command.source is Source.CONSOLE
            if isinstance(command, SetVerbosity):
                assert case["command"] == f"verbosity_{command.level.value}"
            else:
                assert case["command"] == _snake_case(type(command).__name__)
        else:
            event = decode_event(envelope.payload)
            expect = case["event"]
            assert _snake_case(type(event).__name__) == {"spoken": "speak"}.get(
                expect["kind"], expect["kind"]
            )
            if isinstance(event, Settings):
                assert event.verbosity.value == expect["verbosity"], case["name"]
