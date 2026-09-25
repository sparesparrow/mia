"""The API must load its generated bindings with the PYTHONPATH its systemd unit sets.

A plain pytest import cannot catch this: tests/conftest.py puts extra source
roots on sys.path. Before schemas/generated/python was resolved from main.py,
mia-api on the Pi silently ran with "Telemetry decoding disabled".
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PY_API = REPO_ROOT / "apps" / "rpi-backend" / "py-api"
UNIT = REPO_ROOT / "infra" / "systemd" / "mia-api.service"


def _unit_pythonpath():
    match = re.search(r"^Environment=PYTHONPATH=(.+)$", UNIT.read_text(), re.MULTILINE)
    assert match, "mia-api.service no longer sets PYTHONPATH"
    return match.group(1).replace("/opt/mia", str(REPO_ROOT))


def test_api_imports_generated_bindings_under_the_systemd_pythonpath():
    code = (
        "import api.main as m; "
        "print(m.parse_citroen_telemetry is not None, m.validate_cycle1_envelope is not None)"
    )
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "PYTHONPATH": _unit_pythonpath()}
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PY_API, env=env, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().splitlines()[-1] == "True True", result.stderr[-2000:]
