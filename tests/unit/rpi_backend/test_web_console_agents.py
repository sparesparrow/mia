"""The web console's agent view and setup checklist (ADR-0029, REQ-WEB-007, REQ-WEB-008).

Shapes are the user's personas for the three fixed agent roles; handoffs are posted by agents and streamed to the
page. The setup checklist only looks at the Pi. No hardware, no server.
"""

import json

import pytest
from api import console_agents, console_setup
from api import main as api_main
from api.auth import api_key as api_key_module
from api.auth import dependencies as deps
from fastapi.testclient import TestClient

WRITE_KEY = "mia_api_agents_writer_0123456789a"
READ_KEY = "mia_api_agents_reader_0123456789a"
LOCAL = ("127.0.0.1", 50000)
LAN = ("192.168.200.20", 50000)


def _from(address):
    async def asgi(scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope = dict(scope, client=address)
        await api_main.app(scope, receive, send)

    return asgi


@pytest.fixture
def keys(monkeypatch):
    def _configure(*, write=None, read=None):
        for name in ("MIA_API_KEY", "MIA_API_KEYS", "MIA_AUTH_DISABLED"):
            monkeypatch.delenv(name, raising=False)
        if write:
            monkeypatch.setenv("MIA_API_KEY", write)
        deps._verified.clear()
        monkeypatch.setattr(deps, "_warned_open", True)
        monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
        if read:
            api_key_module.get_api_key_auth().add_key(read, "reader", scopes=["read"])

    yield _configure
    deps._verified.clear()
    api_key_module._api_key_auth = None


@pytest.fixture
def local(keys, monkeypatch, tmp_path):
    keys()
    monkeypatch.setenv("MIA_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("MIA_WEB_CONSOLE", raising=False)
    console_agents.clear()
    yield TestClient(_from(LOCAL), base_url="http://localhost:8000")
    console_agents.clear()


@pytest.fixture
def lines(monkeypatch):
    """The first ``n`` lines of the handoff stream; ``during(line)`` runs on the server after each line."""
    original = console_agents.handoff_lines

    def _read(client, n, headers=None, during=None):
        async def limited(request):
            source = original(request)
            count = 0
            try:
                async for line in source:
                    yield line
                    count += 1
                    if during is not None:
                        during(json.loads(line))
                    if count >= n:
                        break
            finally:
                await source.aclose()

        monkeypatch.setattr(console_agents, "handoff_lines", limited)
        response = client.get("/console/agents/events", headers=headers or {})
        monkeypatch.setattr(console_agents, "handoff_lines", original)
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/x-ndjson")
        return [json.loads(line) for line in response.text.splitlines() if line]

    return _read


def _shapes(**override):
    doc = json.loads(json.dumps(console_agents.DEFAULT_SHAPES))
    doc["shapes"]["dwarf"] = {
        "label": "Red Dwarf",
        "roles": {
            "orchestrator": {"persona": "Holly", "color": "#336699", "voice": "Norman"},
            "evaluator": {"persona": "Rimmer", "color": "#aa3333", "voice": ""},
            "executor": {"persona": "Kryten", "color": "#33aa55", "voice": "Robert"},
        },
    }
    doc["active"] = "dwarf"
    doc.update(override)
    return doc


# ── Shapes (REQ-WEB-007) ──────────────────────────────────────────────────


@pytest.mark.req("REQ-WEB-007")
def test_the_shipped_shape_plays_the_three_roles_until_the_user_stores_one(local):
    body = local.get("/console/agents/shapes").json()
    assert body["roles"] == ["orchestrator", "evaluator", "executor"]
    assert body["stored"] is False and body["active"] == "crew"
    assert body["shapes"]["crew"]["roles"]["orchestrator"]["persona"] == "The Feral Maestro"


@pytest.mark.req("REQ-WEB-007")
def test_a_user_defined_shape_is_stored_and_used(local, tmp_path):
    response = local.put("/console/agents/shapes", json=_shapes())
    assert response.status_code == 200, response.text
    stored = json.loads((tmp_path / "agent_shapes.json").read_text(encoding="utf-8"))
    assert stored["active"] == "dwarf" and stored["shapes"]["dwarf"]["roles"]["executor"]["persona"] == "Kryten"
    body = local.get("/console/agents/shapes").json()
    assert body["stored"] is True and body["active"] == "dwarf"


@pytest.mark.req("REQ-WEB-007")
@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(active="nobody"),
        lambda d: d["shapes"]["dwarf"]["roles"].pop("evaluator"),
        lambda d: d["shapes"]["dwarf"]["roles"].update(pilot={"persona": "Lister", "color": "#000000"}),
        lambda d: d["shapes"]["dwarf"]["roles"]["executor"].update(color="red"),
        lambda d: d["shapes"]["dwarf"]["roles"]["executor"].update(persona=""),
        lambda d: d["shapes"]["dwarf"]["roles"]["executor"].update(persona="K" * 41),
        lambda d: d["shapes"]["dwarf"]["roles"]["executor"].update(persona="Kry\x1bten"),
        lambda d: d["shapes"].update({"Bad Id": d["shapes"]["crew"]}),
        lambda d: d["shapes"].update({f"s{i}": d["shapes"]["crew"] for i in range(8)}),
        lambda d: d.update(shapes={}),
    ],
)
def test_a_shape_that_breaks_the_roles_is_refused_and_nothing_is_stored(local, tmp_path, mutate):
    doc = _shapes()
    mutate(doc)
    assert local.put("/console/agents/shapes", json=doc).status_code == 422
    assert not (tmp_path / "agent_shapes.json").exists()


@pytest.mark.req("REQ-WEB-007")
def test_a_damaged_shapes_file_falls_back_to_the_shipped_shape(local, tmp_path):
    (tmp_path / "agent_shapes.json").write_text("{not json", encoding="utf-8")
    assert local.get("/console/agents/shapes").json()["active"] == "crew"


# ── Handoffs (REQ-WEB-007) ────────────────────────────────────────────────


@pytest.mark.req("REQ-WEB-007")
def test_a_handoff_carries_the_personas_of_the_active_shape(local):
    local.put("/console/agents/shapes", json=_shapes())
    response = local.post(
        "/console/agents/events",
        json={"from_role": "orchestrator", "to_role": "executor", "task": "mia-car", "summary": "read the coolant"},
    )
    assert response.status_code == 200, response.text
    event = response.json()["event"]
    assert (event["from_persona"], event["to_persona"]) == ("Holly", "Kryten")
    assert (event["from_color"], event["to_color"]) == ("#336699", "#33aa55")
    assert event["shape"] == "dwarf" and event["seq"] == 1 and event["at"].endswith("+00:00")
    human = local.post("/console/agents/events", json={"from_role": "human", "to_role": "orchestrator"}).json()
    assert human["event"]["from_persona"] == "you"


@pytest.mark.req("REQ-WEB-007")
@pytest.mark.parametrize(
    "body",
    [
        {"from_role": "pilot", "to_role": "executor"},
        {"from_role": "executor", "to_role": "executor"},
        {"from_role": "orchestrator", "to_role": "executor", "summary": "x" * 281},
        {"from_role": "orchestrator", "to_role": "executor", "summary": "bell\x07"},
        {"from_role": "orchestrator", "to_role": "executor", "task": "t" * 81},
        {"to_role": "executor"},
    ],
)
def test_a_handoff_that_cannot_be_shown_is_refused(local, body):
    assert local.post("/console/agents/events", json=body).status_code == 422
    assert not list(console_agents.hub.recent)


@pytest.mark.req("REQ-WEB-007")
def test_the_stream_replays_recent_handoffs_then_shows_new_ones_and_shape_changes(local, lines):
    local.post("/console/agents/events", json={"from_role": "orchestrator", "to_role": "evaluator", "summary": "1"})
    posted = []

    def act(line):
        if line["type"] == "handoff" and not posted:
            posted.append(True)
            console_agents.hub.publish(
                console_agents.make_handoff(
                    console_agents.HandoffIn(from_role="evaluator", to_role="executor", summary="2")
                )
            )
            console_agents.hub.publish({"type": "shapes", **_shapes()}, remember=False)

    hello, old, new, shapes = lines(local, 4, during=act)
    assert hello["type"] == "hello" and hello["active"] == "crew" and "crew" in hello["shapes"]
    assert (old["summary"], new["summary"]) == ("1", "2")
    assert shapes["type"] == "shapes" and shapes["active"] == "dwarf"


@pytest.mark.req("REQ-WEB-007")
def test_the_backlog_is_bounded():
    hub = console_agents.HandoffHub(backlog=3)
    for i in range(5):
        hub.publish({"type": "handoff", "summary": str(i)})
    assert [e["summary"] for e in hub.recent] == ["2", "3", "4"]


@pytest.mark.req("REQ-WEB-007")
async def test_a_watcher_that_stops_reading_is_dropped_without_holding_up_the_others():
    hub = console_agents.HandoffHub()
    slow, fast = hub.watch(), hub.watch()
    for i in range(console_agents.SUBSCRIBER_LIMIT + 1):
        hub.publish({"type": "handoff", "summary": str(i)})
        while not fast.empty():
            fast.get_nowait()
    assert not hub.watching(slow) and hub.watching(fast)


@pytest.mark.req("REQ-WEB-007")
def test_posting_needs_the_write_scope_and_watching_the_read_scope(local, keys, lines):
    keys(write=WRITE_KEY, read=READ_KEY)
    lan = TestClient(_from(LAN), base_url="http://mia.local:8000")
    body = {"from_role": "orchestrator", "to_role": "executor"}
    assert lan.post("/console/agents/events", json=body).status_code == 401
    assert lan.post("/console/agents/events", json=body, headers={"X-API-Key": READ_KEY}).status_code == 403
    assert lan.post("/console/agents/events", json=body, headers={"X-API-Key": WRITE_KEY}).status_code == 200
    assert lan.put("/console/agents/shapes", json=_shapes(), headers={"X-API-Key": READ_KEY}).status_code == 403
    assert lan.get("/console/agents/events").status_code == 401
    hello, handoff = lines(lan, 2, {"X-API-Key": READ_KEY})
    assert (hello["type"], handoff["type"]) == ("hello", "handoff")


@pytest.mark.req("REQ-WEB-007")
def test_without_a_key_the_network_cannot_post_or_watch(local):
    lan = TestClient(_from(LAN), base_url="http://mia.local:8000")
    assert lan.post("/console/agents/events", json={"from_role": "human", "to_role": "orchestrator"}).status_code == 403
    assert lan.get("/console/agents/shapes").status_code == 403
    assert lan.get("/console/setup").status_code == 403


# ── Setup checklist (REQ-WEB-008) ─────────────────────────────────────────


def _steps(client):
    body = client.get("/console/setup").json()
    return body, {s["id"]: s for s in body["steps"]}


@pytest.mark.req("REQ-WEB-008")
def test_a_fresh_pi_shows_every_step_still_to_do(local, monkeypatch, tmp_path):
    for name in ("MIA_VEHICLE_VIN", "MIA_VEHICLE_MODEL", "VOICE_CONSOLE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MIA_PHONES_FILE", str(tmp_path / "missing.json"))
    body, steps = _steps(local)
    assert list(steps) == [
        "api_key",
        "vehicle",
        "phone",
        "voice_console",
        "voice_settings",
        "audio_settings",
        "agent_shapes",
    ]
    assert body["done"] == 0 and body["total"] == 7
    assert all(s["done"] is False and s["how"] for s in steps.values())
    assert {s["id"]: s.get("action") for s in steps.values() if s.get("action")} == {
        "voice_settings": "voice",
        "audio_settings": "audio",
        "agent_shapes": "agents",
    }


@pytest.mark.req("REQ-WEB-008")
def test_a_configured_pi_shows_every_step_done_without_revealing_a_value(local, keys, monkeypatch, tmp_path):
    keys(write=WRITE_KEY)
    vin = "WAUZZZ8H25K000123"
    monkeypatch.setenv("MIA_VEHICLE_VIN", vin)
    monkeypatch.setenv("MIA_VEHICLE_MODEL", "A4 Cabriolet 8H")
    monkeypatch.setenv("VOICE_CONSOLE", "1")
    phones = tmp_path / "phones.json"
    phones.write_text(json.dumps({"version": 1, "phones": {"SHA256:abc": {"mac": "", "bonded": False, "updated": 1}}}))
    monkeypatch.setenv("MIA_PHONES_FILE", str(phones))
    for name in ("voice_settings.json", "audio_settings.json", "agent_shapes.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    client = TestClient(_from(LOCAL), base_url="http://localhost:8000")
    response = client.get("/console/setup", headers={"X-API-Key": WRITE_KEY})
    assert response.status_code == 200
    steps = {s["id"]: s for s in response.json()["steps"]}
    assert all(s["done"] is True for s in steps.values()), steps
    assert steps["phone"]["detail"] == "1 phone enrolled"
    assert vin not in response.text and "A4 Cabriolet" not in response.text and "SHA256:abc" not in response.text
    assert WRITE_KEY not in response.text


@pytest.mark.req("REQ-WEB-008")
def test_an_invalid_vin_is_named_as_such(local, monkeypatch):
    monkeypatch.setenv("MIA_VEHICLE_VIN", "WAUZZZ8H25K00O123")  # an O, which a VIN never holds
    monkeypatch.setenv("MIA_VEHICLE_MODEL", "A4")
    vehicle = _steps(local)[1]["vehicle"]
    assert vehicle["done"] is False and "not a valid" in vehicle["detail"]


@pytest.mark.req("REQ-WEB-008")
def test_a_registry_the_api_cannot_read_is_unknown_not_missing(local, monkeypatch, tmp_path):
    phones = tmp_path / "phones.json"
    phones.write_text("{}")

    real_read_text = type(phones).read_text

    def denied(self, *args, **kwargs):
        if self == phones:
            raise PermissionError(13, "Permission denied")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(type(phones), "read_text", denied)
    monkeypatch.setenv("MIA_PHONES_FILE", str(phones))
    step = console_setup._phone()
    assert step["done"] is None and "root" in step["detail"]


@pytest.mark.req("REQ-WEB-008")
def test_the_checklist_changes_nothing(local, tmp_path, monkeypatch):
    monkeypatch.setenv("MIA_PHONES_FILE", str(tmp_path / "phones.json"))
    before = sorted(p.name for p in tmp_path.iterdir())
    _steps(local)
    _steps(local)
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert local.post("/console/setup").status_code == 405
