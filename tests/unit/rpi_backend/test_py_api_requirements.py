"""The Pi API's requirements file must install everything mia-api needs to start.

CI installs requirements-ci.txt, which already has these packages, so a missing
entry in apps/rpi-backend/py-api/requirements.txt only shows up on a Pi set up
from that file (README "Manual Setup"): mia-api restart-loops because FastAPI
refuses to register Form/File routes without python-multipart.
"""

import ast
import re
import sys
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

pytestmark = pytest.mark.req("REQ-DEP-003")

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_API = REPO_ROOT / "apps" / "rpi-backend" / "py-api"
REQUIREMENTS = PY_API / "requirements.txt"

# Import name -> distribution name, for modules api/main.py imports at startup.
DISTRIBUTION = {
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "psutil": "psutil",
    "yaml": "pyyaml",
    "zmq": "pyzmq",
}
# Packages that ship with the repo rather than from PyPI.
LOCAL = {"api", "core", "services", "hardware", "shared", "Mia"}


def _requirements():
    reqs = {}
    for line in REQUIREMENTS.read_text().splitlines():
        line = line.split(" #", 1)[0].strip()
        if line and not line.startswith(("#", "-")):
            req = Requirement(line)
            reqs[canonicalize_name(req.name)] = req
    return reqs


def _startup_imports(path):
    """Top-level names imported unconditionally at module level (not inside try/if)."""
    names = set()
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return {n for n in names if n not in sys.stdlib_module_names and n not in LOCAL}


def test_startup_imports_of_api_main_are_listed():
    reqs = _requirements()
    imports = _startup_imports(PY_API / "api" / "main.py")
    unmapped = imports - DISTRIBUTION.keys()
    assert not unmapped, f"add the distribution name for {sorted(unmapped)} to DISTRIBUTION"
    missing = sorted(DISTRIBUTION[name] for name in imports if canonicalize_name(DISTRIBUTION[name]) not in reqs)
    assert not missing, f"{REQUIREMENTS.relative_to(REPO_ROOT)} is missing {missing}"


def test_form_and_upload_routes_have_python_multipart():
    form_routes = [
        p.relative_to(PY_API)
        for p in (PY_API / "api").rglob("*.py")
        if re.search(r"\b(UploadFile|Form\(|File\()", p.read_text())
    ]
    assert form_routes, "no Form/File routes left; drop this test and the python-multipart pin"
    assert "python-multipart" in _requirements(), f"python-multipart is required by {form_routes}"


@pytest.mark.parametrize("package", ["rpi-gpio", "gpiozero"])
def test_gpio_libraries_install_on_raspberry_pi_os_only(package):
    marker = _requirements()[package].marker
    assert marker is not None, f"{package} must stay limited to the Pi"
    for machine in ("aarch64", "armv7l", "armv6l"):  # 64-bit Pi OS, then 32-bit
        assert marker.evaluate({"platform_machine": machine}), f"{package} not installed on {machine}"
    assert not marker.evaluate({"platform_machine": "x86_64"}), f"{package} would install on x86_64"
