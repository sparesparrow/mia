"""Runs a scenario against a layer that exists in CI today (REQ-VOICE-028).

- ``ws``: the API's /ws/voice endpoint (a simulated machine in the mia-api process, real clock) through
  starlette's TestClient and the real FlatBuffers codec.
- ``machine``: the same router, service and simulated speech in this process on a fake clock, so a wait costs no
  time. Here an Intent may be sent (the service allows it), which is how a scenario gets into a confirmation or a
  dictation without a recogniser.

Both rigs feed one ``VoiceTrace``; ``run_scenario`` is the same for each.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any, Iterator, List

from support.voice_scenarios import Scenario
from support.voice_stimuli import press
from support.voice_trace import VoiceTrace

SESSION = "scenario"


def _intents() -> dict:
    from services.voice_fsm import ActionClass, Intent, Part

    return {
        # Message and call parts never run on silence: the machine asks, and waits for an explicit yes.
        "send_message": Intent((Part("message.send", ActionClass.MESSAGE, {"to": "Jana"}),)),
        # A part the splitter was not sure about: announced, then run when the window ends or on Go now.
        "uncertain_lights": Intent((Part("lights.on", ActionClass.COMFORT, certain=False),)),
        "dictate": Intent((Part("note.dictate", ActionClass.NOTE),)),
    }


def command_for(setting: dict) -> Any:
    from services.voice_fsm import SetLanguage, SetVerbosity, SwitchPersona, Verbosity

    if "verbosity" in setting:
        return SetVerbosity(Verbosity(setting["verbosity"]))
    if "persona" in setting:
        return SwitchPersona(setting["persona"])
    return SetLanguage(setting["language"])


def _envelope(command: Any, seq: int) -> bytes:
    from services.voice_fsm.wire import Envelope, Op, Service, Status, encode_command, encode_envelope

    return encode_envelope(Envelope(Service.VOICE, SESSION, Op.DATA, Status.OK, seq, encode_command(command)))


def _open_envelope() -> bytes:
    from services.voice_fsm.wire import Envelope, Op, Service, Status, encode_envelope

    return encode_envelope(Envelope(Service.VOICE, SESSION, Op.OPEN, Status.OK, 1))


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class MachineRig:
    """Router + service + simulated speech in-process on a fake clock."""

    layer = "machine"
    tick_sec = 0.1

    def __init__(self, tmp_dir: Any = None) -> None:
        from api import voice_console
        from services.voice_fsm import Intent, VoiceMachine
        from services.voice_fsm.personas import Phrasebook
        from services.voice_fsm.wire import PEER_COMMANDS, EnvelopeRouter, Service, VoiceService

        self.clock = FakeClock()
        self.trace = VoiceTrace(self.clock)
        book = Phrasebook.load()
        machine = VoiceMachine(self.clock, personas=book.names, languages=book.languages)
        service = VoiceService(machine, allowed=PEER_COMMANDS | {Intent}, render=book.render)
        self.router = EnvelopeRouter()
        self.router.register(Service.VOICE, voice_console.SimulatedSpeech(service, self.clock))
        self.connection = self.router.connect(self.trace.tap_sink())
        self._seq = 1
        self.connection.handle(_open_envelope())
        self.trace.clear()

    def send_command(self, command: Any) -> None:
        self._seq += 1
        self.connection.handle(_envelope(command, self._seq))

    def sleep(self, seconds: float) -> None:
        """What expect() calls while it waits: time passes, the router ticks."""
        steps = max(1, round(seconds / self.tick_sec))
        for _ in range(steps):
            self.clock.now += self.tick_sec
            self.router.tick()

    @property
    def wait_args(self) -> dict:
        return {"clock": self.clock, "sleep": self.sleep, "poll": self.tick_sec}


class WsRig:
    """A /ws/voice client from starlette's TestClient, read by a thread into the trace."""

    layer = "ws"

    def __init__(self, ws: Any) -> None:
        self._ws = ws
        self.trace = VoiceTrace()
        self._seq = 1
        ws.send_bytes(_open_envelope())
        # The Open reply and the settings snapshot: read here so the trace starts with the stimulus.
        for _ in range(2):
            ws.receive_bytes()
        self.tap = self.trace.tap_ws(ws)

    def send_command(self, command: Any) -> None:
        self._seq += 1
        self._ws.send_bytes(_envelope(command, self._seq))

    @property
    def wait_args(self) -> dict:
        return {"clock": time.monotonic, "sleep": time.sleep, "poll": 0.02}


@contextlib.contextmanager
def ws_rig(client: Any) -> Iterator[WsRig]:
    with client.websocket_connect("/ws/voice") as ws:
        rig = WsRig(ws)
        try:
            yield rig
        finally:
            pass  # leaving the websocket block closes the socket, which ends the reader thread
    rig.tap.stop()


def run_stimulus(rig: Any, scenario: Scenario, items: List[dict]) -> None:
    intents = _intents() if rig.layer == "machine" else {}
    for item in items:
        kind = item["kind"]
        if kind == "button":
            press(rig, item["button"])
        elif kind == "setting":
            rig.send_command(command_for(item))
        elif kind == "setup":
            if item["intent"] not in intents:
                raise AssertionError(f"intent {item['intent']!r} is not available in the {rig.layer} layer")
            rig.send_command(intents[item["intent"]])
        elif kind == "await":
            rig.trace.expect(item["steps"], scenario.timeout, **rig.wait_args)
        else:
            raise AssertionError(f"stimulus {kind!r} is not live in the {rig.layer} layer")


def run_scenario(rig: Any, scenario: Scenario) -> List[dict]:
    run_stimulus(rig, scenario, scenario.stimulus)
    return rig.trace.expect(scenario.expect, scenario.timeout, **rig.wait_args)
