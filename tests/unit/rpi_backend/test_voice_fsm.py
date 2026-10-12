"""The voice state machine: confirmation window, action classes, interrupts (ADR-0011, ADR-0012).

Pure logic with a fake clock: no audio, no network and no sleeping.
"""

import pytest
from services.voice_fsm import (
    FEEDBACK,
    ActionClass,
    Cancel,
    Confirm,
    Deny,
    DictationText,
    EndDictation,
    Execute,
    ExecutionDone,
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
    StopSpeaking,
    Verbosity,
    VoiceMachine,
    Wake,
    Warning,
)

pytestmark = pytest.mark.req(
    "REQ-VOICE-011", "REQ-VOICE-012", "REQ-VOICE-013", "REQ-VOICE-014"
)


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def of(effects, kind):
    return [e for e in effects if isinstance(e, kind)]


def phrases(effects):
    return [e.phrase for e in of(effects, Speak)]


def read(name="read.voltage", certain=True):
    return Part(name, ActionClass.READ, {}, certain)


def comfort(name="lights.on", certain=True):
    return Part(name, ActionClass.COMFORT, {}, certain)


def sms(name="message.send"):
    return Part(name, ActionClass.MESSAGE, {"to": "Petr"}, certain=False)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def machine(clock):
    return VoiceMachine(clock)


def announce_and_finish(machine, parts, source=Source.VOICE):
    """Give the machine an intent, let MIA finish announcing and return to the quiet state."""
    out = machine.handle(Intent(tuple(parts), source))
    out += machine.handle(SpeakingDone())
    return out


# ── Wake and listening ────────────────────────────────────────────────────


def test_wake_starts_listening_and_silence_returns_to_idle(machine, clock):
    machine.handle(Wake())
    assert machine.state is State.LISTENING
    clock.advance(4.9)
    machine.tick()
    assert machine.state is State.LISTENING
    clock.advance(0.2)
    machine.tick()
    assert machine.state is State.IDLE


def test_every_state_has_a_feedback_cue():
    assert set(FEEDBACK) == set(State)


# ── Confirmation window ───────────────────────────────────────────────────


def test_certain_parts_run_at_once(machine):
    machine.handle(Wake())
    out = machine.handle(Intent((read(), comfort())))
    (execute,) = of(out, Execute)
    assert [p.name for p in execute.parts] == ["read.voltage", "lights.on"]
    assert machine.state is State.EXECUTING
    machine.handle(ExecutionDone("read.result", {"value": 12.6}))
    machine.handle(SpeakingDone())
    assert machine.state is State.IDLE


def test_uncertain_part_runs_after_the_window(machine, clock):
    machine.handle(Wake())
    out = machine.handle(Intent((comfort(certain=False),)))
    assert phrases(out) == ["chain.announce"]
    assert of(out, Execute) == []

    machine.handle(SpeakingDone())
    assert machine.state is State.WINDOW
    clock.advance(4.9)
    assert of(machine.tick(), Execute) == []
    clock.advance(0.2)
    (execute,) = of(machine.tick(), Execute)
    assert [p.name for p in execute.parts] == ["lights.on"]


def test_window_does_not_start_while_mia_is_still_speaking(machine, clock):
    machine.handle(Wake())
    machine.handle(Intent((comfort(certain=False),)))
    clock.advance(30)
    assert machine.tick() == []
    assert machine.state is State.SPEAKING


def test_cancel_by_button_drops_the_pending_part(machine, clock):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    out = machine.handle(Cancel(Source.BUTTON))
    assert machine.state is State.IDLE
    assert of(out, Execute) == []
    clock.advance(10)
    assert of(machine.tick(), Execute) == []


def test_cancel_by_voice_and_by_console_do_the_same(clock):
    for source in (Source.VOICE, Source.CONSOLE, Source.BUTTON):
        machine = VoiceMachine(clock)
        machine.handle(Wake())
        announce_and_finish(machine, [comfort(certain=False)])
        machine.handle(Cancel(source))
        assert machine.state is State.IDLE


def test_go_now_shortens_the_window(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    out = machine.handle(GoNow(Source.BUTTON))
    assert [p.name for p in of(out, Execute)[0].parts] == ["lights.on"]


def test_a_new_utterance_in_the_window_replaces_the_pending_part(machine, clock):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort("lights.on", certain=False)])
    out = machine.handle(Intent((comfort("lights.off", certain=True),)))
    (execute,) = of(out, Execute)
    assert [p.name for p in execute.parts] == ["lights.off"]
    clock.advance(10)
    assert of(machine.tick(), Execute) == []


def test_certain_parts_run_now_and_uncertain_parts_after_the_window(machine, clock):
    machine.handle(Wake())
    out = machine.handle(
        Intent(
            (comfort("lights.on", certain=True), read("read.coolant", certain=False))
        )
    )
    (now,) = of(out, Execute)
    assert [p.name for p in now.parts] == ["lights.on"]
    machine.handle(ExecutionDone())
    machine.handle(SpeakingDone())
    assert machine.state is State.WINDOW
    clock.advance(5)
    (later,) = of(machine.tick(), Execute)
    assert [p.name for p in later.parts] == ["read.coolant"]


# ── Messages and calls ────────────────────────────────────────────────────


def test_a_message_never_runs_on_silence(machine, clock):
    machine.handle(Wake())
    out = announce_and_finish(machine, [sms()])
    assert "message.confirm" in phrases(out)
    assert machine.state is State.CONFIRMING
    clock.advance(60)
    out = machine.tick()
    assert of(out, Execute) == []
    assert phrases(out) == ["confirm.timeout"]


def test_a_message_runs_after_an_explicit_yes(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [sms()])
    out = machine.handle(Confirm(Source.VOICE))
    (execute,) = of(out, Execute)
    assert [p.name for p in execute.parts] == ["message.send"]


def test_the_go_now_button_counts_as_an_explicit_confirmation(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [sms()])
    assert of(machine.handle(GoNow(Source.BUTTON)), Execute)


def test_a_no_cancels_the_message(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [sms()])
    out = machine.handle(Deny())
    assert of(out, Execute) == []
    assert machine.state is State.IDLE


def test_two_messages_are_confirmed_one_at_a_time(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [sms("message.send"), sms("call.place")])
    first = machine.handle(Confirm())
    assert [p.name for p in of(first, Execute)[0].parts] == ["message.send"]
    machine.handle(ExecutionDone())
    machine.handle(SpeakingDone())
    assert machine.state is State.CONFIRMING
    second = machine.handle(Confirm())
    assert [p.name for p in of(second, Execute)[0].parts] == ["call.place"]


# ── Forbidden parts ───────────────────────────────────────────────────────


def test_a_write_to_a_control_unit_is_refused_and_the_rest_still_runs(machine, clock):
    forbidden = Part("dtc.clear", ActionClass.FORBIDDEN, {}, certain=False)
    machine.handle(Wake())
    out = machine.handle(Intent((read("dtc.read"), forbidden)))
    assert "chain.refused" in phrases(out)
    (execute,) = of(out, Execute)
    assert [p.name for p in execute.parts] == ["dtc.read"]
    clock.advance(60)
    assert all(
        "dtc.clear" not in [p.name for p in e.parts]
        for e in of(machine.tick(), Execute)
    )


def test_a_forbidden_part_alone_is_refused_and_nothing_is_queued(machine, clock):
    forbidden = Part("dpf.regenerate", ActionClass.FORBIDDEN, {}, certain=True)
    machine.handle(Wake())
    out = machine.handle(Intent((forbidden,)))
    assert phrases(out) == ["chain.refused"]
    machine.handle(SpeakingDone())
    assert machine.state is State.IDLE
    clock.advance(60)
    assert machine.tick() == []


# ── Interrupts ────────────────────────────────────────────────────────────


def test_a_warning_interrupts_the_window_and_the_window_restarts_afterwards(
    machine, clock
):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    clock.advance(3)
    out = machine.handle(Warning("warning.coolant", {"value": 112}))
    assert machine.state is State.WARNING
    assert [e.priority for e in of(out, Speak)] == [1]
    clock.advance(60)
    assert machine.tick() == []  # the paused window does not run during the warning

    machine.handle(SpeakingDone())
    assert machine.state is State.WINDOW
    clock.advance(4.9)
    assert of(machine.tick(), Execute) == []
    clock.advance(0.2)
    assert of(machine.tick(), Execute)


def test_a_warning_interrupts_dictation_and_keeps_the_text(machine):
    machine.handle(Wake())
    machine.handle(Intent((Part("note.dictate", ActionClass.NOTE),)))
    assert machine.state is State.DICTATING
    machine.handle(DictationText("change the oil"))
    machine.handle(Warning("warning.voltage", {}))
    assert machine.state is State.WARNING
    machine.handle(SpeakingDone())
    assert machine.state is State.DICTATING
    out = machine.handle(EndDictation(Source.BUTTON))
    (execute,) = of(out, Execute)
    assert execute.parts[0].args["text"] == "change the oil"


def test_a_warning_interrupts_speech_and_the_announcement_still_leads_to_the_window(
    machine,
):
    machine.handle(Wake())
    machine.handle(Intent((comfort(certain=False),)))
    out = machine.handle(Warning("warning.coolant"))
    assert of(out, StopSpeaking)
    machine.handle(SpeakingDone())
    assert machine.state is State.WINDOW


def test_a_message_waits_while_the_window_is_open_and_is_announced_afterwards(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    assert machine.handle(IncomingMessage("Petr", "I am late")) == []
    assert machine.state is State.WINDOW

    machine.handle(GoNow())
    assert machine.state is State.EXECUTING
    out = machine.handle(ExecutionDone())
    assert phrases(out) == ["message.arrived"]
    assert machine.state is State.SPEAKING


def test_a_queued_message_is_announced_once_idle(machine):
    machine.handle(Wake())
    machine.handle(Intent((read(),)))
    machine.handle(IncomingMessage("Petr", "I am late"))
    out = machine.handle(ExecutionDone())
    assert phrases(out) == ["message.arrived"]
    assert machine.state is State.SPEAKING
    machine.handle(SpeakingDone())
    assert machine.state is State.IDLE


def test_chatty_mode_reads_the_message_in_full_and_quiet_mode_drops_it(clock):
    chatty = VoiceMachine(clock, verbosity=Verbosity.CHATTY)
    out = chatty.handle(IncomingMessage("Petr", "I am late"))
    (speak,) = of(out, Speak)
    assert speak.phrase == "message.read"
    assert speak.params["text"] == "I am late"

    quiet = VoiceMachine(clock, verbosity=Verbosity.QUIET)
    assert quiet.handle(IncomingMessage("Petr", "I am late")) == []


def test_verbosity_can_be_switched(machine):
    out = machine.handle(SetVerbosity(Verbosity.CHATTY, Source.BUTTON))
    assert machine.verbosity is Verbosity.CHATTY
    assert phrases(out) == ["verbosity.set"]


# ── Microphone and dictation ──────────────────────────────────────────────


def test_the_microphone_is_muted_while_mia_speaks(machine):
    machine.handle(Wake())
    out = machine.handle(Intent((comfort(certain=False),)))
    assert of(out, MuteMic) == [MuteMic(True)]
    out = machine.handle(SpeakingDone())
    assert of(out, MuteMic) == [MuteMic(False)]


def test_a_button_can_silence_speech_and_the_pending_chain(machine):
    machine.handle(Wake())
    machine.handle(Intent((comfort(certain=False),)))
    out = machine.handle(Cancel(Source.BUTTON))
    assert of(out, StopSpeaking)
    assert machine.state is State.IDLE


def test_dictation_is_saved_when_the_button_ends_it(machine):
    machine.handle(Wake())
    machine.handle(Intent((Part("note.dictate", ActionClass.NOTE),)))
    machine.handle(DictationText("buy wipers"))
    machine.handle(DictationText("and washer fluid"))
    out = machine.handle(EndDictation(Source.BUTTON))
    (execute,) = of(out, Execute)
    assert execute.parts[0].name == "note.save"
    assert execute.parts[0].args["text"] == "buy wipers and washer fluid"


def test_an_empty_dictation_is_not_saved(machine):
    machine.handle(Wake())
    machine.handle(Intent((Part("note.dictate", ActionClass.NOTE),)))
    out = machine.handle(EndDictation())
    assert of(out, Execute) == []
    assert phrases(out) == ["note.empty"]


def test_cancel_discards_the_dictation(machine):
    machine.handle(Wake())
    machine.handle(Intent((Part("note.dictate", ActionClass.NOTE),)))
    machine.handle(DictationText("secret"))
    machine.handle(Cancel())
    assert machine.state is State.IDLE
    machine.handle(Wake())
    machine.handle(Intent((Part("note.dictate", ActionClass.NOTE),)))
    assert of(machine.handle(EndDictation()), Execute) == []
