"""infra/deploy/rpi/install-enroll-access.sh (REQ-ONB-004)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.req("REQ-ONB-004"), pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")]

ACCESS = Path(__file__).resolve().parents[3] / "infra" / "deploy" / "rpi" / "install-enroll-access.sh"
KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIGJzdGVzdGtleWJ5dGVzMDEyMzQ1Njc4OWFiY2RlZg"


def _install(tmp_path):
    shim_dir = tmp_path / "shims"
    shim_dir.mkdir()
    log = tmp_path / "calls.log"
    for name in ("useradd", "passwd", "chown", "id", "sshd"):
        shim = shim_dir / name
        shim.write_text(f'#!/bin/bash\necho "{name} $*" >> "{log}"\n[ "{name}" = id ] && exit 1\nexit 0\n')
        shim.chmod(0o755)
    if shutil.which("visudo") is None:
        (shim_dir / "visudo").write_text("#!/bin/bash\nexit 0\n")
        (shim_dir / "visudo").chmod(0o755)
    env = {
        "PATH": f"{shim_dir}{os.pathsep}{os.environ['PATH']}",
        "MIA_ENROLL_SUDOERS_FILE": str(tmp_path / "sudoers.d" / "mia-enroll"),
        "MIA_ENROLL_SSHD_DROPIN": str(tmp_path / "sshd_config.d" / "mia-enroll.conf"),
        "MIA_ENROLL_KEYS_CMD": str(tmp_path / "sbin" / "mia-enroll-authkeys"),
        "MIA_ENROLL_TOOL": "/opt/mia/bin/mia-enroll",
    }
    (tmp_path / "sudoers.d").mkdir()
    done = subprocess.run(["bash", str(ACCESS)], env=env, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return log


def test_the_installer_writes_a_one_command_sudoers_rule_and_one_match_block(tmp_path):
    log = _install(tmp_path)
    assert (tmp_path / "sudoers.d" / "mia-enroll").read_text() == 'mia-enroll ALL=(root) NOPASSWD: /opt/mia/bin/mia-enroll ""\n'
    assert "useradd -r -m -s /bin/sh mia-enroll" in log.read_text()
    sshd = (tmp_path / "sshd_config.d" / "mia-enroll.conf").read_text()
    assert f"AuthorizedKeysCommand {tmp_path}/sbin/mia-enroll-authkeys %t %k" in sshd
    assert "AuthorizedKeysCommandUser nobody" in sshd and "ForceCommand /usr/bin/sudo /opt/mia/bin/mia-enroll" in sshd
    assert "PermitTTY no" in sshd and "AllowTcpForwarding no" in sshd and "PermitUserRC no" in sshd
    assert "ssh-rsa" not in sshd and "PubkeyAcceptedAlgorithms ssh-ed25519" in sshd
    lines = [ln for ln in sshd.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert lines[0] == "Match User mia-enroll"
    assert all(ln.startswith("    ") for ln in lines[1:])
    assert sum(ln.startswith("Match ") for ln in lines) == 1


def test_the_key_helper_emits_the_forced_command_for_ed25519_and_ecdsa_only(tmp_path):
    _install(tmp_path)
    helper = tmp_path / "sbin" / "mia-enroll-authkeys"
    assert helper.stat().st_mode & 0o777 == 0o755

    def run(*args):
        return subprocess.run([str(helper), *args], capture_output=True, text=True, timeout=10).stdout

    out = run("ssh-ed25519", KEY)
    assert out.startswith('restrict,command="sudo /opt/mia/bin/mia-enroll"')
    assert out.endswith(f" ssh-ed25519 {KEY}\n") and out.count("\n") == 1
    assert run("ecdsa-sha2-nistp256", KEY).startswith('restrict,command="sudo /opt/mia/bin/mia-enroll"')
    assert run("ssh-rsa", KEY) == "" and run("ssh-ed25519", "") == ""
    assert run("ssh-ed25519", KEY + '" command="/bin/sh') == ""
    assert run("ssh-ed25519", KEY + "\nssh-ed25519 AAAA") == ""
