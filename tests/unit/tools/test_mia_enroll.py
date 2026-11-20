"""bin/mia-enroll: offline grant verification, replay refusal and the enrollment side effects (REQ-ONB-001..005).

Keys are throwaway ssh-keygen keys in tmp dirs; every path the tool touches is an MIA_* override.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs ssh-keygen")

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "bin" / "mia-enroll"
PAIR = ROOT / "bin" / "mia-update-pair"
NOW = 1_800_000_000


def _load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def enroll():
    return _load("mia_enroll", TOOL)


def _keygen(path: Path) -> str:
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "t", "-f", str(path)], check=True)
    return path.with_suffix(".pub").read_text() if path.suffix else Path(str(path) + ".pub").read_text()


def _fp(pub: Path) -> str:
    out = subprocess.run(["ssh-keygen", "-lf", str(pub)], check=True, capture_output=True, text=True).stdout
    return out.split()[1]


class World:
    """A signer, a Pi host key and a phone key, plus a grant factory."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.signer = tmp / "signer"
        self.phone = tmp / "phone"
        self.host = tmp / "host"
        self.other = tmp / "other"
        for key in (self.signer, self.phone, self.host, self.other):
            _keygen(key)
        self.allowed = tmp / "allowed_signers"
        pub = Path(str(self.signer) + ".pub").read_text().split()
        self.allowed.write_text(f'mia-auth-server namespaces="mia-grant" {pub[0]} {pub[1]}\n')
        self.device_fp = _fp(Path(str(self.host) + ".pub"))
        self.phone_fp = _fp(Path(str(self.phone) + ".pub"))
        self.phone_pub = Path(str(self.phone) + ".pub").read_text().strip()

    def claims(self, **over):
        c = {
            "v": 1, "account_id": "acc-1", "jti": "jti-1", "device_fp": self.device_fp, "phone_fp": self.phone_fp,
            "plan": "pro", "entitlement_exp": NOW + 86400, "iat": NOW - 10, "exp": NOW + 300,
        }
        c.update(over)
        return {k: v for k, v in c.items() if v is not None}

    def sign(self, claims: dict, key: Path = None):
        grant = json.dumps(claims).encode()
        data = self.tmp / "grant.json"
        data.write_bytes(grant)
        sig = Path(str(data) + ".sig")
        sig.unlink(missing_ok=True)
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(key or self.signer), "-n", "mia-grant", str(data)], check=True)
        return grant, sig.read_bytes()


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def _verify(enroll, w, grant, sig, **over):
    args = dict(device_fp=w.device_fp, phone_fp=w.phone_fp, now=NOW, seen_jti=set())
    args.update(over)
    return enroll.verify_grant(grant, sig, w.allowed, **args)


@pytest.mark.req("REQ-ONB-001", "REQ-ONB-002")
def test_valid_grant_accepted(enroll, world):
    grant, sig = world.sign(world.claims())
    claims = _verify(enroll, world, grant, sig)
    assert (claims.account_id, claims.jti, claims.plan) == ("acc-1", "jti-1", "pro")
    assert claims.entitlement_exp == NOW + 86400 and claims.exp == NOW + 300
    assert claims.phone_fp == world.phone_fp and claims.device_fp == world.device_fp


@pytest.mark.req("REQ-ONB-002")
def test_expired_grant_refused(enroll, world):
    grant, sig = world.sign(world.claims())
    with pytest.raises(enroll.GrantError) as err:
        _verify(enroll, world, grant, sig, now=NOW + 300)
    assert "expired" in err.value.reason
    with pytest.raises(enroll.GrantError):
        _verify(enroll, world, grant, sig, now=NOW + 5000)


@pytest.mark.req("REQ-ONB-002")
def test_grant_issued_in_the_future_refused_beyond_skew(enroll, world):
    grant, sig = world.sign(world.claims(iat=NOW + 3600, exp=NOW + 4000))
    with pytest.raises(enroll.GrantError):
        _verify(enroll, world, grant, sig)
    grant, sig = world.sign(world.claims(iat=NOW + 5))
    _verify(enroll, world, grant, sig)  # inside the clock-skew allowance


@pytest.mark.req("REQ-ONB-002")
def test_wrong_device_fingerprint_refused(enroll, world):
    grant, sig = world.sign(world.claims(device_fp=_fp(Path(str(world.other) + ".pub"))))
    with pytest.raises(enroll.GrantError) as err:
        _verify(enroll, world, grant, sig)
    assert "device" in err.value.reason


@pytest.mark.req("REQ-ONB-002")
def test_wrong_phone_fingerprint_refused(enroll, world):
    grant, sig = world.sign(world.claims())
    with pytest.raises(enroll.GrantError) as err:
        _verify(enroll, world, grant, sig, phone_fp=_fp(Path(str(world.other) + ".pub")))
    assert "phone" in err.value.reason


@pytest.mark.req("REQ-ONB-003")
def test_replayed_jti_refused(enroll, world):
    grant, sig = world.sign(world.claims())
    with pytest.raises(enroll.GrantError) as err:
        _verify(enroll, world, grant, sig, seen_jti={"jti-1"})
    assert "replay" in err.value.reason


@pytest.mark.req("REQ-ONB-001")
def test_bad_signature_refused(enroll, world):
    grant, sig = world.sign(world.claims())
    with pytest.raises(enroll.GrantError):
        _verify(enroll, world, grant + b" ", sig)  # tampered bytes
    foreign_grant, foreign_sig = world.sign(world.claims(), key=world.other)  # a key not in allowed_signers
    with pytest.raises(enroll.GrantError):
        _verify(enroll, world, foreign_grant, foreign_sig)
    with pytest.raises(enroll.GrantError):
        _verify(enroll, world, grant, b"not a signature")


@pytest.mark.req("REQ-ONB-001")
def test_unknown_claim_ignored_but_missing_claim_refused(enroll, world):
    grant, sig = world.sign(world.claims(extra="x"))
    _verify(enroll, world, grant, sig)
    for name in ("account_id", "jti", "plan", "entitlement_exp", "exp", "iat", "device_fp", "phone_fp", "v"):
        grant, sig = world.sign(world.claims(**{name: None}))
        with pytest.raises(enroll.GrantError) as err:
            _verify(enroll, world, grant, sig)
        assert name in err.value.reason


@pytest.mark.req("REQ-ONB-001")
def test_wrong_claim_types_refused(enroll, world):
    for over in ({"exp": "soon"}, {"exp": True}, {"v": 2}, {"jti": ""}, {"plan": 3}):
        grant, sig = world.sign(world.claims(**over))
        with pytest.raises(enroll.GrantError):
            _verify(enroll, world, grant, sig)


@pytest.mark.req("REQ-ONB-001")
def test_verification_runs_ssh_keygen_without_a_shell(enroll, world, monkeypatch):
    seen = []
    real = subprocess.run

    def spy(cmd, *a, **kw):
        seen.append((cmd, kw.get("shell", False)))
        return real(cmd, *a, **kw)

    monkeypatch.setattr(enroll.subprocess, "run", spy)
    grant, sig = world.sign(world.claims())
    _verify(enroll, world, grant, sig)
    assert seen and all(isinstance(c, list) and not shell for c, shell in seen)
    assert any(c[:3] == ["ssh-keygen", "-Y", "verify"] and "mia-grant" in c for c, _ in seen)


@pytest.mark.req("REQ-ONB-004")
def test_label_matches_the_pair_tool_pattern(enroll, world):
    pair = _load("mia_update_pair", PAIR)
    _, body = pair.parse_public_key(world.phone_pub)
    label = enroll.phone_label(body)
    assert pair.LABEL_RE.match(label) and label.startswith("phone-") and len(label) == 18
    import base64

    assert label == "phone-" + hashlib.sha256(base64.b64decode(body)).hexdigest()[:12]


# --- CLI -----------------------------------------------------------------------------------------------------------


def _run(world, request, env_extra=None, **over):
    tmp = world.tmp
    env = {
        "PATH": os.environ["PATH"],
        "MIA_ALLOWED_SIGNERS": str(world.allowed),
        "MIA_DEVICE_PUB": str(world.host) + ".pub",
        "MIA_ENROLL_DIR": str(tmp / "state"),
        "MIA_ENV_FILE": str(tmp / "etc" / "environment"),
        "MIA_CONFIG_D": str(tmp / "etc" / "config.d"),
        "MIA_AUTHORIZED_KEYS": str(tmp / "etc" / "update_authorized_keys"),
        "MIA_PAIR_TOOL": str(PAIR),
        "MIA_ENROLL_NOW": str(NOW),
        "MIA_ENROLL_SKIP_CHOWN": "1",
        "MIA_PHONES_FILE": str(tmp / "state" / "phones.json"),
        "MIA_PAIRING_WINDOW": str(tmp / "run" / "pairing-window"),
    }
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(TOOL)], input=json.dumps(request) + "\n", env=env, capture_output=True,
                          text=True, timeout=60)


def _request(world, claims=None, phone_key=None):
    grant, sig = world.sign(claims or world.claims())
    return {"grant": grant.decode(), "signature": sig.decode(), "phone_public_key": phone_key or world.phone_pub}


def _last(done):
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.mark.req("REQ-ONB-001", "REQ-ONB-003", "REQ-ONB-004", "REQ-ONB-005")
def test_cli_enrolls_once_and_keeps_existing_environment_lines(world):
    env_file = world.tmp / "etc" / "environment"
    env_file.parent.mkdir()
    env_file.write_text("FOO=bar\n# comment\nMIA_USER=mia\n")
    done = _run(world, _request(world))
    assert done.returncode == 0, done.stderr
    assert _last(done) == {"ok": True, "step": "enrolled", "error": None}
    lines = env_file.read_text().splitlines()
    assert lines[:3] == ["FOO=bar", "# comment", "MIA_USER=mia"]
    key_lines = [ln for ln in lines if ln.startswith("MIA_API_KEY=")]
    assert len(key_lines) == 1 and len(key_lines[0]) > len("MIA_API_KEY=") + 20
    assert env_file.stat().st_mode & 0o777 == 0o600
    # The key never reaches stdout or stderr.
    assert key_lines[0].split("=", 1)[1] not in done.stdout + done.stderr
    billing = json.loads((world.tmp / "etc" / "config.d" / "60-billing.json").read_text())
    assert billing == {"account_id": "acc-1", "plan": "pro", "entitlement_exp": NOW + 86400}
    keys = (world.tmp / "etc" / "update_authorized_keys").read_text()
    assert 'command="sudo /opt/mia/bin/mia-apply-update"' in keys and "mia-phone:phone-" in keys
    assert (world.tmp / "state" / "seen_jti").read_text().split() == ["jti-1"]
    # Replaying the same grant is refused and changes nothing.
    before = env_file.read_text(), keys
    again = _run(world, _request(world))
    assert again.returncode == 1 and _last(again)["ok"] is False and "replay" in _last(again)["error"]
    assert (env_file.read_text(), (world.tmp / "etc" / "update_authorized_keys").read_text()) == before


@pytest.mark.req("REQ-ONB-005")
def test_cli_leaves_an_existing_api_key_alone(world):
    env_file = world.tmp / "etc" / "environment"
    env_file.parent.mkdir()
    env_file.write_text("MIA_API_KEY=keep-me-1234567890\n")
    done = _run(world, _request(world))
    assert done.returncode == 0, done.stderr
    assert env_file.read_text() == "MIA_API_KEY=keep-me-1234567890\n"
    assert "keep-me" not in done.stdout + done.stderr


@pytest.mark.req("REQ-ONB-003", "REQ-ONB-002")
def test_cli_refusal_changes_no_state(world):
    cases = {
        "phone key not the grant's": _request(world, phone_key=Path(str(world.other) + ".pub").read_text().strip()),
        "wrong device": _request(world, claims=world.claims(device_fp=_fp(Path(str(world.other) + ".pub")))),
        "expired": _request(world, claims=world.claims(exp=NOW - 1)),
    }
    for name, req in cases.items():
        done = _run(world, req)
        assert done.returncode == 1, name
        assert _last(done)["ok"] is False and _last(done)["error"], name
    bad = _run(world, {"grant": "x"})
    assert bad.returncode == 1 and _last(bad)["ok"] is False
    junk = subprocess.run([sys.executable, str(TOOL)], input="not json\n", capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], "MIA_ENROLL_DIR": str(world.tmp / "state")})
    assert junk.returncode == 1 and _last(junk)["ok"] is False
    for name in ("state", "etc"):
        assert not (world.tmp / name).exists() or not any(p.is_file() and p.stat().st_size for p in (world.tmp / name).rglob("*")), name


# --- fix round 1 -----------------------------------------------------------------------------------------------------


@pytest.mark.req("REQ-ONB-003")
@pytest.mark.parametrize("jti", ["a b", "a\nb", "a\tb", "a/b", "é", "x" * 129, ""])
def test_jti_outside_the_allowed_alphabet_is_refused(enroll, world, jti):
    grant, sig = world.sign(world.claims(jti=jti))
    with pytest.raises(enroll.GrantError) as err:
        _verify(enroll, world, grant, sig)
    assert "jti" in err.value.reason


@pytest.mark.req("REQ-ONB-003")
def test_cli_whitespace_jti_refused_and_nothing_stored(world):
    done = _run(world, _request(world, claims=world.claims(jti="a b")))
    assert done.returncode == 1 and _last(done)["ok"] is False and "jti" in _last(done)["error"]
    assert not (world.tmp / "state" / "seen_jti").exists()
    assert not (world.tmp / "etc").exists()


@pytest.mark.req("REQ-ONB-003")
def test_cli_prefix_jti_is_not_a_replay_of_a_longer_one(world):
    first = _run(world, _request(world, claims=world.claims(jti="ab")))
    assert first.returncode == 0, first.stderr
    second = _run(world, _request(world, claims=world.claims(jti="a")))
    assert second.returncode == 0, _last(second)
    assert (world.tmp / "state" / "seen_jti").read_text().splitlines() == ["a", "ab"]
    replay = _run(world, _request(world, claims=world.claims(jti="ab")))
    assert replay.returncode == 1 and "replay" in _last(replay)["error"]


def _failing_pair_tool(world) -> Path:
    stub = world.tmp / "pair-fails"
    stub.write_text(PAIR.read_text() + "\n\ndef add(*args, **kwargs):\n    raise OSError(5, 'simulated write failure')\n")
    return stub


@pytest.mark.req("REQ-ONB-003")
def test_cli_failed_pairing_burns_the_grant(world):
    req = _request(world)
    bad = _run(world, req, env_extra={"MIA_PAIR_TOOL": str(_failing_pair_tool(world))})
    assert bad.returncode == 1 and _last(bad)["ok"] is False
    assert (world.tmp / "state" / "seen_jti").read_text().splitlines() == ["jti-1"]
    retry = _run(world, req)
    assert retry.returncode == 1 and "replay" in _last(retry)["error"]
    assert not (world.tmp / "etc" / "update_authorized_keys").exists()


@pytest.mark.req("REQ-ONB-003")
def test_cli_failed_billing_write_burns_the_grant(world):
    blocker = world.tmp / "blocker"
    blocker.write_text("a file, not a directory")
    req = _request(world)
    bad = _run(world, req, env_extra={"MIA_CONFIG_D": str(blocker / "config.d")})
    assert bad.returncode == 1 and _last(bad)["ok"] is False
    retry = _run(world, req)
    assert retry.returncode == 1 and "replay" in _last(retry)["error"]


@pytest.mark.req("REQ-ONB-005")
@pytest.mark.parametrize("empty", ["MIA_API_KEY=\n", "MIA_API_KEY=\"\"\n", "export MIA_API_KEY=\n"])
def test_cli_empty_api_key_line_counts_as_absent(world, empty):
    env_file = world.tmp / "etc" / "environment"
    env_file.parent.mkdir()
    env_file.write_text("FOO=bar\n" + empty)
    done = _run(world, _request(world))
    assert done.returncode == 0, done.stderr
    lines = env_file.read_text().splitlines()
    assert lines[:2] == ["FOO=bar", empty.rstrip("\n")]  # existing lines untouched
    assert len(lines) == 3 and lines[2].startswith("MIA_API_KEY=") and len(lines[2]) > len("MIA_API_KEY=") + 20
    assert lines[2].split("=", 1)[1] not in done.stdout + done.stderr
    assert env_file.stat().st_mode & 0o777 == 0o600


@pytest.mark.req("REQ-ONB-005")
def test_cli_api_key_set_then_blanked_later_gets_a_new_line(world):
    env_file = world.tmp / "etc" / "environment"
    env_file.parent.mkdir()
    env_file.write_text("MIA_API_KEY=old-secret-123\nMIA_API_KEY=\n")
    done = _run(world, _request(world))
    assert done.returncode == 0
    lines = env_file.read_text().splitlines()
    assert lines[:2] == ["MIA_API_KEY=old-secret-123", "MIA_API_KEY="] and len(lines) == 3


@pytest.mark.req("REQ-ONB-002")
def test_cli_always_ends_with_the_json_line_on_internal_errors(world):
    env_file = world.tmp / "etc" / "environment"
    env_file.parent.mkdir()
    env_file.write_bytes(b"MIA_USER=\xff\xfe\n")
    bad_env = _run(world, _request(world))
    assert bad_env.returncode != 0
    last = _last(bad_env)
    assert last["ok"] is False and last["step"] in ("internal", "io") and last["error"]
    bad_now = _run(world, _request(world), env_extra={"MIA_ENROLL_NOW": "not-a-number"})
    assert bad_now.returncode != 0
    last = _last(bad_now)
    assert last["ok"] is False and last["step"] == "internal" and "not-a-number" not in last["error"]
    assert "Traceback" not in bad_now.stdout


@pytest.mark.req("REQ-ONB-002")
def test_internal_error_message_never_contains_environment_file_content(world):
    env_file = world.tmp / "etc" / "environment"
    env_file.parent.mkdir()
    env_file.write_bytes(b"MIA_API_KEY=topsecretvalue\n\xff\n")
    done = _run(world, _request(world))
    assert done.returncode != 0 and _last(done)["ok"] is False
    assert "topsecretvalue" not in done.stdout + done.stderr


# --- phone registry and Bluetooth pairing window (REQ-ONB-007, REQ-ONB-009) ------------------------------------------


def _registry():
    return _load("mia_phone_registry", ROOT / "bin" / "mia-phone-registry")


@pytest.mark.req("REQ-ONB-007")
def test_cli_registers_the_phone_by_fingerprint_with_its_mac(world):
    request = _request(world)
    request["phone_mac"] = "AA:BB:CC:00:11:22"
    done = _run(world, request)
    assert done.returncode == 0, done.stderr
    assert _last(done) == {"ok": True, "step": "enrolled", "error": None}  # no warning key when all went well
    stored = json.loads((world.tmp / "state" / "phones.json").read_text())["phones"]
    assert stored[world.phone_fp]["mac"] == "aa:bb:cc:00:11:22" and stored[world.phone_fp]["bonded"] is False
    assert list(stored) == [world.phone_fp]


@pytest.mark.req("REQ-ONB-007")
@pytest.mark.parametrize("mac", [None, "not-a-mac", 5, "aa:bb:cc:00:11"])
def test_cli_missing_or_invalid_mac_registers_with_an_empty_mac(world, mac):
    request = _request(world)
    if mac is not None:
        request["phone_mac"] = mac
    done = _run(world, request)
    assert _last(done)["ok"] is True
    stored = json.loads((world.tmp / "state" / "phones.json").read_text())["phones"]
    assert stored[world.phone_fp]["mac"] == ""


@pytest.mark.req("REQ-ONB-007")
def test_cli_registry_failure_keeps_the_pairing_and_warns(world):
    blocker = world.tmp / "blocker"
    blocker.write_text("a file, so the registry directory cannot be made")
    done = _run(world, _request(world), env_extra={"MIA_PHONES_FILE": str(blocker / "phones.json")})
    last = _last(done)
    assert done.returncode == 0 and last["ok"] is True and last["step"] == "enrolled" and last["error"] is None
    assert "registry" in last["warning"]
    assert "mia-phone:phone-" in (world.tmp / "etc" / "update_authorized_keys").read_text()  # pairing not undone
    assert (world.tmp / "state" / "seen_jti").read_text().split() == ["jti-1"]


@pytest.mark.req("REQ-ONB-007")
def test_cli_refused_request_registers_nothing(world):
    done = _run(world, _request(world, world.claims(exp=NOW - 1)))
    assert _last(done)["ok"] is False
    assert not (world.tmp / "state" / "phones.json").exists()


@pytest.mark.req("REQ-ONB-009")
def test_cli_opens_a_120_second_pairing_window_after_success(world):
    window = world.tmp / "run" / "pairing-window"
    done = _run(world, _request(world))
    assert _last(done)["ok"] is True
    assert window.read_text().strip() == str(NOW + 120)
    assert window.stat().st_mode & 0o777 == 0o644  # the unprivileged agent user must be able to read it


@pytest.mark.req("REQ-ONB-009")
def test_cli_refusal_opens_no_pairing_window(world):
    done = _run(world, _request(world, world.claims(exp=NOW - 1)))
    assert _last(done)["ok"] is False
    assert not (world.tmp / "run" / "pairing-window").exists()


@pytest.mark.req("REQ-ONB-009")
def test_cli_window_failure_is_a_warning_not_an_error(world):
    blocker = world.tmp / "blocker"
    blocker.write_text("x")
    done = _run(world, _request(world), env_extra={"MIA_PAIRING_WINDOW": str(blocker / "pairing-window")})
    last = _last(done)
    assert done.returncode == 0 and last["ok"] is True and "pairing window" in last["warning"]
