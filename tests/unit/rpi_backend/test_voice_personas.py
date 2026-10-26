"""Personas Holly and Rimmer in Czech and English, and the language MIA speaks (REQ-VOICE-019, ADR-0015).

Fakes and a fake clock: no ZeroMQ, no audio. Persona packages are read from the repository, and broken ones are
written to pytest's temporary directory.
"""

import json

import pytest
import yaml
from services import tts_service
from services.voice_fsm import (
    SetLanguage,
    Settings,
    Source,
    Speak,
    State,
    SwitchPersona,
    Verbosity,
    VoiceMachine,
    Wake,
)
from services.voice_fsm.bridge import RouterBridge
from services.voice_fsm.events import FINISHED
from services.voice_fsm.personas import (
    LANGUAGES,
    PersonaError,
    Phrasebook,
    load_personas,
    parse_persona,
)
from services.voice_fsm.phrases import DEFAULT_PHRASES, SAMPLE_PARAMS
from services.voice_fsm.safety import SAFETY_FRAGMENTS, WARNING_KEYS, render_fragment
from services.voice_fsm.settings_store import FILE_NAME, SettingsStore
from services.voice_fsm.wire import (
    Envelope,
    EnvelopeRouter,
    Op,
    Service,
    Status,
    VoiceService,
    decode_envelope,
    decode_event,
    encode_command,
    encode_envelope,
)

pytestmark = pytest.mark.req("REQ-VOICE-019")

BOOK = Phrasebook.load()
WARNING_VALUES = {
    "warning.coolant_high": 112,
    "warning.battery_low": 11.2,
    "warning.battery_high": 15.1,
    "warning.rpm_high": 6400,
}


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def _machine(**kwargs):
    return VoiceMachine(
        Clock(), personas=BOOK.names, languages=BOOK.languages, **kwargs
    )


# ── Packages ──────────────────────────────────────────────────────────────


def test_holly_and_rimmer_load_beside_mias_own_wording():
    assert BOOK.names == ("mia", "holly", "rimmer")
    assert BOOK.languages == ("cs", "en")
    assert BOOK.display("holly") == "Holly" and BOOK.display("mia") == "MIA"


@pytest.mark.parametrize("persona", ["holly", "rimmer"])
@pytest.mark.parametrize("language", LANGUAGES)
def test_each_package_words_every_phrase_in_both_languages(persona, language):
    for key in DEFAULT_PHRASES:
        text = BOOK.render(key, SAMPLE_PARAMS.get(key, {}), persona, language)
        assert text and text != key and "{" not in text, (persona, language, key)


@pytest.mark.parametrize("persona", BOOK.names)
@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("key", sorted(WARNING_KEYS))
def test_every_warning_starts_with_the_shared_fragment_in_every_persona(
    persona, language, key
):
    params = {"value": WARNING_VALUES[key]}
    fragment = render_fragment(key, params, language)
    parked = BOOK.render(key, params, persona, language)
    moving = BOOK.render(key, {**params, "moving": True}, persona, language)

    assert parked.startswith(fragment)
    assert moving == fragment  # no framing while the car moves
    framing = parked[len(fragment) :].strip()
    if persona == "mia":
        assert framing == ""
    else:
        assert framing.count(".") + framing.count("!") + framing.count("?") <= 1


def test_the_fragment_names_value_and_unit_in_each_language():
    assert render_fragment("warning.battery_low", {"value": 11.24}, "cs").startswith(
        "Napětí baterie 11,2 voltu."
    )
    assert render_fragment("warning.coolant_high", {"value": 112.7}, "en").startswith(
        "Coolant at 112 degrees."
    )
    assert set(SAFETY_FRAGMENTS["cs"]) == set(SAFETY_FRAGMENTS["en"]) == WARNING_KEYS


def test_a_warning_without_a_value_or_fragment_is_still_a_warning():
    assert render_fragment("warning.coolant_high", {}, "cs").startswith("Varování")
    assert BOOK.render("warning.unknown", {"value": 3}, "rimmer", "en").startswith(
        "Car warning."
    )


def test_codes_are_said_as_words_of_the_language():
    assert (
        BOOK.render("verbosity.set", {"level": "quiet"}, "mia", "cs")
        == "Dobře, režim tichý."
    )
    assert (
        BOOK.render("persona.set", {"persona": "holly"}, "mia", "en") == "Holly here."
    )
    assert (
        BOOK.render("language.unknown", {"language": "de"}, "mia", "en")
        == "I can't speak de."
    )


@pytest.mark.parametrize(
    "package, problem",
    [
        ({"phrases": {"en": {"no.such.key": "Hi."}}}, "unknown key"),
        ({"phrases": {"en": {"warning.coolant_high": "Hot."}}}, "warning"),
        ({"phrases": {"de": {"intent.unknown": "Was?"}}}, "unknown language"),
        ({"phrases": {"en": {"message.arrived": "From {who}."}}}, "does not format"),
        ({"phrases": {"en": {"intent.unknown": ""}}}, "non-empty"),
        (
            {"warning_framing": {"en": {"warning.rpm_high": "Slow down. Now."}}},
            "one short sentence",
        ),
        ({"warning_framing": {"en": {"warning.fuel": "Fill up."}}}, "unknown warning"),
        ({"tts": {"length_scale": 5}}, "length_scale"),
        ({"tts": {"length_scale": True}}, "length_scale"),
        ([], "mapping"),
    ],
)
def test_a_package_that_could_change_a_warning_or_break_at_runtime_is_refused(
    package, problem
):
    with pytest.raises(PersonaError, match=problem):
        parse_persona("tester", package)


@pytest.mark.parametrize("name", ["mia", "Holly", "x", "../etc"])
def test_a_package_needs_its_own_lowercase_name(name):
    with pytest.raises(PersonaError):
        parse_persona(name, {})


def test_a_broken_package_is_left_out_and_the_rest_still_load(tmp_path):
    (tmp_path / "good.yaml").write_text(
        yaml.safe_dump({"phrases": {"en": {"intent.unknown": "Pardon?"}}})
    )
    (tmp_path / "bad.yaml").write_text("phrases: {en: {warning.rpm_high: 'Faster!'}}")
    (tmp_path / "garbled.yaml").write_text("phrases: [unclosed")
    assert sorted(load_personas(tmp_path)) == ["good"]


# ── Machine ───────────────────────────────────────────────────────────────


def test_switch_persona_names_one_or_takes_the_next_and_reports_settings():
    machine = _machine()
    out = machine.handle(SwitchPersona("rimmer"))
    assert machine.persona == "rimmer"
    assert machine.settings() in out
    assert any(isinstance(e, Speak) and e.phrase == "persona.set" for e in out)

    machine = _machine(persona="rimmer")
    machine.handle(SwitchPersona())
    assert machine.persona == "mia"  # wraps around


def test_an_unknown_persona_or_language_is_refused_aloud_and_changes_nothing():
    machine = _machine()
    out = machine.handle(SwitchPersona("kryten"))
    assert machine.persona == "mia"
    assert not any(isinstance(e, Settings) for e in out)
    assert [e.phrase for e in out if isinstance(e, Speak)] == ["persona.unknown"]

    machine = _machine()
    out = machine.handle(SetLanguage("de"))
    assert machine.language == "en"
    assert [e.phrase for e in out if isinstance(e, Speak)] == ["language.unknown"]


def test_set_language_reports_settings_and_a_busy_machine_stays_quiet():
    machine = _machine()
    machine.handle(Wake())
    assert machine.state is State.LISTENING
    out = machine.handle(SetLanguage("cs"))
    assert machine.language == "cs"
    assert Settings(Verbosity.NORMAL, "mia", BOOK.names, "cs", BOOK.languages) in out
    assert not any(isinstance(e, Speak) for e in out)


def test_a_stored_persona_this_pi_no_longer_has_falls_back_to_the_first():
    machine = _machine(persona="kryten", language="de")
    assert (machine.persona, machine.language) == ("mia", "en")


# ── Peers see sentences ───────────────────────────────────────────────────


def test_a_console_receives_the_words_in_the_persona_and_language_in_use():
    machine = _machine()
    router = EnvelopeRouter()
    router.register(Service.VOICE, VoiceService(machine, render=BOOK.render))
    inbox = []
    console = router.connect(inbox.append)

    def send(command, seq):
        console.handle(
            encode_envelope(
                Envelope(
                    Service.VOICE, "c", Op.DATA, Status.OK, seq, encode_command(command)
                )
            )
        )

    console.handle(encode_envelope(Envelope(Service.VOICE, "c", Op.OPEN, Status.OK, 1)))
    send(SwitchPersona("holly", Source.CONSOLE), 2)
    events = [
        decode_event(decode_envelope(m).payload)
        for m in inbox
        if decode_envelope(m).payload
    ]
    spoken = [e for e in events if isinstance(e, Speak)]
    assert spoken[-1].text == "Holly. Back on duty."
    assert events[0].personas == ("mia", "holly", "rimmer")  # the snapshot after Open


# ── Spoken commands ───────────────────────────────────────────────────────


def _bridge():
    machine = _machine()
    said, classified, saved = [], [], []

    def classify(text):
        classified.append(text)
        return ()

    bridge = RouterBridge(
        machine,
        classify=classify,
        execute=lambda part: "",
        publish_text=lambda text, utterance_id: said.append(text),
        on_settings=saved.append,
        phrasebook=BOOK,
    )
    return machine, bridge, said, classified, saved


def test_spoken_persona_and_language_commands_and_the_words_follow():
    machine, bridge, said, classified, saved = _bridge()
    bridge.on_transcript("switch to rimmer")
    assert machine.persona == "rimmer"
    assert said[-1] == "Rimmer here. Everybody remain calm. I am in charge."

    bridge.on_speaking(FINISHED)  # TTS reports the sentence done, as on the Pi
    bridge.on_transcript("Speak Czech.")
    assert machine.language == "cs"
    assert said[-1] == "Přecházím do češtiny. Spisovně, s tečkami."

    bridge.on_speaking(FINISHED)
    bridge.on_transcript("change persona")
    assert machine.persona == "mia"
    assert [s.persona for s in saved] == ["rimmer", "rimmer", "mia"]
    assert classified == []


@pytest.mark.parametrize(
    "sentence", ["switch to kryten", "tell rimmer I am late", "speak german", "persona"]
)
def test_anything_else_is_still_a_request(sentence):
    machine, bridge, said, classified, saved = _bridge()
    bridge.on_transcript(sentence)
    assert classified == [sentence] and saved == []


# ── Store ─────────────────────────────────────────────────────────────────


def test_the_store_keeps_persona_and_language(tmp_path):
    store = SettingsStore(tmp_path / FILE_NAME)
    store.save(Settings(Verbosity.CHATTY, "holly", BOOK.names, "cs", BOOK.languages))
    loaded = store.load()
    assert (loaded.verbosity, loaded.persona, loaded.language) == (
        Verbosity.CHATTY,
        "holly",
        "cs",
    )
    (tmp_path / FILE_NAME).write_text(json.dumps({"persona": "../../x", "language": 7}))
    loaded = store.load()
    assert (loaded.persona, loaded.language) == ("mia", "en")


# ── Speech ────────────────────────────────────────────────────────────────


VOICES = {"en": "en_US-amy-medium", "cs": "cs_CZ-jirka-medium"}


def test_tts_picks_the_model_for_the_language_from_its_own_list():
    assert tts_service.choose_voice(
        {"language": "cs", "length_scale": 1.1}, VOICES
    ) == (
        "cs",
        "cs_CZ-jirka-medium",
        1.1,
    )
    assert tts_service.choose_voice({}, VOICES) == ("en", "en_US-amy-medium", 1.0)


def test_a_message_cannot_choose_a_model_or_an_absurd_speed():
    language, model, scale = tts_service.choose_voice(
        {"language": "../../evil", "voice": "/tmp/evil", "length_scale": 50}, VOICES
    )
    assert (language, model, scale) == ("en", "en_US-amy-medium", 2.0)
    assert tts_service.choose_voice({"length_scale": True}, VOICES)[2] == 1.0
    assert tts_service.parse_voices("en=a, cs=b,broken,de=../x,fr=") == {
        "en": "a",
        "cs": "b",
    }
