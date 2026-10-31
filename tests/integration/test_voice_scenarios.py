"""Voice scenarios from tests/fixtures/voice/scenarios, run through the simulated machine (REQ-VOICE-028).

Each YAML file is one scenario: a stimulus and the ordered events the pipeline must produce. They run against
two layers that exist in CI: the /ws/voice endpoint (``ws``) and the router, service and simulated speech
in-process on a fake clock (``machine``). The files with a ``pending`` reason are skipped until the typed-text
and audio paths exist; the same files then run on the real router and on the Pi.

Nothing here touches audio, a microphone or hardware.
"""

import pytest
from api import main as api_main
from api import voice_console
from fastapi.testclient import TestClient
from support.voice_rig import MachineRig, run_scenario, ws_rig
from support.voice_scenarios import load_all

pytestmark = [pytest.mark.integration, pytest.mark.req("REQ-VOICE-028")]

SCENARIOS = load_all()


def _cases(layer):
    return [
        pytest.param(
            s,
            id=s.name,
            marks=[pytest.mark.skip(reason=s.pending)] if s.pending else [],
        )
        for s in SCENARIOS
        if layer in s.layers and (layer == "machine" or not s.pending)
    ]


@pytest.fixture(scope="module")
def app_client():
    # One client for the module: starting the app (its lifespan) takes seconds.
    with TestClient(api_main.app) as client:
        yield client


@pytest.fixture
def client(app_client, monkeypatch, tmp_path):
    monkeypatch.setenv("VOICE_CONSOLE", "1")
    monkeypatch.setenv("MIA_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(voice_console, "_router", None)  # a fresh simulated machine per scenario
    return app_client


def test_the_scenario_set_covers_what_the_harness_claims():
    live = [s for s in SCENARIOS if not s.pending]
    pending = [s for s in SCENARIOS if s.pending]
    assert len(live) >= 6 and len(pending) >= 3
    assert all("REQ-VOICE-025" in s.pending or "REQ-VOICE-027" in s.pending for s in pending)
    assert {"ws", "machine"} <= {layer for s in live for layer in s.layers}


@pytest.mark.parametrize("scenario", _cases("ws"))
def test_scenario_through_the_console_endpoint(client, scenario):
    with ws_rig(client) as rig:
        run_scenario(rig, scenario)


@pytest.mark.parametrize("scenario", _cases("machine"))
def test_scenario_through_the_machine(scenario):
    run_scenario(MachineRig(), scenario)
