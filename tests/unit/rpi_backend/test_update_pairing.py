"""POST /admin/update/pair: admin scope, plain keys only, forced-command entries, idempotence (REQ-UPD-004)."""

import base64
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", "apps", "rpi-backend", "py-api"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import main as api_main  # noqa: E402
from api.auth import api_key as api_key_module  # noqa: E402
from api.auth import dependencies as deps  # noqa: E402
from api.routers import update_pairing as pairing  # noqa: E402

pytestmark = pytest.mark.req("REQ-UPD-004")

ADMIN = "mia_api_admin_0123456789abcdef0"
WRITE = "mia_api_readwrite_0123456789abcd"


def _key(kind="ssh-ed25519", payload=b"\x01" * 32):
    blob = struct.pack(">I", len(kind)) + kind.encode() + struct.pack(">I", len(payload)) + payload
    return f"{kind} {base64.b64encode(blob).decode()}"


@pytest.fixture
def client(monkeypatch, tmp_path):
    keys = tmp_path / "update_authorized_keys"
    monkeypatch.setenv("MIA_AUTHORIZED_KEYS", str(keys))
    for name in ("MIA_API_KEY", "MIA_API_KEYS", "MIA_AUTH_DISABLED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MIA_API_KEY", ADMIN)
    monkeypatch.setenv("MIA_API_KEYS", WRITE)
    deps._verified.clear()
    monkeypatch.setattr(api_key_module, "_api_key_auth", api_key_module.APIKeyAuth())
    c = TestClient(api_main.app)
    c.keys_file = keys
    yield c
    deps._verified.clear()
    api_key_module._api_key_auth = None


def _post(client, key, label="pixel", token=ADMIN):
    return client.post("/admin/update/pair", json={"public_key": key, "label": label}, headers={"X-API-Key": token})


def test_pairing_needs_the_admin_scope(client):
    body = {"public_key": _key(), "label": "pixel"}
    assert client.post("/admin/update/pair", json=body).status_code == 401
    assert client.post("/admin/update/pair", json=body, headers={"X-API-Key": WRITE}).status_code == 403
    assert not client.keys_file.exists()


def test_an_admin_key_pairs_a_phone_with_a_forced_command(client):
    reply = _post(client, _key() + " phone@home")
    assert reply.status_code == 200 and reply.json()["status"] == "paired"
    assert reply.json()["fingerprint"].startswith("SHA256:")
    line = client.keys_file.read_text().strip()
    assert line.startswith(
        'command="sudo /opt/mia/bin/mia-apply-update",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding ssh-ed25519 '
    )
    assert line.endswith(" mia-phone:pixel") and "phone@home" not in line
    assert (client.keys_file.stat().st_mode & 0o777) == 0o600


def test_pairing_twice_changes_nothing(client):
    assert _post(client, _key()).json()["status"] == "paired"
    before = client.keys_file.read_text()
    assert _post(client, _key()).json()["status"] == "already_paired"
    assert client.keys_file.read_text() == before


def test_the_same_label_replaces_the_old_key(client):
    _post(client, _key(payload=b"\x01" * 32))
    _post(client, _key(payload=b"\x02" * 32))
    assert len(client.keys_file.read_text().splitlines()) == 1


@pytest.mark.parametrize(
    "bad",
    [
        'command="rm -rf /" ' + _key(),
        _key() + "\n" + _key(),
        "ssh-dss AAAAB3NzaC1kc3MAAACBAP",
        "ssh-ed25519 !!!notbase64!!!!!!!!",
        "ssh-rsa " + base64.b64encode(struct.pack(">I", 7) + b"ssh-dss").decode(),
        "",
    ],
)
def test_only_a_plain_public_key_is_accepted(client, bad):
    assert _post(client, bad).status_code == 422
    assert not client.keys_file.exists()


@pytest.mark.parametrize("label", ["", "a b", "x" * 33, 'a"b', "a\nb"])
def test_a_label_cannot_carry_extra_text(client, label):
    assert _post(client, _key(), label=label).status_code == 422


def test_the_number_of_phones_is_capped(client):
    for i in range(pairing.MAX_KEYS):
        assert _post(client, _key(payload=bytes([i]) * 32), label=f"p{i}").status_code == 200
    assert _post(client, _key(payload=b"\xff" * 32), label="one-more").status_code == 409


def test_a_phone_can_be_listed_and_revoked(client):
    _post(client, _key())
    listed = client.get("/admin/update/pair", headers={"X-API-Key": ADMIN}).json()["phones"]
    assert [p["label"] for p in listed] == ["pixel"] and "key" not in listed[0]
    assert client.delete("/admin/update/pair/pixel", headers={"X-API-Key": WRITE}).status_code == 403
    assert client.delete("/admin/update/pair/pixel", headers={"X-API-Key": ADMIN}).status_code == 200
    assert client.keys_file.read_text() == ""
    assert client.delete("/admin/update/pair/pixel", headers={"X-API-Key": ADMIN}).status_code == 404
