"""infra/deploy/rpi/install-update-access.sh and deploy-raspberry-pi.sh --skip-packages (REQ-UPD-004, REQ-UPD-001)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.req("REQ-UPD-004", "REQ-UPD-001"), pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")]

ROOT = Path(__file__).resolve().parents[3]
ACCESS = ROOT / "infra" / "deploy" / "rpi" / "install-update-access.sh"
DEPLOY = ROOT / "tools" / "scripts" / "deploy-raspberry-pi.sh"


def _shims(tmp_path, names):
    shim_dir = tmp_path / "shims"
    shim_dir.mkdir()
    log = tmp_path / "calls.log"
    for name in names:
        shim = shim_dir / name
        shim.write_text(f'#!/bin/bash\necho "{name} $*" >> "{log}"\n[ "{name}" = id ] && exit 1\nexit 0\n')
        shim.chmod(0o755)
    return shim_dir, log


def test_the_access_installer_writes_a_one_command_sudoers_rule(tmp_path):
    shim_dir, log = _shims(tmp_path, ["useradd", "passwd", "chown", "id", "sshd"])
    # visudo -cf is the real syntax check where sudo is installed; a shim stands in elsewhere.
    if shutil.which("visudo") is None:
        (shim_dir / "visudo").write_text("#!/bin/bash\nexit 0\n")
        (shim_dir / "visudo").chmod(0o755)
    env = {
        "PATH": f"{shim_dir}{os.pathsep}{os.environ['PATH']}",
        "MIA_SUDOERS_FILE": str(tmp_path / "sudoers.d" / "mia-update"),
        "MIA_SSHD_DROPIN": str(tmp_path / "sshd_config.d" / "mia-update.conf"),
        "MIA_AUTHORIZED_KEYS": str(tmp_path / "mia" / "update_authorized_keys"),
        "MIA_UPDATE_TOOL": "/opt/mia/bin/mia-apply-update",
    }
    (tmp_path / "sudoers.d").mkdir()
    done = subprocess.run(["bash", str(ACCESS)], env=env, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "sudoers.d" / "mia-update").read_text() == 'mia-update ALL=(root) NOPASSWD: /opt/mia/bin/mia-apply-update ""\n'
    sshd = (tmp_path / "sshd_config.d" / "mia-update.conf").read_text()
    assert "Match User mia-update" in sshd and "PermitTTY no" in sshd and "AllowTcpForwarding no" in sshd
    assert "useradd -r -m -s /bin/sh mia-update" in log.read_text()
    # Root-owned, world-readable: the service user and the API can read the list but never change it.
    assert (tmp_path / "mia" / "update_authorized_keys").stat().st_mode & 0o777 == 0o644
    assert "chown root:root" in log.read_text()
    assert "AuthorizedKeysCommandUser nobody" in sshd
    assert "ForceCommand /usr/bin/sudo /opt/mia/bin/mia-apply-update" in sshd and "PermitUserRC no" in sshd
    assert "ssh-rsa" not in sshd and "PubkeyAcceptedAlgorithms ssh-ed25519" in sshd
    # Everything is scoped to the one Match block: nothing may sit before it and no second Match may follow.
    lines = [ln for ln in sshd.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert lines[0] == "Match User mia-update"
    assert all(ln.startswith("    ") for ln in lines[1:])
    assert sum(ln.startswith("Match ") for ln in lines) == 1


def test_skip_packages_leaves_apt_and_pip_alone_and_installs_the_update_tool(tmp_path):
    shim_dir, log = _shims(tmp_path, ["apt-get", "systemctl", "useradd", "usermod", "chown"])
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("# nothing\n")
    install = tmp_path / "opt" / "mia"
    env = {
        "PATH": f"{shim_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "MIA_USE_SUDO": "0",
        "MIA_INSTALL_DIR": str(install),
        "MIA_SYSTEMD_DIR": str(tmp_path / "systemd"),
        "MIA_ENV_FILE": str(tmp_path / "etc" / "environment"),
        "MIA_PYTHON_WRAPPER": str(tmp_path / "bin" / "mia-python"),
        "MIA_BASE_PYTHON": sys.executable,
        "MIA_PY_REQUIREMENTS": str(requirements),
        "MIA_USER": "mia-install-test",
    }
    done = subprocess.run(
        ["bash", str(DEPLOY), "--skip-packages"], input="y\n", env=env, capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 0, done.stderr + done.stdout
    assert "apt-get" not in log.read_text()
    assert not (install / "venv").exists()
    tool = install / "bin" / "mia-apply-update"
    assert tool.is_file() and tool.stat().st_mode & 0o777 == 0o755
    assert tool.read_bytes() == (ROOT / "bin" / "mia-apply-update").read_bytes()
    pair = install / "bin" / "mia-update-pair"
    assert pair.is_file() and pair.stat().st_mode & 0o777 == 0o755


def test_an_unknown_option_is_refused():
    done = subprocess.run(["bash", str(DEPLOY), "--bogus"], capture_output=True, text=True, timeout=30)
    assert done.returncode == 2
