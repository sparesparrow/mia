"""The voice state machine: confirmation window, action classes, interrupts (ADR-0011, ADR-0012).

Pure logic with a fake clock: no audio, no network and no sleeping. The machine accepts typed commands
whatever their source, so these tests prove the machine, not a button or console adapter.
"""

import random
import re
from pathlib import Path

import pytest
from services import voice_command_router as router
from services.voice_fsm import (
    ACTION_CLASSES,
    BUSY_TONE,
    FEEDBACK,
    Abort,
    ActionClass,
    Cancel,
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
    SetVerbosity,
    Source,
    Speak,
    SpeakingDone,
    State,
    StopSpeaking,
    Verbosity,
    VoiceMachine,
    Wake,
    effective_class,
)

pytestmark = pytest.mark.req(
    "REQ-VOICE-011", "REQ-VOICE-012", "REQ-VOICE-013", "REQ-VOICE-014"
)

VOICE_MD = Path(__file__).resolve().parents[3] / "spec" / "interfaces" / "voice.md"


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


def dictate():
    return Part("note.dictate", ActionClass.NOTE)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def machine(clock):
    return VoiceMachine(clock)


def finish_speech(machine, effects):
    """Report every utterance in ``effects`` as finished, in order, and return what that produced."""
    out = []
    for speak in of(effects, Speak):
        out += machine.handle(SpeakingDone(speak.id))
    return out


def announce_and_finish(machine, parts, source=Source.VOICE):
    """Give the machine an intent, let MIA finish announcing and return everything that was emitted."""
    out = machine.handle(Intent(tuple(parts), source))
    return out + finish_speech(machine, out)


def execute_names(effects):
    return [p.name for e in of(effects, Execute) for p in e.parts]


# ── Wake, listening and the cue table ─────────────────────────────────────


def test_wake_starts_listening_and_silence_returns_to_idle(machine, clock):
    machine.handle(Wake())
    assert machine.state is State.LISTENING
    clock.advance(4.9)
    machine.tick()
    assert machine.state is State.LISTENING
    clock.advance(0.2)
    machine.tick()
    assert machine.state is State.IDLE


def test_every_state_and_cue_has_one_feedback_entry():
    assert set(FEEDBACK) == {s.value for s in State} | {c.value for c in CueName}


def test_the_window_and_the_confirmation_look_and_sound_different():
    window, confirming = FEEDBACK["window"], FEEDBACK["confirming"]
    assert window.led != confirming.led
    assert window.tone != confirming.tone


def test_the_state_table_in_the_interface_spec_matches_the_code():
    rows = {}
    for line in VOICE_MD.read_text(encoding="utf-8").splitlines():
        match = re.match(
            r"\|\s*`(\w+)`\s*\|[^|]*\|\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|", line
        )
        if match:
            rows[match.group(1)] = (match.group(2), match.group(3))
    assert rows == {name: (cue.led, cue.tone) for name, cue in FEEDBACK.items()}


def test_transient_cues_never_become_states(machine):
    out = machine.handle(Wake())
    out += machine.handle(Intent((comfort(certain=False),)))
    changed = [e.current.value for e in out if hasattr(e, "current")]
    assert "wake_caught" not in changed and "analysing" not in changed
    assert "wake_caught" in [e.state for e in of(out, Feedback)]


def test_commands_and_effects_are_hashable():
    assert hash(Part("lights.on", ActionClass.COMFORT, {"a": 1})) == hash(
        Part("lights.on", ActionClass.COMFORT, {"b": 2})
    )
    assert hash(Speak("x", {"k": 1}, 0, 1)) == hash(Speak("x", {"k": 2}, 0, 1))


# ── Confirmation window ───────────────────────────────────────────────────


def test_certain_parts_run_at_once(machine):
    machine.handle(Wake())
    out = machine.handle(Intent((read(), comfort())))
    (execute,) = of(out, Execute)
    assert [p.name for p in execute.parts] == ["read.voltage", "lights.on"]
    assert machine.state is State.EXECUTING
    out = machine.handle(
        ExecutionDone("read.result", {"value": 12.6}, execute.batch_id)
    )
    finish_speech(machine, out)
    assert machine.state is State.IDLE


def test_uncertain_part_runs_after_the_window(machine, clock):
    machine.handle(Wake())
    out = machine.handle(Intent((comfort(certain=False),)))
    assert phrases(out) == ["chain.announce"]
    assert of(out, Execute) == []

    finish_speech(machine, out)
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


def test_cancel_drops_the_pending_part_whatever_the_source(clock):
    for source in (Source.VOICE, Source.CONSOLE, Source.BUTTON):
        machine = VoiceMachine(clock)
        machine.handle(Wake())
        announce_and_finish(machine, [comfort(certain=False)])
        out = machine.handle(Cancel(source))
        assert machine.state is State.IDLE
        assert of(out, Execute) == []
        clock.advance(10)
        assert of(machine.tick(), Execute) == []


def test_go_now_shortens_the_window(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    out = machine.handle(GoNow(Source.BUTTON))
    assert execute_names(out) == ["lights.on"]


def test_go_now_during_the_announcement_runs_the_part_at_once(machine, clock):
    machine.handle(Wake())
    out = machine.handle(Intent((comfort(certain=False),)))
    assert machine.state is State.SPEAKING
    out = machine.handle(GoNow())
    assert execute_names(out) == ["lights.on"]
    assert of(out, StopSpeaking)
    assert of(out, MuteMic) == [MuteMic(False)]  # once, not twice
    assert machine.state is State.EXECUTING


def test_a_new_utterance_in_the_window_replaces_the_pending_part(machine, clock):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort("lights.on", certain=False)])
    out = machine.handle(Intent((comfort("lights.off", certain=True),)))
    assert execute_names(out) == ["lights.off"]
    clock.advance(10)
    assert of(machine.tick(), Execute) == []


def test_certain_parts_run_now_and_uncertain_parts_after_the_window(machine, clock):
    machine.handle(Wake())
    out = machine.handle(
        Intent(
            (comfort("lights.on", certain=True), read("read.coolant", certain=False))
        )
    )
    assert execute_names(out) == ["lights.on"]
    finish_speech(machine, out)
    assert machine.state is State.WINDOW
    clock.advance(5)
    assert execute_names(machine.tick()) == ["read.coolant"]


# ── A spoken result arriving while something is open ──────────────────────


def test_a_read_result_does_not_lose_the_open_window(machine, clock):
    machine.handle(Wake())
    out = machine.handle(
        Intent((read("read.voltage"), comfort("lights.on", certain=False)))
    )
    finish_speech(machine, out)
    assert machine.state is State.WINDOW

    result = machine.handle(ExecutionDone("read.result", {"value": 12.6}))
    assert phrases(result) == ["read.result"]
    assert machine.state is State.SPEAKING
    clock.advance(60)
    assert machine.tick() == []  # the window is paused while the result is spoken

    finish_speech(machine, result)
    assert machine.state is State.WINDOW
    clock.advance(5)
    assert execute_names(machine.tick()) == ["lights.on"]


def test_a_result_does_not_lose_a_pending_confirmation(machine):
    machine.handle(Wake())
    out = machine.handle(Intent((read("read.voltage"), sms())))
    finish_speech(machine, out)
    assert machine.state is State.CONFIRMING

    result = machine.handle(ExecutionDone("read.result"))
    finish_speech(machine, result)
    assert machine.state is State.CONFIRMING
    assert execute_names(machine.handle(Confirm())) == ["message.send"]


def test_a_result_arriving_during_dictation_is_held_and_the_microphone_stays_open(
    machine, clock
):
    machine.handle(Wake())
    out = machine.handle(
        Intent((read("read.voltage"), comfort("lights.on", certain=False)))
    )
    finish_speech(machine, out)
    # The driver changes their mind in the window and starts a note while the reading is still running.
    machine.handle(Intent((dictate(),)))
    assert machine.state is State.DICTATING

    result = machine.handle(ExecutionDone("read.result", {"value": 12.6}))
    assert (
        result == []
    )  # no speech, so the microphone is not muted while the driver talks
    machine.handle(DictationText("buy wipers"))
    out = machine.handle(EndDictation(Source.BUTTON))
    assert execute_names(out) == ["note.save"]
    assert phrases(out) == ["read.result"]
    assert of(out, Execute)[0].parts[0].args["text"] == "buy wipers"


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
    assert execute_names(machine.handle(Confirm(Source.VOICE))) == ["message.send"]


def test_the_go_now_button_counts_as_an_explicit_confirmation(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [sms()])
    assert execute_names(machine.handle(GoNow(Source.BUTTON))) == ["message.send"]


def test_go_now_during_the_question_skips_it_and_still_needs_a_second_press(machine):
    machine.handle(Wake())
    machine.handle(Intent((sms(),)))
    assert machine.state is State.SPEAKING
    out = machine.handle(GoNow())
    assert of(out, Execute) == []
    assert machine.state is State.CONFIRMING
    assert execute_names(machine.handle(GoNow())) == ["message.send"]


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
    assert execute_names(first) == ["message.send"]
    finish_speech(machine, machine.handle(ExecutionDone()))
    finish_speech(machine, first)
    assert machine.state is State.CONFIRMING
    assert execute_names(machine.handle(Confirm())) == ["call.place"]


def test_a_no_to_the_first_message_still_asks_about_the_second(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [sms("message.send"), sms("call.place")])
    out = machine.handle(Deny())
    assert phrases(out) == ["message.confirm"]
    finish_speech(machine, out)
    assert execute_names(machine.handle(Confirm())) == ["call.place"]


def test_a_no_in_the_window_cancels_it(machine, clock):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    machine.handle(Deny())
    clock.advance(10)
    assert of(machine.tick(), Execute) == []
    assert machine.state is State.IDLE


# ── The class table fails closed ──────────────────────────────────────────


def test_a_message_labelled_as_comfort_still_needs_confirmation(machine, clock):
    mislabelled = Part("message.send", ActionClass.COMFORT, {}, certain=False)
    machine.handle(Wake())
    out = announce_and_finish(machine, [mislabelled])
    assert "message.confirm" in phrases(out)
    clock.advance(60)
    assert of(machine.tick(), Execute) == []


def test_an_unknown_action_is_refused(machine, clock):
    machine.handle(Wake())
    out = machine.handle(
        Intent((Part("lights.strobe", ActionClass.READ, {}, certain=True),))
    )
    assert phrases(out) == ["chain.refused"]
    assert of(out, Execute) == []


def test_a_label_can_only_make_a_part_stricter():
    assert effective_class("lights.on", ActionClass.READ) is ActionClass.COMFORT
    assert effective_class("lights.on", ActionClass.MESSAGE) is ActionClass.MESSAGE
    assert effective_class("message.send", ActionClass.READ) is ActionClass.MESSAGE
    assert effective_class("dtc.clear", ActionClass.READ) is ActionClass.FORBIDDEN
    assert effective_class("nobody.knows", ActionClass.READ) is ActionClass.FORBIDDEN


def test_every_route_the_router_offers_is_in_the_class_table():
    labels = {label for label, _, _ in router.ROUTES}
    assert labels <= set(ACTION_CLASSES)
    assert all(
        ACTION_CLASSES[label] in (ActionClass.READ, ActionClass.COMFORT)
        for label in labels
    )


# ── Forbidden parts ───────────────────────────────────────────────────────


def test_a_write_to_a_control_unit_is_refused_and_the_rest_still_runs(machine, clock):
    forbidden = Part("dtc.clear", ActionClass.FORBIDDEN, {}, certain=False)
    machine.handle(Wake())
    out = machine.handle(Intent((read("dtc.read"), forbidden)))
    assert "chain.refused" in phrases(out)
    assert execute_names(out) == ["dtc.read"]
    clock.advance(60)
    assert "dtc.clear" not in execute_names(machine.tick())


def test_a_forbidden_part_with_a_harmless_label_is_still_refused(machine):
    machine.handle(Wake())
    out = machine.handle(
        Intent((Part("dpf.regenerate", ActionClass.READ, {}, certain=True),))
    )
    assert phrases(out) == ["chain.refused"]
    assert of(out, Execute) == []


def test_a_forbidden_part_alone_is_refused_and_nothing_is_queued(machine, clock):
    forbidden = Part("dpf.regenerate", ActionClass.FORBIDDEN, {}, certain=True)
    machine.handle(Wake())
    out = machine.handle(Intent((forbidden,)))
    assert phrases(out) == ["chain.refused"]
    finish_speech(machine, out)
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
    out = machine.handle(SafetyWarning("warning.coolant", {"value": 112}))
    assert machine.state is State.WARNING
    assert [e.priority for e in of(out, Speak)] == [1]
    clock.advance(60)
    assert machine.tick() == []  # the paused window does not run during the warning

    finish_speech(machine, out)
    assert machine.state is State.WINDOW
    clock.advance(4.9)
    assert of(machine.tick(), Execute) == []
    clock.advance(0.2)
    assert of(machine.tick(), Execute)


def test_cancel_during_a_warning_drops_the_paused_window_and_the_warning_keeps_playing(
    machine, clock
):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    warning = machine.handle(SafetyWarning("warning.coolant"))
    out = machine.handle(Cancel(Source.BUTTON))
    assert of(out, StopSpeaking) == []
    assert machine.state is State.WARNING

    finish_speech(machine, warning)
    assert machine.state is State.IDLE
    clock.advance(60)
    assert of(machine.tick(), Execute) == []


def test_a_warning_interrupts_dictation_and_keeps_the_text(machine):
    machine.handle(Wake())
    machine.handle(Intent((dictate(),)))
    assert machine.state is State.DICTATING
    machine.handle(DictationText("change the oil"))
    warning = machine.handle(SafetyWarning("warning.voltage", {}))
    assert machine.state is State.WARNING
    finish_speech(machine, warning)
    assert machine.state is State.DICTATING
    out = machine.handle(EndDictation(Source.BUTTON))
    (execute,) = of(out, Execute)
    assert execute.parts[0].args["text"] == "change the oil"


def test_a_warning_that_cuts_off_the_announcement_is_followed_by_a_repeat(
    machine, clock
):
    machine.handle(Wake())
    announcement = machine.handle(Intent((comfort(certain=False),)))
    (first,) = of(announcement, Speak)
    warning = machine.handle(SafetyWarning("warning.coolant"))
    assert of(warning, StopSpeaking)

    again = finish_speech(machine, warning)
    assert phrases(again) == ["chain.announce"]  # said again before any window starts
    assert machine.state is State.SPEAKING
    clock.advance(60)
    assert machine.tick() == []

    finish_speech(machine, again)
    assert machine.state is State.WINDOW
    assert first.id not in [s.id for s in of(again, Speak)]


def test_a_warning_that_cuts_off_the_question_cannot_be_followed_by_a_blind_confirmation(
    machine,
):
    machine.handle(Wake())
    machine.handle(Intent((sms(),)))
    warning = machine.handle(SafetyWarning("warning.coolant"))
    assert (
        of(machine.handle(GoNow()), Execute) == []
    )  # dismissing the warning confirms nothing
    assert machine.state is State.WARNING

    again = finish_speech(machine, warning)
    assert phrases(again) == ["message.confirm"]
    assert of(again, Execute) == []
    finish_speech(machine, again)
    assert machine.state is State.CONFIRMING
    assert execute_names(machine.handle(Confirm())) == ["message.send"]


def test_a_stale_done_from_a_stopped_utterance_does_not_unmute_the_microphone(machine):
    machine.handle(Wake())
    announcement = machine.handle(Intent((comfort(certain=False),)))
    (stopped,) = of(announcement, Speak)
    warning = machine.handle(SafetyWarning("warning.coolant"))
    (playing,) = of(warning, Speak)

    stale = machine.handle(SpeakingDone(stopped.id))
    assert stale == []
    assert machine.state is State.WARNING

    after = machine.handle(SpeakingDone(playing.id))
    assert (
        of(after, MuteMic) == []
    )  # the repeated announcement keeps the microphone muted
    assert machine.state is State.SPEAKING


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
    finish_speech(machine, out)
    assert machine.state is State.IDLE


def test_cancel_does_not_start_reading_a_queued_message(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    machine.handle(IncomingMessage("Petr", "I am late"))
    out = machine.handle(Cancel())
    assert phrases(out) == []
    assert machine.state is State.IDLE


def test_chatty_mode_reads_the_message_in_full(clock):
    chatty = VoiceMachine(clock, verbosity=Verbosity.CHATTY)
    (speak,) = of(chatty.handle(IncomingMessage("Petr", "I am late")), Speak)
    assert speak.phrase == "message.read"
    assert speak.params["text"] == "I am late"


def test_quiet_mode_drops_new_and_waiting_messages(clock):
    quiet = VoiceMachine(clock, verbosity=Verbosity.QUIET)
    assert quiet.handle(IncomingMessage("Petr", "I am late")) == []

    machine = VoiceMachine(clock)
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    machine.handle(IncomingMessage("Petr", "I am late"))
    machine.handle(SetVerbosity(Verbosity.QUIET))
    machine.handle(SetVerbosity(Verbosity.NORMAL))
    machine.handle(GoNow())
    out = machine.handle(ExecutionDone())
    assert phrases(out) == []


def test_only_the_newest_messages_are_kept(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [comfort(certain=False)])
    for n in range(25):
        machine.handle(IncomingMessage("Petr", f"message {n}"))
    assert len(machine._queue) == 20
    assert machine._queue[0].text == "message 5"


def test_verbosity_can_be_switched(machine):
    out = machine.handle(SetVerbosity(Verbosity.CHATTY, Source.BUTTON))
    assert machine.verbosity is Verbosity.CHATTY
    assert phrases(out) == ["verbosity.set"]


# ── Utterances that arrive while MIA is busy ──────────────────────────────


def test_an_utterance_while_executing_waits_its_turn(machine):
    machine.handle(Wake())
    first = machine.handle(Intent((read(),)))
    assert machine.state is State.EXECUTING
    assert machine.handle(Intent((comfort("lights.off"),))) == []

    out = machine.handle(ExecutionDone("", {}, of(first, Execute)[0].batch_id))
    assert execute_names(out) == ["lights.off"]


def test_a_correction_while_a_question_is_pending_replaces_it(machine):
    machine.handle(Wake())
    announce_and_finish(machine, [sms()])
    assert machine.state is State.CONFIRMING
    out = machine.handle(Intent((comfort("lights.on"),)))
    assert execute_names(out) == ["lights.on"]
    assert machine.handle(Confirm()) == []  # the old question is gone


def test_a_correction_during_the_announcement_replaces_the_pending_part(machine, clock):
    machine.handle(Wake())
    machine.handle(Intent((comfort("lights.on", certain=False),)))
    assert machine.state is State.SPEAKING
    out = machine.handle(Intent((comfort("lights.off"),)))
    assert execute_names(out) == ["lights.off"]
    assert of(out, MuteMic) == [MuteMic(False)]
    clock.advance(60)
    assert "lights.on" not in execute_names(machine.tick())


def test_an_utterance_during_dictation_gets_a_busy_cue(machine):
    machine.handle(Wake())
    machine.handle(Intent((dictate(),)))
    out = machine.handle(Intent((comfort(),)))
    (cue,) = of(out, Feedback)
    assert cue.state == "dictating" and cue.tone == BUSY_TONE
    assert of(out, Execute) == []


# ── Executor batches ──────────────────────────────────────────────────────


def test_cancel_while_executing_aborts_the_batch_and_ignores_its_result(machine):
    machine.handle(Wake())
    first = machine.handle(Intent((read(),)))
    (execute,) = of(first, Execute)
    out = machine.handle(Cancel())
    assert of(out, Abort) == [Abort(execute.batch_id)]
    late = machine.handle(ExecutionDone("read.result", {}, execute.batch_id))
    assert late == []
    assert machine.state is State.IDLE


def test_overlapping_batches_keep_the_machine_busy_until_both_are_done(machine, clock):
    machine.handle(Wake())
    out = machine.handle(
        Intent((read("read.voltage"), comfort("lights.on", certain=False)))
    )
    (first,) = of(out, Execute)
    finish_speech(machine, out)
    clock.advance(5)
    (second,) = of(machine.tick(), Execute)
    assert first.batch_id != second.batch_id
    assert machine.state is State.EXECUTING

    assert machine.handle(ExecutionDone("", {}, first.batch_id)) == []
    assert machine.state is State.EXECUTING
    machine.handle(ExecutionDone("", {}, second.batch_id))
    assert machine.state is State.IDLE


def test_a_result_for_an_unknown_batch_is_ignored(machine):
    machine.handle(Wake())
    machine.handle(Intent((read(),)))
    assert machine.handle(ExecutionDone("read.result", {}, 999)) == []
    assert machine.state is State.EXECUTING


# ── Microphone and dictation ──────────────────────────────────────────────


def test_the_microphone_is_muted_while_mia_speaks(machine):
    machine.handle(Wake())
    out = machine.handle(Intent((comfort(certain=False),)))
    assert of(out, MuteMic) == [MuteMic(True)]
    out = finish_speech(machine, out)
    assert of(out, MuteMic) == [MuteMic(False)]


def test_a_button_can_silence_speech_and_the_pending_chain(machine):
    machine.handle(Wake())
    machine.handle(Intent((comfort(certain=False),)))
    out = machine.handle(Cancel(Source.BUTTON))
    assert of(out, StopSpeaking)
    assert machine.state is State.IDLE


def test_dictation_is_saved_when_the_button_ends_it(machine):
    machine.handle(Wake())
    machine.handle(Intent((dictate(),)))
    machine.handle(DictationText("buy wipers"))
    machine.handle(DictationText("and washer fluid"))
    out = machine.handle(EndDictation(Source.BUTTON))
    (execute,) = of(out, Execute)
    assert execute.parts[0].name == "note.save"
    assert execute.parts[0].args["text"] == "buy wipers and washer fluid"


def test_an_empty_dictation_is_not_saved(machine):
    machine.handle(Wake())
    machine.handle(Intent((dictate(),)))
    out = machine.handle(EndDictation())
    assert of(out, Execute) == []
    assert phrases(out) == ["note.empty"]


def test_cancel_discards_the_dictation(machine):
    machine.handle(Wake())
    machine.handle(Intent((dictate(),)))
    machine.handle(DictationText("secret"))
    machine.handle(Cancel())
    assert machine.state is State.IDLE
    machine.handle(Wake())
    machine.handle(Intent((dictate(),)))
    assert of(machine.handle(EndDictation()), Execute) == []


def test_dictation_cannot_be_combined_with_other_parts(machine):
    machine.handle(Wake())
    for other in (sms(), comfort(certain=False)):
        out = machine.handle(Intent((dictate(), other)))
        assert phrases(out) == ["chain.dictation_alone"]
        assert of(out, Execute) == []
        finish_speech(machine, out)
        assert machine.state is State.IDLE


# ── Invariants under random orderings ─────────────────────────────────────

PART_POOL = [
    ("read.voltage", ActionClass.READ),
    ("lights.on", ActionClass.COMFORT),
    ("message.send", ActionClass.MESSAGE),
    ("message.send", ActionClass.COMFORT),  # mislabelled
    ("call.place", ActionClass.READ),  # mislabelled
    ("dtc.clear", ActionClass.FORBIDDEN),
    ("dpf.regenerate", ActionClass.READ),  # mislabelled
    ("made.up", ActionClass.READ),  # unknown
    ("note.dictate", ActionClass.NOTE),
]


def random_command(rng, machine):
    pick = rng.randrange(14)
    if pick == 0:
        return Wake()
    if pick == 1:
        parts = tuple(
            Part(*rng.choice(PART_POOL), {}, rng.random() < 0.5)
            for _ in range(rng.randrange(0, 4))
        )
        return Intent(parts)
    if pick == 2:
        return GoNow(rng.choice(list(Source)))
    if pick == 3:
        return Cancel(rng.choice(list(Source)))
    if pick == 4:
        return Confirm()
    if pick == 5:
        return Deny()
    if pick == 6:
        return EndDictation()
    if pick == 7:
        return DictationText("text")
    if pick == 8:
        return SafetyWarning("warning.coolant")
    if pick == 9:
        return IncomingMessage("Petr", "hello")
    if pick == 10:
        return SetVerbosity(rng.choice(list(Verbosity)))
    if pick == 11:
        ids = [s.id for s in machine._playing] + [None, rng.randrange(1, 50)]
        return SpeakingDone(rng.choice(ids))
    if pick == 12:
        ids = list(machine._inflight) + [None, rng.randrange(1, 50)]
        return ExecutionDone(rng.choice(["", "read.result"]), {}, rng.choice(ids))
    return None  # time passes


@pytest.mark.parametrize("seed", range(150))
def test_no_ordering_runs_a_message_without_a_yes_or_a_forbidden_part(seed):
    rng = random.Random(seed)
    clock = Clock()
    machine = VoiceMachine(clock)
    muted = False
    for _ in range(60):
        command = random_command(rng, machine)
        before = machine.state
        if command is None:
            clock.advance(rng.choice([0.5, 3, 6, 20]))
            effects = machine.tick()
        else:
            effects = machine.handle(command)

        for effect in of(effects, MuteMic):
            muted = effect.muted
        for execute in of(effects, Execute):
            for part in execute.parts:
                assert part.name in ACTION_CLASSES, part
                assert part.action_class is not ActionClass.FORBIDDEN, (seed, part)
                if part.action_class is ActionClass.MESSAGE:
                    assert (
                        isinstance(command, (Confirm, GoNow))
                        and before is State.CONFIRMING
                    ), (seed, part)
        if machine.state in (State.SPEAKING, State.WARNING):
            assert muted, (seed, machine.state)
