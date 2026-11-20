"""infra/deploy/rpi/setup-nm-hotspot.sh (REQ-ONB-006, REQ-ONB-007): runs only with a stub nmcli in a tmp dir."""

import base64
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.req("REQ-ONB-006"), pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")]

SCRIPT = Path(__file__).resolve().parents[3] / "infra" / "deploy" / "rpi" / "setup-nm-hotspot.sh"
FLAG = "--i-know-this-drops-wlan0"
MAC = "aa:bb:cc:00:11:22"


def _fp(seed):
    return "SHA256:" + base64.b64encode(hashlib.sha256(seed.encode()).digest()).decode().rstrip("=")


class Box:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        bindir = tmp / "bin"
        bindir.mkdir()
        self.log = tmp / "nmcli.log"
        stub = bindir / "nmcli"  # a stub on PATH: the real nmcli is never called
        stub.write_text(f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{self.log}"\nexit 0\n')
        stub.chmod(0o755)
        self.psk = tmp / "etc" / "hotspot.psk"
        self.dnsmasq = tmp / "nm" / "dnsmasq-shared.d"
        self.phones = tmp / "phones.json"
        self.fp = _fp("phone")
        self.phones.write_text(json.dumps({"version": 1, "phones": {
            self.fp: {"mac": MAC, "bonded": True, "updated": 1},
            _fp("nomac"): {"mac": "", "bonded": False, "updated": 1}}}))
        self.env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "MIA_HOTSPOT_PSK_FILE": str(self.psk),
                    "MIA_DNSMASQ_SHARED_DIR": str(self.dnsmasq), "MIA_PHONES_FILE": str(self.phones)}

    def run(self, *args):
        return subprocess.run(["bash", str(SCRIPT), *args], env=self.env, capture_output=True, text=True, timeout=60)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def box(tmp_path):
    return Box(tmp_path)


def test_refuses_without_the_confirmation_flag(box):
    for args in ([], ["--dry-run"], ["--bogus"]):
        done = box.run(*args)
        assert done.returncode != 0
    assert box.calls() == [] and not box.psk.exists() and not box.dnsmasq.exists()
    assert FLAG in box.run().stderr


def test_dry_run_prints_the_plan_and_writes_nothing(box):
    done = box.run(FLAG, "--dry-run")
    assert done.returncode == 0, done.stderr
    out = done.stdout
    assert "nmcli connection add type wifi" in out and "ipv4.method shared" in out and "802-11-wireless.mode ap" in out
    assert "MIA-Car" in out and f"dhcp-host={MAC}," in out
    assert _fp("nomac") not in out and "dhcp-host=," not in out
    assert box.calls() == [] and not box.psk.exists() and not box.dnsmasq.exists()
    assert not (box.tmp / "nm").exists()


def test_apply_runs_nmcli_writes_psk_and_reservations(box):
    done = box.run(FLAG)
    assert done.returncode == 0, done.stderr
    psk = box.psk.read_text().strip()
    assert 8 <= len(psk) <= 63 and box.psk.stat().st_mode & 0o777 == 0o600
    assert psk not in done.stdout + done.stderr  # never printed
    calls = box.calls()
    add = [c for c in calls if c.startswith("connection add")]
    assert len(add) == 1
    for part in ("type wifi", "ssid MIA-Car", "802-11-wireless.mode ap", "ipv4.method shared", "wifi-sec.key-mgmt wpa-psk"):
        assert part in add[0]
    assert any(c.startswith("connection up MIA-Car") for c in calls)
    fragment = (box.dnsmasq / "mia-phones.conf").read_text()
    lines = [ln for ln in fragment.splitlines() if ln.startswith("dhcp-host=")]
    assert len(lines) == 1 and lines[0].startswith(f"dhcp-host={MAC},192.168.4.")


def test_apply_keeps_an_existing_psk(box):
    box.psk.parent.mkdir(parents=True)
    box.psk.write_text("existing-passphrase\n")
    assert box.run(FLAG).returncode == 0
    assert box.psk.read_text() == "existing-passphrase\n"


def test_reservation_follows_the_registry_after_a_mac_change(box):
    box.run(FLAG)
    first = (box.dnsmasq / "mia-phones.conf").read_text()
    box.phones.write_text(json.dumps({"version": 1, "phones": {box.fp: {"mac": "aa:bb:cc:00:11:99", "bonded": True, "updated": 2}}}))
    box.run(FLAG)
    second = (box.dnsmasq / "mia-phones.conf").read_text()
    assert MAC in first and MAC not in second and "aa:bb:cc:00:11:99" in second
    ip = lambda text: text.split(",")[1].split()[0]  # noqa: E731
    assert ip(first.split("dhcp-host=")[1]) == ip(second.split("dhcp-host=")[1])  # same fingerprint, same address


def test_missing_registry_means_no_reservations(box):
    box.phones.unlink()
    assert box.run(FLAG).returncode == 0
    assert "dhcp-host=" not in (box.dnsmasq / "mia-phones.conf").read_text()


def test_disable_removes_connection_and_fragment(box):
    box.run(FLAG)
    box.log.unlink()
    done = box.run("--disable")
    assert done.returncode == 0, done.stderr
    calls = box.calls()
    assert any(c.startswith("connection down MIA-Car") for c in calls)
    assert any(c.startswith("connection delete MIA-Car") for c in calls)
    assert not (box.dnsmasq / "mia-phones.conf").exists()


def test_disable_dry_run_changes_nothing(box):
    box.run(FLAG)
    box.log.unlink()
    done = box.run("--disable", "--dry-run")
    assert done.returncode == 0 and "connection delete MIA-Car" in done.stdout
    assert box.calls() == [] and (box.dnsmasq / "mia-phones.conf").exists()


def test_shellcheck_clean():
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck not installed")
    done = subprocess.run(["shellcheck", str(SCRIPT)], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout
