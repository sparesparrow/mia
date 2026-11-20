"""GET /admin/update/pair is read-only; the API has no write path to the key list (REQ-UPD-004, ADR-0023)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", "apps", "rpi-backend", "py-api"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import main as api_main  # noqa: E402
from api.auth import api_key as api_key_module  # noqa: E402
from api.auth import dependencies as deps  # noqa: E402

pytestmark = pytest.mark.req("REQ-UPD-004")

ADMIN = "mia_api_admin_0123456789abcdef0"
WRITE = "mia_api_readwrite_0123456789abcd"
OPTS = 'restrict,command="sudo /opt/mia/bin/mia-apply-update",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-user-rc'
BODY = "AAAAC3NzaC1lZDI1NTE5AAAAIAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB"


def _reset(monkeypatch):
    for name in ("MIA_API_KEY", "MIA_API_KEYS", "MIA_AUTH_DISABLED"):
        monkeypatch.delenv(name, raising=False)
    deps._verified.clear()


@pytest.fixture
def client(monkeypatch, tmp_path):
    keys = tmp_path / "update_authorized_keys"
    keys.write_text(f"{OPTS} ssh-ed25519 {BODY} mia-phone:pixel\n")
    monkeypatch.setenv("MIA_AUTHORIZED_KEYS", str(keys))
    _reset(monkeypatch)
    monkeypatch.setenv("MIA_API_KEY", ADMIN)
    monkeypatch.setenv("MIA_API_KEYS", WRITE)
    monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
    c = TestClient(api_main.app)
    c.keys_file = keys
    yield c
    deps._verified.clear()
    api_key_module._api_key_auth = None


def test_listing_needs_the_admin_scope(client):
    assert client.get("/admin/update/pair").status_code == 401
    assert client.get("/admin/update/pair", headers={"X-API-Key": WRITE}).status_code == 403


def test_an_admin_lists_labels_and_fingerprints_never_keys(client):
    phones = client.get("/admin/update/pair", headers={"X-API-Key": ADMIN}).json()["phones"]
    assert [p["label"] for p in phones] == ["pixel"]
    assert phones[0]["fingerprint"].startswith("SHA256:") and BODY not in str(phones)


def test_a_missing_list_is_empty(client):
    client.keys_file.unlink()
    assert client.get("/admin/update/pair", headers={"X-API-Key": ADMIN}).json() == {"phones": []}


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_the_api_has_no_way_to_change_the_list(client, method):
    before = client.keys_file.read_text()
    for path in ("/admin/update/pair", "/admin/update/pair/pixel"):
        reply = getattr(client, method)(path, headers={"X-API-Key": ADMIN})
        assert reply.status_code in (404, 405)
    assert client.keys_file.read_text() == before


def test_the_router_defines_only_a_get():
    from api.routers import update_pairing

    assert {m for r in update_pairing.router.routes for m in r.methods} == {"GET"}


def test_listing_is_refused_when_authentication_is_disabled(monkeypatch, tmp_path):
    _reset(monkeypatch)
    monkeypatch.setenv("MIA_AUTHORIZED_KEYS", str(tmp_path / "keys"))
    monkeypatch.setenv("MIA_AUTH_DISABLED", "1")
    monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
    try:
        assert TestClient(api_main.app).get("/admin/update/pair").status_code == 503
    finally:
        deps._verified.clear()
        api_key_module._api_key_auth = None
