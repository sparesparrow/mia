"""GET /features serves the requirements registry in spec/requirements."""

import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", "apps", "rpi-backend", "py-api"))

from fastapi.testclient import TestClient  # noqa: E402

from api import main as api_main  # noqa: E402
from services.voice_command_router import _format_features  # noqa: E402
import pytest

pytestmark = pytest.mark.req("REQ-NFR-004", "REQ-NET-002")

REGISTRY = Path(__file__).resolve().parents[3] / "spec" / "requirements"


def _registry():
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(REGISTRY.glob("*.yaml"))}


def test_every_registry_requirement_is_served():
    body = TestClient(api_main.app).get("/features").json()
    expected = {r["id"] for doc in _registry().values() for r in doc["requirements"]}
    served = {f["id"] for feats in body["categories"].values() for f in feats}
    assert served == expected
    assert body["total"] == len(expected)
    assert sum(body["summary"].values()) == len(expected)


def test_entries_carry_evidence_and_implementation():
    body = TestClient(api_main.app).get("/features").json()
    feature = body["categories"]["automotive"][0]
    assert {"id", "name", "state", "evidence", "description", "services", "files"} <= feature.keys()
    assert feature["state"] == feature["evidence"]


def test_category_and_state_filters():
    client = TestClient(api_main.app)
    body = client.get("/features", params={"category": "automotive", "state": "SIMULATION_TESTED"}).json()
    assert list(body["categories"]) == ["automotive"]
    assert {f["id"] for f in body["categories"]["automotive"]} == {"REQ-AUTO-011"}


@pytest.mark.req("REQ-VOICE-010")
def test_voice_router_reads_the_summary_aloud():
    text = _format_features({"total": 2, "summary": {"implemented_and_ci_tested": 1, "planned": 1}})
    assert text == "MIA has 2 features: 1 implemented and ci tested, 1 planned."
