"""App-wide API authentication, WebSocket authentication and the CORS allow-list."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", "apps", "rpi-backend", "py-api"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from api import main as api_main  # noqa: E402
from api.auth import api_key as api_key_module  # noqa: E402
from api.auth import dependencies as deps  # noqa: E402

pytestmark = pytest.mark.req("REQ-SEC-001")

class _OneTickAsyncio:
    """Stand-in for api.main's asyncio: the second sleep ends the 10 Hz send loop."""

    def __init__(self):
        self._ticks = 0

    def __getattr__(self, name):
        return getattr(asyncio, name)

    async def sleep(self, delay):
        self._ticks += 1
        if self._ticks > 1:
            raise WebSocketDisconnect()


def _websocket_paths():
    return sorted(r.path for r in api_main.app.routes if type(r).__name__ in ("APIWebSocketRoute", "WebSocketRoute"))


READ_KEY = "mia_api_readonly_0123456789abcdef"
WRITE_KEY = "mia_api_readwrite_0123456789abcd"


@pytest.fixture
def configure_auth(monkeypatch):
    """Build a fresh key store from the environment and drop the verification cache."""

    def _configure(**env):
        for name in ("MIA_API_KEY", "MIA_API_KEYS", "MIA_AUTH_DISABLED"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        deps._verified.clear()
        monkeypatch.setattr(deps, "_warned_open", False)
        monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
        return TestClient(api_main.app)

    yield _configure
    deps._verified.clear()
    api_key_module._api_key_auth = None


def test_open_with_a_warning_when_no_key_is_configured(configure_auth, caplog):
    client = configure_auth()
    with caplog.at_level("WARNING"):
        assert client.get("/features").status_code == 200
    assert "NOT enforced" in caplog.text


def test_disabled_flag_keeps_the_api_open(configure_auth):
    client = configure_auth(MIA_AUTH_DISABLED="1")
    assert client.get("/features").status_code == 200


def test_every_route_needs_a_key_once_one_is_configured(configure_auth):
    client = configure_auth(MIA_API_KEYS=WRITE_KEY)
    assert client.get("/features").status_code == 401
    assert client.get("/features", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/features", headers={"X-API-Key": WRITE_KEY}).status_code == 200
    for method, path in [("get", "/telemetry"), ("post", "/command"), ("post", "/gpio/set"), ("put", "/led/state")]:
        assert getattr(client, method)(path).status_code == 401, (method, path)


def test_routes_from_included_routers_are_covered(configure_auth):
    client = configure_auth(MIA_API_KEY=WRITE_KEY)
    router_paths = {
        r.path for r in api_main.app.routes
        if r.path.startswith(("/ota", "/logs", "/anpr")) and "GET" in getattr(r, "methods", ())
    }
    assert router_paths, "expected the ota/logs/anpr routers to be mounted"
    for path in sorted(p for p in router_paths if "{" not in p):
        assert client.get(path).status_code in (401, 405), path


def test_health_and_docs_stay_public(configure_auth):
    client = configure_auth(MIA_API_KEY=WRITE_KEY)
    for path in ("/", "/auth/status", "/openapi.json"):
        assert client.get(path).status_code == 200, path


def test_mutations_need_the_write_scope(configure_auth):
    client = configure_auth(MIA_API_KEY=WRITE_KEY)
    api_key_module.get_api_key_auth().add_key(READ_KEY, "reader", scopes=["read"])
    headers = {"X-API-Key": READ_KEY}
    assert client.get("/features", headers=headers).status_code == 200
    assert client.post("/command", headers=headers, json={}).status_code == 403
    assert client.delete("/registry/devices/x", headers=headers).status_code == 403


def test_a_verified_key_is_cached(configure_auth, monkeypatch):
    client = configure_auth(MIA_API_KEY=WRITE_KEY)
    calls = []
    real_verify = api_key_module.APIKeyAuth.verify

    def counting(self, key):
        calls.append(key)
        return real_verify(self, key)

    monkeypatch.setattr(api_key_module.APIKeyAuth, "verify", counting)
    for _ in range(3):
        assert client.get("/features", headers={"X-API-Key": WRITE_KEY}).status_code == 200
    assert len(calls) == 1


def test_every_websocket_route_is_known():
    # Guards the parametrised tests below: a new WebSocket route must be authenticated too.
    assert _websocket_paths() == ["/anpr/stream", "/ws", "/ws/telemetry"]


@pytest.mark.parametrize("path", _websocket_paths())
def test_websockets_reject_missing_and_bad_keys(configure_auth, path):
    client = configure_auth(MIA_API_KEY=WRITE_KEY)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(path):
            pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(path, headers={"X-API-Key": "wrong"}):
            pass
    # A key in the query string must not authenticate a socket (it leaks into logs).
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{path}?api_key={WRITE_KEY}"):
            pass


@pytest.mark.parametrize("path", ["/ws", "/ws/telemetry"])
def test_telemetry_websockets_accept_a_valid_header_key(configure_auth, monkeypatch, path):
    client = configure_auth(MIA_API_KEY=WRITE_KEY)
    monkeypatch.setattr(api_main, "asyncio", _OneTickAsyncio())
    with client.websocket_connect(path, headers={"X-API-Key": WRITE_KEY}) as ws:
        assert ws.receive_json()


def test_anpr_stream_accepts_a_valid_header_key(configure_auth):
    client = configure_auth(MIA_API_KEY=WRITE_KEY)
    with client.websocket_connect("/anpr/stream", headers={"X-API-Key": WRITE_KEY}) as ws:
        ws.send_text("not json")
        assert ws.receive_json() == {"error": "Invalid JSON"}


@pytest.mark.parametrize("path", ["/ws", "/ws/telemetry"])
def test_telemetry_websockets_open_when_no_key_is_configured(configure_auth, monkeypatch, path):
    client = configure_auth()
    monkeypatch.setattr(api_main, "asyncio", _OneTickAsyncio())
    with client.websocket_connect(path) as ws:
        assert ws.receive_json()


def _preflight(origin):
    return TestClient(api_main.app).options(
        "/features", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:8080", "http://mia.local"])
def test_cors_allows_local_origins(origin):
    assert _preflight(origin).headers.get("access-control-allow-origin") == origin


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost.evil.example", "http://192.0.2.1"])
def test_cors_rejects_foreign_origins(origin):
    assert "access-control-allow-origin" not in _preflight(origin).headers
