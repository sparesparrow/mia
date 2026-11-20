"""bin/mia-update-pair: root-only pairing into a root-owned key list (REQ-UPD-004)."""

import base64
import importlib.machinery
import importlib.util
import os
import stat
import struct
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.req("REQ-UPD-004")

TOOL = Path(__file__).resolve().parents[3] / "bin" / "mia-update-pair"


@pytest.fixture
def pair(monkeypatch, tmp_path):
    loader = importlib.machinery.SourceFileLoader("mia_update_pair", str(TOOL))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("mia_update_pair", loader))
    loader.exec_module(mod)
    keys = tmp_path / "etc" / "update_authorized_keys"
    monkeypatch.setenv("MIA_AUTHORIZED_KEYS", str(keys))
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(mod, "_chown_root", lambda path: None)
    mod.keys = keys
    return mod


def _blob(*fields):
    return b"".join(struct.pack(">I", len(f)) + f for f in fields)


def ed(payload=b"\x01" * 32):
    return "ssh-ed25519 " + base64.b64encode(_blob(b"ssh-ed25519", payload)).decode()


def ec(point=b"\x04" + b"\x02" * 64):
    return "ecdsa-sha2-nistp256 " + base64.b64encode(_blob(b"ecdsa-sha2-nistp256", b"nistp256", point)).decode()


def test_it_refuses_to_run_as_a_normal_user(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("running as root")
    env = {**os.environ, "MIA_AUTHORIZED_KEYS": str(tmp_path / "keys")}
    done = subprocess.run([sys.executable, str(TOOL), "add", "x", ed()], env=env, capture_output=True, text=True)
    assert done.returncode == 1 and "root" in done.stderr
    assert not (tmp_path / "keys").exists()


def test_add_writes_a_restricted_world_readable_entry(pair, capsys):
    assert pair.main(["add", "pixel", ed() + " phone@home"]) == 0
    line = pair.keys.read_text().strip()
    assert line.startswith(
        'restrict,command="sudo /opt/mia/bin/mia-apply-update",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding'
    )
    assert line.endswith(" mia-phone:pixel") and "phone@home" not in line
    assert stat.S_IMODE(pair.keys.stat().st_mode) == 0o644
    assert "SHA256:" in capsys.readouterr().out


def test_adding_twice_changes_nothing(pair, capsys):
    pair.main(["add", "pixel", ed()])
    before = pair.keys.read_text()
    assert pair.main(["add", "pixel", ed()]) == 0 and pair.keys.read_text() == before
    assert "already paired" in capsys.readouterr().out


def test_the_same_label_replaces_the_old_key(pair):
    pair.main(["add", "pixel", ed()])
    pair.main(["add", "pixel", ed(b"\x02" * 32)])
    assert len(pair.keys.read_text().splitlines()) == 1


def test_ecdsa_is_accepted(pair):
    assert pair.main(["add", "pixel", ec()]) == 0


@pytest.mark.parametrize(
    "bad",
    [
        'command="rm -rf /" ' + ed(),
        ed() + "\n" + ed(),
        "ssh-dss AAAAB3NzaC1kc3MAAACBAP",
        "ssh-ed25519 !!!notbase64!!!!!!!!",
        "ssh-rsa " + base64.b64encode(_blob(b"ssh-rsa", b"\x01", b"\x01" * 256)).decode(),
        ed(b"\x01" * 31),
        "ssh-ed25519 " + base64.b64encode(_blob(b"ssh-rsa", b"\x01" * 32)).decode(),
        ec(b"\x04" + b"\x02" * 10),
        "",
    ],
)
def test_only_a_strong_plain_key_is_accepted(pair, bad):
    assert pair.main(["add", "pixel", bad]) == 1
    assert not pair.keys.exists()


@pytest.mark.parametrize("label", ["", "a b", "x" * 33, 'a"b', "a\nb"])
def test_a_label_cannot_carry_extra_text(pair, label):
    assert pair.main(["add", label, ed()]) == 1


def test_the_number_of_phones_is_capped(pair):
    for i in range(pair.MAX_KEYS):
        assert pair.main(["add", f"p{i}", ed(bytes([i]) * 32)]) == 0
    assert pair.main(["add", "one-more", ed(b"\xff" * 32)]) == 1


def test_list_and_remove(pair, capsys):
    pair.main(["add", "pixel", ed()])
    capsys.readouterr()
    assert pair.main(["list"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("pixel SHA256:") and "AAAA" not in out
    assert pair.main(["remove", "pixel"]) == 0 and pair.keys.read_text() == ""
    assert pair.main(["remove", "pixel"]) == 1


def test_bad_usage(pair):
    assert pair.main([]) == 2 and pair.main(["add", "only-label"]) == 2
