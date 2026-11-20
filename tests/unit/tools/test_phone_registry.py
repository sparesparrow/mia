"""bin/mia-phone-registry: phones keyed by key fingerprint; a MAC is only a DHCP reservation hint (REQ-ONB-007)."""

from __future__ import annotations

import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.req("REQ-ONB-007")

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "bin" / "mia-phone-registry"
PAIR = ROOT / "bin" / "mia-update-pair"


def _fp(seed: str) -> str:
    digest = hashlib.sha256(seed.encode()).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


FP_A, FP_B = _fp("phone-a"), _fp("phone-b")
MAC_1, MAC_2 = "aa:bb:cc:00:11:22", "aa:bb:cc:00:11:33"


def _load():
    loader = importlib.machinery.SourceFileLoader("mia_phone_registry", str(TOOL))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("mia_phone_registry", loader))
    loader.exec_module(mod)
    return mod


@pytest.fixture
def reg(tmp_path, monkeypatch):
    monkeypatch.setenv("MIA_PHONES_FILE", str(tmp_path / "state" / "phones.json"))
    return _load()


def _store(tmp_path) -> Path:
    return tmp_path / "state" / "phones.json"


def test_upsert_new_phone(reg, tmp_path):
    reg.upsert(FP_A, MAC_1, False)
    entry = reg.lookup_by_fp(FP_A)
    assert (entry.phone_fp, entry.mac, entry.bonded) == (FP_A, MAC_1, False)
    assert reg.lookup_by_fp(FP_B) is None
    assert FP_A in json.loads(_store(tmp_path).read_text())["phones"]


def test_mac_change_updates_same_entry(reg, tmp_path):
    reg.upsert(FP_A, MAC_1, False)
    reg.upsert(FP_A, MAC_2.upper(), True)  # Android randomized the MAC; upper case is normalized
    phones = json.loads(_store(tmp_path).read_text())["phones"]
    assert list(phones) == [FP_A]
    entry = reg.lookup_by_fp(FP_A)
    assert (entry.mac, entry.bonded) == (MAC_2, True)
    assert MAC_1 not in _store(tmp_path).read_text()  # the old MAC is gone, not kept as a second identity


def test_empty_mac_keeps_a_known_one(reg):
    reg.upsert(FP_A, MAC_1, False)
    reg.upsert(FP_A, "", False)
    assert reg.lookup_by_fp(FP_A).mac == MAC_1


def test_a_mac_belongs_to_one_phone(reg):
    reg.upsert(FP_A, MAC_1, False)
    reg.upsert(FP_B, MAC_1, False)  # one reservation per MAC: the later phone wins
    assert reg.lookup_by_fp(FP_B).mac == MAC_1
    assert reg.lookup_by_fp(FP_A).mac == ""


def test_unknown_mac_not_trusted(reg):
    reg.upsert(FP_A, MAC_1, True)
    assert reg.lookup_by_fp(MAC_1) is None  # a MAC is not a key fingerprint
    assert reg.lookup_by_fp(MAC_2) is None
    assert not [n for n in dir(reg) if "mac" in n.lower() and callable(getattr(reg, n)) and n.startswith(("lookup", "auth", "trust"))]


@pytest.mark.parametrize("fp", ["", "SHA256:short", "MD5:aa:bb", FP_A + "x", FP_A.replace("SHA256:", "sha256:"), "SHA256:" + "!" * 43, 7])
def test_invalid_fingerprint_refused(reg, tmp_path, fp):
    with pytest.raises(reg.RegistryError):
        reg.upsert(fp, MAC_1, False)
    assert not _store(tmp_path).exists()


@pytest.mark.parametrize("mac", ["aa:bb:cc:00:11", "aa-bb-cc-00-11-22", "zz:bb:cc:00:11:22", "aa:bb:cc:00:11:22:33", " aa:bb:cc:00:11:22", 5])
def test_invalid_mac_refused(reg, tmp_path, mac):
    with pytest.raises(reg.RegistryError):
        reg.upsert(FP_A, mac, False)
    assert not _store(tmp_path).exists()


def test_invalid_bonded_refused(reg):
    with pytest.raises(reg.RegistryError):
        reg.upsert(FP_A, MAC_1, "yes")


def test_store_is_mode_600(reg, tmp_path):
    reg.upsert(FP_A, MAC_1, False)
    reg.upsert(FP_B, MAC_2, True)
    assert _store(tmp_path).stat().st_mode & 0o777 == 0o600


def test_write_is_atomic(reg, tmp_path, monkeypatch):
    reg.upsert(FP_A, MAC_1, False)
    before = _store(tmp_path).read_text()

    def boom(src, dst):
        raise OSError(5, "simulated crash before rename")

    monkeypatch.setattr(reg.os, "replace", boom)
    with pytest.raises(OSError):
        reg.upsert(FP_B, MAC_2, True)
    monkeypatch.undo()
    assert _store(tmp_path).read_text() == before  # the old file is intact
    assert sorted(p.name for p in _store(tmp_path).parent.iterdir()) == ["phones.json", "phones.json.lock"]  # no temp left over


def test_corrupt_store_is_refused_not_overwritten(reg, tmp_path):
    _store(tmp_path).parent.mkdir(parents=True)
    _store(tmp_path).write_text("{not json")
    with pytest.raises(reg.RegistryError):
        reg.upsert(FP_A, MAC_1, False)
    assert _store(tmp_path).read_text() == "{not json"


def test_remove_works(reg):
    reg.upsert(FP_A, MAC_1, False)
    reg.upsert(FP_B, MAC_2, False)
    assert reg.remove(FP_A) is True
    assert reg.lookup_by_fp(FP_A) is None and reg.lookup_by_fp(FP_B) is not None
    assert reg.remove(FP_A) is False
    with pytest.raises(reg.RegistryError):
        reg.remove("nope")


# --- CLI and revocation ---------------------------------------------------------------------------------------------


def _cli(tmp_path, *args, extra=None):
    env = {
        "PATH": os.environ["PATH"],
        "MIA_PHONES_FILE": str(_store(tmp_path)),
        "MIA_PAIR_TOOL": str(PAIR),
        "MIA_AUTHORIZED_KEYS": str(tmp_path / "update_authorized_keys"),
        "MIA_ENROLL_SKIP_CHOWN": "1",
    }
    env.update(extra or {})
    return subprocess.run([sys.executable, str(TOOL), *args], env=env, capture_output=True, text=True, timeout=60)


def test_cli_upsert_list_remove(tmp_path):
    assert _cli(tmp_path, "upsert", FP_A, "--mac", MAC_1, "--bonded").returncode == 0
    listed = _cli(tmp_path, "list")
    assert listed.returncode == 0 and FP_A in listed.stdout and MAC_1 in listed.stdout and "bonded" in listed.stdout
    assert _cli(tmp_path, "upsert", FP_A, "--mac", "bad").returncode == 1
    assert _cli(tmp_path, "upsert", "bad").returncode == 1
    assert _cli(tmp_path, "remove", FP_A).returncode == 0
    assert FP_A not in _cli(tmp_path, "list").stdout
    assert _cli(tmp_path, "frobnicate").returncode == 2


def _keygen(tmp_path):
    key = tmp_path / "k"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "t", "-f", str(key)], check=True)
    pub = Path(str(key) + ".pub").read_text().strip()
    fp = subprocess.run(["ssh-keygen", "-lf", str(key) + ".pub"], check=True, capture_output=True, text=True).stdout.split()[1]
    return pub, fp


def test_remove_also_removes_the_update_pair_key(tmp_path):
    pair = importlib.machinery.SourceFileLoader("mia_update_pair", str(PAIR)).load_module()
    pub, fp = _keygen(tmp_path)
    _, body = pair.parse_public_key(pub)
    label = "phone-" + hashlib.sha256(base64.b64decode(body)).hexdigest()[:12]
    keys = tmp_path / "update_authorized_keys"
    pair._chown_root = lambda path: None
    pair.add(keys, label, pub)
    assert label in keys.read_text()
    assert _cli(tmp_path, "upsert", fp, "--mac", MAC_1).returncode == 0
    done = _cli(tmp_path, "remove", fp)
    assert done.returncode == 0, done.stderr
    assert label not in keys.read_text()
    assert fp not in _cli(tmp_path, "list").stdout


def test_cli_never_prints_the_environment_or_keys(tmp_path):
    done = _cli(tmp_path, "upsert", FP_A, "--mac", MAC_1, extra={"MIA_API_KEY": "s3cret-value"})
    assert "s3cret-value" not in done.stdout + done.stderr


# --- root boundary (I-1) ---------------------------------------------------------------------------------------------


def test_default_store_is_in_the_root_owned_enroll_directory(reg):
    assert reg.DEFAULT_STORE == "/var/lib/mia-enroll/phones.json"


def test_registry_refuses_a_symlinked_lock(reg, tmp_path):
    victim = tmp_path / "victim"
    victim.write_text("precious")
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "phones.json.lock").symlink_to(victim)
    with pytest.raises(reg.RegistryError):
        reg.upsert(FP_A, MAC_1, False)
    assert victim.read_text() == "precious"


def test_registry_ensure_dir_refuses_symlink_and_foreign_owner(reg, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(reg.RegistryError):
        reg.ensure_dir(link, 0o700, os.getuid())
    with pytest.raises(reg.RegistryError):
        reg.ensure_dir(real, 0o700, os.getuid() + 1)
    reg.ensure_dir(real, 0o700, None)


def test_registry_file_mode_is_set_by_fchmod_before_writing(reg, tmp_path, monkeypatch):
    seen = []
    real_fchmod = os.fchmod
    monkeypatch.setattr(os, "fchmod", lambda fd, m: (seen.append((m, os.fstat(fd).st_size)), real_fchmod(fd, m))[1])
    monkeypatch.setattr(os, "chmod", lambda *a, **k: (_ for _ in ()).throw(AssertionError("chmod by path")))
    reg.upsert(FP_A, MAC_1, False)
    assert (0o600, 0) in seen
    assert _store(tmp_path).stat().st_mode & 0o777 == 0o600
