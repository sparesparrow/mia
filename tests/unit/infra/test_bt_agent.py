"""infra/systemd/mia-bt-agent.service and infra/deploy/rpi/mia-bt-window.sh (REQ-ONB-009): static unit checks, and the
window logic run against stub busctl/bt-agent in a tmp dir. Real Bluetooth behaviour is not exercised."""

import configparser
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.req("REQ-ONB-009"), pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")]

ROOT = Path(__file__).resolve().parents[3]
UNIT = ROOT / "infra" / "systemd" / "mia-bt-agent.service"
SCRIPT = ROOT / "infra" / "deploy" / "rpi" / "mia-bt-window.sh"
NOW = 1_800_000_000


def _unit():
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    parser.read(UNIT, encoding="utf-8")
    return parser


def test_unit_runs_as_mia_with_the_window_script_and_restarts():
    service = _unit()["Service"]
    assert service["User"] == "mia"
    assert service["ExecStart"].split()[0] == "/opt/mia/infra/deploy/rpi/mia-bt-window.sh"
    assert service["Restart"] in ("always", "on-failure")
    assert "bluetooth.service" in _unit()["Unit"]["Requires"]
    assert "bluetooth" in service["SupplementaryGroups"].split()


def test_unit_exposes_no_network():
    text = UNIT.read_text(encoding="utf-8")
    service = _unit()["Service"]
    assert service["RestrictAddressFamilies"] == "AF_UNIX"  # D-Bus only: no IP, no Bluetooth socket
    assert service["NoNewPrivileges"] == "true"
    assert not any(word in text for word in ("ListenStream", "ListenDatagram", "BindTo", "IPAddressAllow", "Environment=MIA_API"))
    assert "bluetoothctl" not in service["ExecStart"]  # unreliable without a tty


def _box(tmp: Path):
    bindir = tmp / "bin"
    bindir.mkdir()
    log = tmp / "calls.log"
    for name in ("busctl", "bt-agent"):
        stub = bindir / name
        stub.write_text(f'#!/bin/bash\nprintf "{name} %s\\n" "$*" >> "{log}"\nexit 0\n')
        stub.chmod(0o755)
    env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "MIA_PAIRING_WINDOW": str(tmp / "pairing-window"),
           "MIA_BT_NOW": str(NOW), "MIA_BT_ADAPTER": "/org/bluez/hci9"}
    return env, log


def _once(env):
    return subprocess.run(["bash", str(SCRIPT), "--once"], env=env, capture_output=True, text=True, timeout=30)


def _sets(log):
    calls = log.read_text().splitlines() if log.exists() else []
    return [c for c in calls if c.startswith("busctl")]


def test_window_open_makes_the_adapter_discoverable_and_pairable(tmp_path):
    env, log = _box(tmp_path)
    (tmp_path / "pairing-window").write_text(f"{NOW + 100}\n")
    assert _once(env).returncode == 0
    sets = _sets(log)
    assert any("Discoverable b true" in c and "/org/bluez/hci9" in c for c in sets)
    assert any("Pairable b true" in c for c in sets)
    assert (tmp_path / "pairing-window").exists()


@pytest.mark.parametrize("content", [None, f"{NOW}\n", f"{NOW - 5}\n", "garbage\n", f"{NOW + 100000}\n", ""])
def test_window_closed_when_missing_expired_or_invalid(tmp_path, content):
    env, log = _box(tmp_path)
    if content is not None:
        (tmp_path / "pairing-window").write_text(content)
    assert _once(env).returncode == 0
    sets = _sets(log)
    assert any("Discoverable b false" in c for c in sets) and any("Pairable b false" in c for c in sets)
    assert not any("b true" in c for c in sets)
    assert not (tmp_path / "pairing-window").exists()  # an expired or bogus window file is removed


def test_shellcheck_clean():
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck not installed")
    done = subprocess.run(["shellcheck", str(SCRIPT)], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout


@pytest.mark.skipif(shutil.which("systemd-analyze") is None, reason="systemd-analyze not installed")
def test_systemd_analyze_verify_accepts_the_unit(tmp_path):
    """Real, state-free check (R8): the unit is copied and its ExecStart (an /opt/mia path that does not exist here) is
    pointed at an existing executable, so verify judges the rest of the unit."""
    true = shutil.which("true") or "/bin/true"
    lines = [f"ExecStart={true}" if ln.startswith("ExecStart=") else ln for ln in UNIT.read_text(encoding="utf-8").splitlines()]
    copy = tmp_path / "mia-bt-agent.service"
    copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
    done = subprocess.run(["systemd-analyze", "verify", str(copy)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0 and done.stderr.strip() == "", done.stderr
    broken = tmp_path / "broken" / "mia-bt-agent.service"
    broken.parent.mkdir()
    broken.write_text(copy.read_text().replace("[Service]", "[Service]\nNoSuchDirective=1\nExecStart=/nonexistent/x"), encoding="utf-8")
    bad = subprocess.run(["systemd-analyze", "verify", str(broken)], capture_output=True, text=True, timeout=60)
    assert bad.returncode != 0 or bad.stderr.strip()  # the check does bite
