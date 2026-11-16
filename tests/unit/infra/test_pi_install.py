"""The on-Pi install, tools/scripts/deploy-raspberry-pi.sh, run in a temporary directory (REQ-DEP-008).

Shims on PATH stand in for apt-get, systemctl, useradd, usermod and chown and log their arguments. The venv is
real: the script creates it from this interpreter, with a requirements file that names nothing, so nothing is
downloaded. The script runs twice, as a re-deploy would, then a third time with a `cat` that cannot read the
environment file.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

pytestmark = [
    pytest.mark.req("REQ-DEP-008"),
    pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash"),
]

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SCRIPTS = REPO_ROOT / "tools" / "scripts"
INSTALL_SCRIPT = SCRIPTS / "deploy-raspberry-pi.sh"
ON_PI_SCRIPTS = [
    INSTALL_SCRIPT,
    SCRIPTS / "deploy-production-rpi.sh",
    SCRIPTS / "setup-ble-service.sh",
]
SHIMMED = ("apt-get", "systemctl", "useradd", "usermod", "chown")
CORE_UNITS = (
    "zmq-broker.service",
    "mia-api.service",
    "mia-gpio-worker.service",
    "mia-serial-bridge.service",
    "mia-obd-worker.service",
)
API_KEY = "MIA_API_KEY=mia_api_0123456789abcdef"


@pytest.fixture(scope="module")
def pi(tmp_path_factory):
    root = tmp_path_factory.mktemp("pi")
    shim_dir = root / "shims"
    shim_dir.mkdir()
    calls = root / "calls.log"
    for name in SHIMMED:
        shim = shim_dir / name
        shim.write_text(f'#!/bin/bash\necho "{name} $*" >> "{calls}"\n')
        shim.chmod(0o755)

    requirements = root / "requirements.txt"
    requirements.write_text("# nothing to download\n")
    env_file = root / "etc" / "mia" / "environment"
    env_file.parent.mkdir(parents=True)
    # What step 2 of the install page writes, plus what an earlier bundled-CPython run left behind.
    env_file.write_text(
        f"{API_KEY}\nPYTHONHOME=/opt/mia/rpi\nMIA_PYTHON=/opt/mia/rpi/bin/python3\n"
    )

    # The script's work directory, which holds a copy of the environment file, lands here and must not stay.
    tmpdir = root / "tmp"
    tmpdir.mkdir()

    install_dir = root / "opt" / "mia"
    systemd_dir = root / "systemd"
    wrapper = root / "usr" / "local" / "bin" / "mia-python"
    env = {
        "PATH": f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "HOME": str(root),
        "TMPDIR": str(tmpdir),
        "MIA_USE_SUDO": "0",
        "MIA_INSTALL_DIR": str(install_dir),
        "MIA_SYSTEMD_DIR": str(systemd_dir),
        "MIA_ENV_FILE": str(env_file),
        "MIA_PYTHON_WRAPPER": str(wrapper),
        "MIA_BASE_PYTHON": sys.executable,
        "MIA_PY_REQUIREMENTS": str(requirements),
        "MIA_USER": "mia-install-test",
    }

    def install(run_env):
        return subprocess.run(
            ["bash", str(INSTALL_SCRIPT)],
            input="y\n",  # "designed for Raspberry Pi, continue anyway?"
            env=run_env,
            capture_output=True,
            text=True,
            timeout=300,
        )

    runs = [install(env) for _ in range(2)]
    leftovers_after_success = sorted(p.name for p in tmpdir.iterdir())

    # A read of the environment file that fails, as an unreadable file or a refused sudo would.
    failing_dir = root / "failing-cat"
    failing_dir.mkdir()
    failing_cat = failing_dir / "cat"
    failing_cat.write_text(
        f'#!/bin/bash\n[ "$1" = "{env_file}" ] && {{ echo "cat: permission denied" >&2; exit 1; }}\n'
        'exec /bin/cat "$@"\n'
    )
    failing_cat.chmod(0o755)
    env_before_failure = env_file.read_text()
    failed = install({**env, "PATH": f"{failing_dir}{os.pathsep}{env['PATH']}"})

    return SimpleNamespace(
        runs=runs,
        failed=failed,
        env_before_failure=env_before_failure,
        leftovers_after_success=leftovers_after_success,
        leftovers_after_failure=sorted(p.name for p in tmpdir.iterdir()),
        install=install_dir,
        venv=install_dir / "venv",
        systemd=systemd_dir,
        env_file=env_file,
        wrapper=wrapper,
        calls=calls.read_text() if calls.exists() else "",
    )


def _on_pi(path: str, pi) -> Path:
    """A path as a unit names it (under /opt/mia), moved into the temporary install."""
    return Path(path.replace("/opt/mia", str(pi.install), 1))


def _unit_fields(unit: Path):
    fields = {}
    for line in unit.read_text().splitlines():
        if "=" in line and not line.startswith(("#", ";")):
            key, value = line.split("=", 1)
            fields.setdefault(key.strip(), []).append(value.strip())
    return fields


def test_install_and_reinstall_succeed(pi):
    for number, run in enumerate(pi.runs, 1):
        assert (
            run.returncode == 0
        ), f"run {number}:\n{run.stdout[-3000:]}\n{run.stderr[-3000:]}"


def test_a_reinstall_keeps_the_venv(pi):
    assert "Creating" in pi.runs[0].stdout
    assert "Creating" not in pi.runs[1].stdout


@pytest.mark.parametrize("unit", CORE_UNITS)
def test_every_path_an_installed_unit_names_exists(pi, unit):
    installed = pi.systemd / unit
    assert installed.is_file(), f"{unit} was not installed"
    fields = _unit_fields(installed)
    workdir = _on_pi(fields["WorkingDirectory"][0], pi)
    assert workdir.is_dir(), workdir

    for env in fields.get("Environment", []):
        if env.startswith("PYTHONPATH="):
            for entry in env.split("=", 1)[1].split(":"):
                assert _on_pi(entry, pi).is_dir(), entry

    exec_start = fields["ExecStart"][0]
    scripts = re.findall(r"(\S+\.py)\b", exec_start)
    modules = re.findall(r"-m uvicorn (\S+):", exec_start)
    assert scripts or modules, exec_start
    for script in scripts:
        target = _on_pi(script, pi) if script.startswith("/") else workdir / script
        assert target.is_file(), f"{unit}: {script}"
    for module in modules:
        assert (
            workdir / (module.replace(".", "/") + ".py")
        ).is_file(), f"{unit}: {module}"


def test_the_generated_bindings_are_where_the_code_looks(pi):
    assert (pi.install / "schemas" / "generated" / "python" / "MiaVoice").is_dir()


def test_the_installed_api_imports_under_the_unit_pythonpath(pi):
    """The copied tree is complete: api.main and its generated bindings load from the install, not the checkout."""
    py_api = pi.install / "apps" / "rpi-backend" / "py-api"
    code = (
        "import api.main as m; "
        "print(m.__file__); "
        "print(m.parse_citroen_telemetry is not None, m.validate_cycle1_envelope is not None)"
    )
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": str(py_api),
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=py_api,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    lines = result.stdout.strip().splitlines()
    assert Path(lines[-2]).resolve().is_relative_to(pi.install.resolve())
    assert lines[-1] == "True True", result.stderr[-2000:]


def test_the_wrapper_and_mia_python_run_the_venv(pi):
    mode = pi.wrapper.stat().st_mode
    assert mode & stat.S_IXUSR
    prefix = subprocess.run(
        [str(pi.wrapper), "-c", "import sys; print(sys.prefix)"],
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert prefix.returncode == 0, prefix.stderr
    assert Path(prefix.stdout.strip()).resolve() == pi.venv.resolve()

    lines = pi.env_file.read_text().splitlines()
    assert lines.count(f"MIA_PYTHON={pi.venv}/bin/python") == 1
    assert Path(f"{pi.venv}/bin/python").is_file()


def test_the_environment_file_keeps_the_api_key_and_drops_pythonhome(pi):
    lines = pi.env_file.read_text().splitlines()
    assert API_KEY in lines
    assert not any(line.startswith("PYTHONHOME=") for line in lines)
    assert [line for line in lines if line.startswith("MIA_PYTHON=")] == [
        f"MIA_PYTHON={pi.venv}/bin/python"
    ]
    assert stat.S_IMODE(pi.env_file.stat().st_mode) == 0o600


def test_the_core_units_are_enabled_and_systemd_reloaded(pi):
    assert "systemctl daemon-reload" in pi.calls
    assert f"systemctl enable {' '.join(CORE_UNITS)}" in pi.calls


def test_the_service_user_is_created_and_owns_the_data_directory(pi):
    # A login shell, as setup-ble-service.sh gives it: the repo's tools SSH in as mia@<pi> and run sudo.
    assert re.search(
        r"^useradd -r -m -s /bin/bash .*mia-install-test$", pi.calls, re.MULTILINE
    )
    assert f"chown mia-install-test:mia-install-test {pi.install}/data" in pi.calls


@pytest.mark.parametrize("script", ON_PI_SCRIPTS, ids=lambda p: p.name)
def test_on_pi_scripts_parse(script):
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("script", ON_PI_SCRIPTS, ids=lambda p: p.name)
def test_no_on_pi_script_installs_into_the_system_python(script):
    text = script.read_text()
    assert "--break-system-packages" not in text
    for line in text.splitlines():
        if re.search(r"\bpip3? install", line):
            assert (
                '"$VENV_DIR/bin/python" -m pip install' in line
            ), f"packages go into the venv: {line.strip()}"


def test_the_install_takes_the_apis_own_requirements():
    text = INSTALL_SCRIPT.read_text()
    assert (
        "MIA_PY_REQUIREMENTS:-$PROJECT_ROOT/apps/rpi-backend/py-api/requirements.txt"
        in text
    )
    assert "$PROJECT_ROOT/requirements.txt" not in text


def test_a_failed_read_of_the_environment_file_stops_the_install_and_keeps_the_key(pi):
    assert pi.failed.returncode != 0, pi.failed.stdout[-2000:]
    assert "permission denied" in pi.failed.stderr
    assert pi.env_file.read_text() == pi.env_before_failure
    assert API_KEY in pi.env_file.read_text().splitlines()


def test_no_copy_of_the_environment_file_is_left_behind(pi):
    assert pi.leftovers_after_success == []
    assert pi.leftovers_after_failure == []


def test_ci_keeps_the_aarch64_install_check_this_requirement_cites():
    """REQ-DEP-008 cites the "Pi Python (aarch64)" job; this keeps the job, not its result, which CI shows."""
    job = yaml.safe_load(CI_WORKFLOW.read_text())["jobs"]["pi-python"]
    assert job["runs-on"] == "ubuntu-24.04-arm"
    assert {"3.11", "3.13"} <= set(job["strategy"]["matrix"]["python"])
    script = "\n".join(step.get("run", "") for step in job["steps"])
    assert "-r apps/rpi-backend/py-api/requirements.txt" in script
    assert "pip check" in script
    assert "import api.main" in script
