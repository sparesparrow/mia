"""infra/deploy/rpi/setup-nm-hotspot.sh (REQ-ONB-006, REQ-ONB-007): runs with a stub nmcli on PATH in a tmp dir. The stub
forwards only `nmcli --offline ...` (prints a keyfile, touches nothing, ruling R8) to the real nmcli when present; every
other subcommand is only recorded. dnsmasq --test validates the generated fragment."""

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
    def __init__(self, tmp: Path, use_real_offline=False):
        self.tmp = tmp
        bindir = tmp / "bin"
        bindir.mkdir()
        self.log = tmp / "nmcli.log"
        stub = bindir / "nmcli"  # a stub on PATH: the real nmcli is never called
        real = shutil.which("nmcli") if use_real_offline else None
        offline = f'exec "{real}" "$@"' if real else (
            'printf "[connection]\\nid=MIA-Car\\n\\n[wifi]\\nmode=ap\\n\\n[wifi-security]\\nkey-mgmt=wpa-psk\\n\\n'
            '[ipv4]\\nmethod=shared\\n"')
        stub.write_text(
            f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{self.log}"\n[ "$1" = "--offline" ] && {{ {offline}; exit $?; }}\nexit 0\n')
        stub.chmod(0o755)
        self.psk = tmp / "etc" / "hotspot.psk"
        self.dnsmasq = tmp / "nm" / "dnsmasq-shared.d"
        self.phones = tmp / "phones.json"
        self.fp = _fp("phone")
        self.phones.write_text(json.dumps({"version": 1, "phones": {
            self.fp: {"mac": MAC, "bonded": True, "updated": 1},
            _fp("nomac"): {"mac": "", "bonded": False, "updated": 1}}}))
        self.env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "MIA_HOTSPOT_PSK_FILE": str(self.psk),
                    "MIA_DNSMASQ_SHARED_DIR": str(self.dnsmasq), "MIA_PHONES_FILE": str(self.phones),
                    "MIA_NM_CONNECTIONS_DIR": str(tmp / "nm" / "system-connections")}
        self.keyfile = tmp / "nm" / "system-connections" / "MIA-Car.nmconnection"

    def run(self, *args):
        return subprocess.run(["bash", str(SCRIPT), *args], env=self.env, capture_output=True, text=True, timeout=60)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def box(tmp_path):
    return Box(tmp_path)


def _offline_nmcli_ok():
    """True when the installed nmcli supports --offline (R8: a state-free check, prints a keyfile)."""
    nmcli = shutil.which("nmcli")
    if nmcli is None:
        return False
    done = subprocess.run([nmcli, "--offline", "connection", "add", "type", "wifi", "con-name", "t", "ssid", "t"],
                          capture_output=True, text=True, timeout=30)
    return done.returncode == 0 and "[connection]" in done.stdout


needs_offline_nmcli = pytest.mark.skipif(not _offline_nmcli_ok(), reason="nmcli missing or without --offline")


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
    assert "nmcli --offline connection add type wifi" in out and "ipv4.method shared" in out and "802-11-wireless.mode ap" in out
    assert "<redacted>" in out and "nmcli connection reload" in out
    assert "MIA-Car" in out and f"dhcp-host={MAC}," in out
    assert _fp("nomac") not in out and "dhcp-host=," not in out
    assert box.calls() == [] and not box.psk.exists() and not box.dnsmasq.exists() and not box.keyfile.exists()
    assert not (box.tmp / "nm").exists()


def test_apply_runs_nmcli_writes_psk_and_reservations(box):
    done = box.run(FLAG)
    assert done.returncode == 0, done.stderr
    psk = box.psk.read_text().strip()
    assert 8 <= len(psk) <= 63 and box.psk.stat().st_mode & 0o777 == 0o600
    assert psk not in done.stdout + done.stderr  # never printed
    calls = box.calls()
    add = [c for c in calls if c.startswith("--offline connection add")]
    assert len(add) == 1
    for part in ("type wifi", "ssid MIA-Car", "802-11-wireless.mode ap", "ipv4.method shared", "wifi-sec.key-mgmt wpa-psk"):
        assert part in add[0]
    assert "connection reload" in calls and any(c.startswith("connection up MIA-Car") for c in calls)
    assert not any(c.startswith("connection add") for c in calls)  # nothing is added to the live NM state by argv
    fragment = (box.dnsmasq / "mia-phones.conf").read_text()
    lines = [ln for ln in fragment.splitlines() if ln.startswith("dhcp-host=")]
    assert len(lines) == 1 and lines[0].startswith(f"dhcp-host={MAC},192.168.4.")


def test_the_passphrase_is_never_an_argument_and_the_keyfile_is_root_only(box):
    assert box.run(FLAG).returncode == 0
    psk = box.psk.read_text().strip()
    assert all(psk not in call for call in box.calls())  # never in the nmcli argv, so never in `ps`
    assert box.keyfile.stat().st_mode & 0o777 == 0o600
    text = box.keyfile.read_text()
    assert f"psk={psk}" in text and text.count("psk=") == 1
    assert [p.name for p in box.keyfile.parent.iterdir()] == ["MIA-Car.nmconnection"]  # no temp file left behind
    dry = box.run(FLAG, "--dry-run")
    assert psk not in dry.stdout + dry.stderr


@needs_offline_nmcli
def test_real_nmcli_offline_renders_the_hotspot_keyfile(tmp_path):
    box = Box(tmp_path, use_real_offline=True)
    done = box.run(FLAG)
    assert done.returncode == 0, done.stderr
    text = box.keyfile.read_text()
    assert box.keyfile.stat().st_mode & 0o777 == 0o600
    for line in ("id=MIA-Car", "type=wifi", "mode=ap", "ssid=MIA-Car", "key-mgmt=wpa-psk", "method=shared"):
        assert line in text.splitlines(), line
    assert f"psk={box.psk.read_text().strip()}" in text.splitlines()
    assert all(box.psk.read_text().strip() not in call for call in box.calls())


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
    assert "connection reload" in calls and not any(c.startswith("connection delete") for c in calls)
    assert not (box.dnsmasq / "mia-phones.conf").exists() and not box.keyfile.exists()


def test_disable_dry_run_changes_nothing(box):
    box.run(FLAG)
    box.log.unlink()
    done = box.run("--disable", "--dry-run")
    assert done.returncode == 0 and "connection down MIA-Car" in done.stdout and "rm -f" in done.stdout
    assert box.calls() == [] and (box.dnsmasq / "mia-phones.conf").exists() and box.keyfile.exists()


def _write_phones(box, entries):
    box.phones.write_text(json.dumps({"version": 1, "phones": entries}))


GOOD_FP = _fp("good")
EVIL = {
    "newline": "aa:bb:cc:00:11:22\ndhcp-option=6,6.6.6.6\naddn-hosts=/etc/passwd",
    "comma": "aa:bb:cc:00:11:22,192.168.4.99,set:evil",
    "trailing-newline": "aa:bb:cc:00:11:22\n",
    "short": "aa:bb:cc:00:11",
    "non-hex": "zz:bb:cc:00:11:22",
    "not-a-string": ["aa:bb:cc:00:11:22"],
}


@pytest.mark.parametrize("dry", [True, False])
@pytest.mark.parametrize("name", sorted(EVIL))
def test_an_invalid_mac_in_the_registry_is_never_emitted(box, name, dry):
    _write_phones(box, {_fp("evil"): {"mac": EVIL[name], "bonded": False, "updated": 1},
                        GOOD_FP: {"mac": "AA:BB:CC:00:11:33", "bonded": True, "updated": 1}})
    done = box.run(FLAG, *(["--dry-run"] if dry else []))
    assert done.returncode == 0, done.stderr
    emitted = done.stdout if dry else (box.dnsmasq / "mia-phones.conf").read_text()
    assert "dhcp-option" not in emitted and "addn-hosts" not in emitted and "6.6.6.6" not in emitted
    assert "192.168.4.99" not in emitted and "set:evil" not in emitted
    hosts = [ln for ln in emitted.splitlines() if ln.startswith("dhcp-host=")]
    assert len(hosts) == 1 and hosts[0].startswith("dhcp-host=aa:bb:cc:00:11:33,192.168.4.")  # lowercased
    assert "warning" in done.stderr and "skipped" in done.stderr
    assert "dhcp-option" not in done.stderr and "addn-hosts" not in done.stderr  # raw strings are not echoed either
    if not dry:
        assert all(ln.startswith(("#", "dhcp-host=")) for ln in emitted.splitlines())


@pytest.mark.parametrize("bad_fp", ["SHA256:short", "SHA256:" + "A" * 43 + "\ndhcp-option=6,1.1.1.1", "not-a-fingerprint"])
def test_an_invalid_fingerprint_in_the_registry_is_skipped(box, bad_fp):
    _write_phones(box, {bad_fp: {"mac": MAC, "bonded": False, "updated": 1}})
    done = box.run(FLAG)
    assert done.returncode == 0, done.stderr
    assert "dhcp-host=" not in (box.dnsmasq / "mia-phones.conf").read_text() and "skipped" in done.stderr


@pytest.mark.skipif(shutil.which("dnsmasq") is None, reason="dnsmasq not installed")
def test_the_generated_fragment_passes_dnsmasq_test(box):
    _write_phones(box, {_fp("evil"): {"mac": EVIL["newline"], "bonded": False, "updated": 1},
                        GOOD_FP: {"mac": MAC, "bonded": True, "updated": 1}, _fp("b"): {"mac": "aa:bb:cc:00:11:44", "bonded": False, "updated": 1}})
    assert box.run(FLAG).returncode == 0
    fragment = box.dnsmasq / "mia-phones.conf"
    done = subprocess.run(["dnsmasq", "--test", f"--conf-file={fragment}"], capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    assert "syntax check OK" in done.stderr + done.stdout


def test_shellcheck_clean():
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck not installed")
    done = subprocess.run(["shellcheck", str(SCRIPT)], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout
