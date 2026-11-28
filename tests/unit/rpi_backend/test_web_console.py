"""The Pi's web console: page, client gate, live voice stream and settings (ADR-0029, REQ-WEB-006).

No hardware and no server. The simulated backend runs in the API process; the router backend runs on real loopback
ZeroMQ sockets with a thread playing the router's loop, as in test_voice_router_host.py.
"""

import json
import re
import threading
import time
from pathlib import Path

import pytest
from api import main as api_main
from api import voice_console, voice_relay, web_console
from api.auth import api_key as api_key_module
from api.auth import dependencies as deps
from fastapi.testclient import TestClient
from services.voice_fsm import State, VoiceMachine, Wake
from services.voice_fsm.personas import Phrasebook
from services.voice_fsm.wire import (
    Envelope,
    EnvelopeRouter,
    Op,
    Service,
    Status,
    VoiceService,
    encode_command,
    encode_envelope,
    zmq_hub,
)
from starlette.requests import Request

pytestmark = pytest.mark.req("REQ-WEB-006")

READ_KEY = "mia_api_console_reader_0123456789"
WRITE_KEY = "mia_api_console_writer_0123456789"
LOCAL = ("127.0.0.1", 50000)
LAN = ("192.168.200.20", 50000)
PUBLIC = ("203.0.113.9", 50000)
PAGE_PATHS = ("/console/", "/console/console.js", "/console/console.css")


def _from(address):
    """The API as a client at ``address`` reaches it (TestClient of the CI Starlette cannot set the address)."""

    async def asgi(scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope = dict(scope, client=address)
        await api_main.app(scope, receive, send)

    return asgi


@pytest.fixture(scope="module")
def app_client():
    # One started app for the module (its lifespan takes seconds), as a browser on the Pi itself.
    with TestClient(_from(LOCAL), base_url="http://localhost:8000") as client:
        yield client


@pytest.fixture
def keys(monkeypatch):
    """Configure API keys (or none) for one test; ``keys()`` with no argument leaves the API open."""

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
def sim(app_client, keys, monkeypatch, tmp_path):
    keys()
    monkeypatch.setenv("VOICE_CONSOLE", "1")
    monkeypatch.delenv("VOICE_CONSOLE_BACKEND", raising=False)
    monkeypatch.delenv("MIA_WEB_CONSOLE", raising=False)
    monkeypatch.setenv("MIA_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(voice_console, "_router", None)
    return app_client


def _client(address, base_url="http://192.168.200.139:8000"):
    # No lifespan: the console routes need none of the app's sockets.
    return TestClient(_from(address), base_url=base_url)


@pytest.fixture
def lines(monkeypatch):
    """``lines(client, n)``: the first ``n`` JSON lines of the voice stream, keepalives left out.

    The stream never ends by itself, and the TestClient of the CI Starlette only returns a response that has
    ended, so the route's generator is wrapped to stop after ``n`` lines. ``during(line)`` runs on the server's
    event loop after each line, as something else happening on the Pi while the stream is open.
    """
    original = web_console.voice_event_lines

    def _read(client, n, headers=None, during=None):
        async def limited(request):
            source = original(request)
            count = 0
            try:
                async for line in source:
                    if json.loads(line)["type"] == "keepalive":
                        continue
                    yield line
                    count += 1
                    if during is not None:
                        during(json.loads(line))
                    if count >= n:
                        break
            finally:
                await source.aclose()

        monkeypatch.setattr(web_console, "voice_event_lines", limited)
        response = client.get("/console/voice/events", headers=headers or {})
        monkeypatch.setattr(web_console, "voice_event_lines", original)
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/x-ndjson")
        return [json.loads(line) for line in response.text.splitlines() if line]

    return _read


def _request(client_host, host_header="localhost:8000"):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/console/",
        "headers": [(b"host", host_header.encode())],
        "client": (client_host, 1234),
    }
    return Request(scope)


# ── The page ──────────────────────────────────────────────────────────────


def test_the_page_is_served_with_a_strict_policy(sim):
    for path in PAGE_PATHS:
        response = sim.get(path)
        assert response.status_code == 200, path
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp
        assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert sim.get("/console/").headers["content-type"].startswith("text/html")
    assert sim.get("/console/console.js").headers["content-type"].startswith("text/javascript")
    redirect = sim.get("/console", follow_redirects=False)
    assert (redirect.status_code, redirect.headers["location"]) == (307, "/console/")


def test_only_the_three_page_files_are_reachable(sim):
    for path in ("/console/../main.py", "/console/index.html", "/console/nothing.js"):
        assert sim.get(path).status_code in (401, 404), path


def test_the_page_works_under_its_policy_and_loads_nothing_from_elsewhere():
    html = (web_console.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), "inline script is blocked by the policy"
    assert "style=" not in html and "<style" not in html
    for name in ("index.html", "console.js", "console.css"):
        text = (web_console.STATIC_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"https?://", text), f"{name} must not load anything from another host"
    assert web_console.PUBLIC_PAGE_PATHS == deps.CONSOLE_PAGE_PATHS


def test_the_page_script_only_reads_the_car():
    """The safety rule of ADR-0029 as a check on the source: these are all the API paths the page names."""
    script = (web_console.STATIC_DIR / "console.js").read_text(encoding="utf-8")
    code = re.sub(r"^\s*//.*$", "", script, flags=re.M)
    paths = set(re.findall(r"""["'](/[a-z][a-z0-9/_-]*)["']""", code))
    assert paths == {
        "/auth/status",
        "/status",
        "/telemetry",
        "/audio/settings",
        "/console/voice/events",
        "/console/voice/settings",
    }
    for forbidden in ("/command", "/gpio", "/led", "/obd", "/ws", "/registry", "/ota", "/devices"):
        assert forbidden not in paths
    assert "innerHTML" not in code and "insertAdjacentHTML" not in code and "eval(" not in code


# ── Who may reach it ──────────────────────────────────────────────────────


def test_without_a_key_only_the_pi_itself_is_served(keys):
    keys()
    assert web_console.client_allowed(_request("127.0.0.1")) is None
    assert web_console.client_allowed(_request("::1", "[::1]:8000")) is None
    assert web_console.client_allowed(_request("::ffff:127.0.0.1")) is None
    # A DNS-rebinding page names another host in Host while it connects to loopback.
    assert "localhost" in web_console.client_allowed(_request("127.0.0.1", "evil.example:8000"))
    assert "MIA_API_KEY" in web_console.client_allowed(_request("192.168.200.20"))
    assert "MIA_API_KEY" in web_console.client_allowed(_request("fe80::1"))
    assert web_console.client_allowed(_request("203.0.113.9")) is not None
    assert web_console.client_allowed(_request("testclient")) is not None


def test_with_a_key_the_local_network_is_served_but_never_the_internet(keys):
    keys(write=WRITE_KEY)
    for host in ("127.0.0.1", "192.168.200.20", "10.0.0.7", "172.16.4.4", "169.254.1.1", "fd00::5"):
        assert web_console.client_allowed(_request(host, "mia.local:8000")) is None, host
    for host in ("203.0.113.9", "8.8.8.8", "2001:4860::8888"):
        assert web_console.client_allowed(_request(host, "mia.local:8000")) is not None, host


def test_the_network_cannot_open_the_console_while_no_key_is_set(sim):
    for path in PAGE_PATHS + ("/console/voice/events",):
        assert _client(LAN).get(path).status_code == 403, path
        assert _client(PUBLIC).get(path).status_code == 403, path
    assert _client(LAN).post("/console/voice/settings", json={"verbosity": "quiet"}).status_code == 403


def test_on_the_network_the_page_loads_and_its_data_needs_the_key(sim, keys, lines):
    keys(write=WRITE_KEY, read=READ_KEY)
    lan = _client(LAN)
    assert lan.get("/console/").status_code == 200  # static, no data
    assert lan.get("/console/voice/events").status_code == 401
    assert lan.get("/status").status_code == 401  # the API's own check, unchanged
    hello, settings = lines(lan, 2, {"X-API-Key": READ_KEY})
    assert hello["type"] == "hello" and settings["type"] == "settings"
    assert _client(PUBLIC).get("/console/voice/events", headers={"X-API-Key": READ_KEY}).status_code == 403


def test_changing_a_setting_needs_the_write_scope(sim, keys):
    keys(write=WRITE_KEY, read=READ_KEY)
    lan = _client(LAN)
    assert lan.post("/console/voice/settings", json={"verbosity": "quiet"}).status_code == 401
    refused = lan.post("/console/voice/settings", json={"verbosity": "quiet"}, headers={"X-API-Key": READ_KEY})
    assert refused.status_code == 403
    done = lan.post("/console/voice/settings", json={"verbosity": "quiet"}, headers={"X-API-Key": WRITE_KEY})
    assert done.status_code == 200 and done.json()["settings"]["verbosity"] == "quiet"


def test_the_console_can_be_switched_off(sim, monkeypatch):
    monkeypatch.setenv("MIA_WEB_CONSOLE", "0")
    for path in ("/console", "/console/", "/console/console.js", "/console/voice/events"):
        assert sim.get(path, follow_redirects=False).status_code == 404, path
    assert sim.post("/console/voice/settings", json={"verbosity": "quiet"}).status_code == 404


# ── The voice machine, simulated backend ──────────────────────────────────


def test_the_stream_starts_with_the_machines_settings(sim, lines):
    hello, settings = lines(sim, 2)
    assert hello == {"type": "hello", "backend": "sim", "session": hello["session"]}
    assert hello["session"].startswith("web-")
    book = Phrasebook.load()
    assert settings["type"] == "settings"
    assert settings["personas"] == list(book.names) and settings["languages"] == list(book.languages)
    assert settings["verbosity"] in ("quiet", "normal", "chatty")


def test_the_stream_shows_what_a_phone_console_does_and_sends_nothing_itself(sim, lines):
    phone = []

    def press_wake_once_settled(line):
        # After the snapshot, a phone console presses Wake: what /ws/voice does with the bytes it receives.
        if line["type"] != "settings" or phone:
            return
        router = voice_console.get_router()
        machine = router._services[Service.VOICE].service.machine
        phone.append(machine.state)  # opening the stream moved nothing
        connection = router.connect(lambda data: None)
        connection.handle(encode_envelope(Envelope(Service.VOICE, "phone", Op.OPEN, Status.OK, 1)))
        connection.handle(
            encode_envelope(Envelope(Service.VOICE, "phone", Op.DATA, Status.OK, 2, encode_command(Wake())))
        )

    seen = lines(sim, 4, during=press_wake_once_settled)
    assert [e["type"] for e in seen[:2]] == ["hello", "settings"]
    assert phone == [State.IDLE]
    state = next(e for e in seen if e["type"] == "state")
    assert (state["previous"], state["current"]) == ("idle", "listening")
    feedback = next(e for e in seen if e["type"] == "feedback")
    assert set(feedback) == {"type", "state", "led", "tone"}


def test_a_setting_changed_here_is_kept_and_seen_by_every_watcher(sim, tmp_path, lines):
    book = Phrasebook.load()
    persona = book.names[-1]
    language = book.languages[0]
    response = sim.post(
        "/console/voice/settings", json={"verbosity": "chatty", "persona": persona, "language": language}
    )
    assert response.status_code == 200, response.text
    settings = response.json()["settings"]
    assert (settings["verbosity"], settings["persona"], settings["language"]) == ("chatty", persona, language)
    stored = json.loads((Path(tmp_path) / "voice_settings.json").read_text(encoding="utf-8"))
    assert stored == {"verbosity": "chatty", "persona": persona, "language": language}
    assert lines(sim, 2)[1]["persona"] == persona


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"verbosity": "loud"},
        {"persona": "Holly"},
        {"persona": "holly; rm -rf /"},
        {"language": "../../etc"},
        {"language": "x" * 40},
    ],
)
def test_a_value_that_cannot_be_a_setting_is_refused(sim, body):
    assert sim.post("/console/voice/settings", json=body).status_code == 422


def test_with_the_voice_console_off_the_stream_says_so(sim, monkeypatch, lines):
    monkeypatch.delenv("VOICE_CONSOLE", raising=False)
    (line,) = lines(sim, 3)
    assert line["type"] == "unavailable" and "VOICE_CONSOLE" in line["reason"]
    assert sim.post("/console/voice/settings", json={"verbosity": "quiet"}).status_code == 503


def test_event_json_covers_every_event_the_wire_carries():
    from services.voice_fsm import Feedback, Settings, Speak, StateChanged, Verbosity
    from services.voice_fsm.wire import Transcript

    assert web_console.event_json(StateChanged(State.IDLE, State.LISTENING)) == {
        "type": "state",
        "previous": "idle",
        "current": "listening",
    }
    assert web_console.event_json(Feedback("listening", "blue", "wake"))["type"] == "feedback"
    speak = web_console.event_json(Speak("status.ok", {"n": 2}, 0, 7, "All good."))
    assert speak == {
        "type": "speak",
        "phrase": "status.ok",
        "params": {"n": 2},
        "priority": 0,
        "id": 7,
        "text": "All good.",
    }
    assert web_console.event_json(Transcript("hello", 3)) == {"type": "transcript", "text": "hello", "utterance_id": 3}
    settings = web_console.event_json(Settings(Verbosity.QUIET))
    assert settings["type"] == "settings" and settings["verbosity"] == "quiet"


# ── The voice machine, router backend over ZeroMQ ─────────────────────────


class RouterThread(threading.Thread):
    """The router's loop with a plain voice service behind the hub."""

    def __init__(self, zmq, ctx, machine):
        super().__init__(daemon=True)
        self.zmq = zmq
        envelope_router = EnvelopeRouter()
        envelope_router.register(Service.VOICE, VoiceService(machine))
        self.hub = zmq_hub.ZmqHub(envelope_router, ctx, port=0)
        self.stop = threading.Event()

    def run(self):
        poller = self.zmq.Poller()
        poller.register(self.hub.socket, self.zmq.POLLIN)
        while not self.stop.is_set():
            if self.hub.socket in dict(poller.poll(20)):
                self.hub.service()
            self.hub.reap()
            self.hub.flush()
        self.hub.close()


@pytest.fixture
def routed(sim, real_zmq, monkeypatch):
    zmq, zmq_asyncio = real_zmq
    monkeypatch.setattr(zmq_hub, "zmq", zmq)
    monkeypatch.setattr(voice_relay, "zmq", zmq)
    monkeypatch.setattr(voice_relay, "zmq_asyncio", zmq_asyncio)
    ctx = zmq.Context()
    machine = VoiceMachine(time.monotonic, personas=("mia", "holly"), languages=("cs", "en"))
    thread = RouterThread(zmq, ctx, machine)
    thread.start()
    monkeypatch.setenv("VOICE_CONSOLE_BACKEND", "router")
    monkeypatch.setenv("VOICE_CONSOLE_ENDPOINT", f"tcp://127.0.0.1:{thread.hub.port}")
    yield sim, thread, machine, zmq, ctx
    thread.stop.set()
    thread.join(5)
    ctx.term()


def test_the_stream_watches_the_routers_machine(routed, lines):
    client, thread, machine, _, _ = routed
    hello, settings = lines(client, 2)
    assert hello["backend"] == "router"
    assert settings["personas"] == ["mia", "holly"]
    deadline = time.monotonic() + 3
    while thread.hub.peers and time.monotonic() < deadline:
        time.sleep(0.02)
    assert thread.hub.peers == 0  # the stream said goodbye with the empty frame
    assert machine.state is State.IDLE


def test_a_setting_reaches_the_routers_machine(routed):
    client, _, machine, _, _ = routed
    response = client.post("/console/voice/settings", json={"persona": "holly", "language": "cs"})
    assert response.status_code == 200, response.text
    assert (machine.persona, machine.language) == ("holly", "cs")
    assert response.json()["settings"]["persona"] == "holly"


def test_a_dead_router_ends_the_stream_and_refuses_a_change(sim, real_zmq, monkeypatch, lines):
    zmq, zmq_asyncio = real_zmq
    monkeypatch.setattr(voice_relay, "zmq", zmq)
    monkeypatch.setattr(voice_relay, "zmq_asyncio", zmq_asyncio)
    ctx = zmq.Context()
    probe = ctx.socket(zmq.ROUTER)
    port = probe.bind_to_random_port("tcp://127.0.0.1")
    probe.close(0)
    ctx.term()

    class JumpingClock:
        now = 0.0

        def __call__(self):
            self.now += 1.0
            return self.now

    monkeypatch.setenv("VOICE_CONSOLE_BACKEND", "router")
    monkeypatch.setenv("VOICE_CONSOLE_ENDPOINT", f"tcp://127.0.0.1:{port}")
    monkeypatch.setattr(voice_relay, "_clock", JumpingClock())
    monkeypatch.setattr(voice_relay, "WATCH_SEC", 0.01)
    hello, gone = lines(sim, 3)
    assert hello["backend"] == "router"
    assert gone == {"type": "unavailable", "reason": voice_relay.OFFLINE_REASON}
    assert sim.post("/console/voice/settings", json={"verbosity": "quiet"}).status_code == 503
