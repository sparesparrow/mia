"""tools/scripts/deploy-production-rpi.sh run end to end with systemd and curl stubbed (REQ-DEP-008).

The script refuses to run unless it is root, so these tests run only where the test process is root (a developer's
container, not the GitHub runner); CI checks the script's text in test_pi_install.py instead. Nothing real is
touched: the script runs from a copy in a temporary tree whose setup-ble-service.sh and deploy-raspberry-pi.sh are
stubs, systemctl, curl, hciconfig and sleep are shims on PATH, and the environment file and state directory are
temporary paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.req("REQ-DEP-008"),
    pytest.mark.skipif(shutil.which("bash") is None or shutil.which("git") is None, reason="needs bash and git"),
    pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() != 0, reason="the deploy script runs only as root"),
]

SCRIPTS = Path(__file__).resolve().parents[3] / "tools" / "scripts"
API_KEY = "mia_api_secret_0123456789"
ENABLED = "mia-api.service mia-gpio-worker.service mia-selftest.service"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}

SYSTEMCTL = r"""#!/bin/bash
echo "systemctl $*" >> "$SHIM_LOG"
has() { [[ " $1 " == *" $2 "* ]]; }
case "$1" in
    restart)
        shift
        for unit in "$@"; do has "${SHIM_FAIL_RESTART:-}" "$unit" && exit 1; done
        exit 0 ;;
    list-unit-files)
        [ "${SHIM_LIST_FAILS:-0}" = 1 ] && { echo "Failed to connect to bus" >&2; exit 1; }
        for unit in $SHIM_ENABLED; do echo "$unit enabled enabled"; done ;;
    show)
        unit="${@: -1}"
        case "$3" in
            Type) if [ "$unit" = mia-selftest.service ]; then echo oneshot; else echo simple; fi ;;
            NRestarts) if has "${SHIM_CRASHLOOP:-}" "$unit"; then echo 3; else echo 0; fi ;;
        esac ;;
    is-active)
        if has "${SHIM_CRASHLOOP:-}" "$2" || has "${SHIM_FAIL_RESTART:-}" "$2"; then echo activating; exit 3; fi
        echo active ;;
    list-units)
        if [[ " $* " == *" --state=failed "* ]]; then
            for unit in ${SHIM_FAILED:-}; do echo "$unit loaded failed failed MIA"; done
        else
            echo "zmq-broker.service loaded active running broker"
        fi ;;
esac
exit 0
"""

CURL = r"""#!/bin/bash
echo "$*" >> "$SHIM_DIR/curl-args.log"
cat >> "$SHIM_DIR/curl-stdin.log"
exit 0
"""

STUB = '#!/bin/bash\necho "stub $(basename "$0")"\n'


@pytest.fixture
def deploy(tmp_path):
    shims = tmp_path / "shims"
    shims.mkdir()
    for name, body in {
        "systemctl": SYSTEMCTL,
        "curl": CURL,
        "hciconfig": "#!/bin/bash\nexit 1\n",
        "sleep": "#!/bin/bash\nexit 0\n",
    }.items():
        (shims / name).write_text(body)
        (shims / name).chmod(0o755)

    src = tmp_path / "src"
    scripts = src / "tools" / "scripts"
    scripts.mkdir(parents=True)
    for name in ("deploy-production-rpi.sh", "mia-update-checkout.sh"):
        shutil.copy(SCRIPTS / name, scripts / name)
    for name in ("setup-ble-service.sh", "deploy-raspberry-pi.sh"):
        (scripts / name).write_text(STUB)

    env_file = tmp_path / "environment"
    env_file.write_text(f"MIA_API_KEY={API_KEY}\n")
    state = tmp_path / "state"
    log = tmp_path / "systemctl.log"

    def run(script: Path | None = None, **extra: str):
        inherited = {k: v for k, v in os.environ.items() if not k.startswith("MIA_")}
        env = {
            **inherited,
            **GIT_ENV,
            "PATH": f"{shims}{os.pathsep}{os.environ.get('PATH', '')}",
            "SHIM_LOG": str(log),
            "SHIM_DIR": str(shims),
            "SHIM_ENABLED": ENABLED,
            "MIA_ENV_FILE": str(env_file),
            "MIA_STATE_DIR": str(state),
            "MIA_DEPLOY_SETTLE_SECONDS": "0",
            "MIA_DEPLOY_SKIP_FETCH": "1",
            **extra,
        }
        result = subprocess.run(
            ["bash", str(script or scripts / "deploy-production-rpi.sh")],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        result.output = result.stdout + result.stderr
        result.calls = log.read_text() if log.exists() else ""
        record = state / "deployed.json"
        result.record = json.loads(record.read_text()) if record.exists() else None
        return result

    def read(name: str) -> str:
        path = shims / name
        return path.read_text() if path.exists() else ""

    return run, src, read


def test_a_healthy_deploy_restarts_broker_first_and_records_a_verified_checkout(deploy):
    run, _, read = deploy
    result = run()
    assert result.returncode == 0, result.output
    calls = result.calls.splitlines()
    assert calls.index("systemctl restart zmq-broker.service") < calls.index(
        "systemctl restart mia-api.service mia-gpio-worker.service"
    )
    assert "mia-selftest.service" not in " ".join(line for line in calls if line.startswith("systemctl restart"))
    # MIA_DEPLOY_SKIP_FETCH=1 deploys the checkout as it is, not origin/main.
    assert result.record["ref"] == "checkout"
    assert result.record["verified"] is True


def test_the_api_key_reaches_curl_on_stdin_not_in_its_arguments(deploy):
    run, _, read = deploy
    assert run().returncode == 0
    assert API_KEY not in read("curl-args.log")
    assert f"X-API-Key: {API_KEY}" in read("curl-stdin.log")


def test_a_crash_looping_unit_fails_the_deploy(deploy):
    run, _, _ = deploy
    result = run(SHIM_CRASHLOOP="mia-gpio-worker.service")
    assert result.returncode == 1, result.output
    assert "mia-gpio-worker.service" in result.output
    assert result.record is None


def test_a_failed_unit_this_deploy_did_not_restart_is_a_warning(deploy):
    """mia-selftest is a oneshot that ran at boot; its old failure does not judge this deploy."""
    run, _, _ = deploy
    result = run(SHIM_FAILED="mia-selftest.service")
    assert result.returncode == 0, result.output
    assert "mia-selftest.service" in result.output
    assert "not restarted by this deploy" in result.output


def test_a_failed_broker_restart_still_verifies_and_fails(deploy):
    run, _, _ = deploy
    result = run(SHIM_FAIL_RESTART="zmq-broker.service")
    assert result.returncode == 1, result.output
    assert "Deployment completed with errors" in result.output
    assert result.record is None


def test_a_failed_unit_listing_fails_the_deploy(deploy):
    run, _, _ = deploy
    result = run(SHIM_LIST_FAILS="1")
    assert result.returncode == 1, result.output
    assert "systemctl restart mia-api.service" not in result.calls
    assert result.record is None


def test_install_only_records_nothing(deploy):
    run, _, _ = deploy
    result = run(MIA_NO_RESTART="1")
    assert result.returncode == 0, result.output
    assert "systemctl restart" not in result.calls
    assert result.record is None


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env={**os.environ, **GIT_ENV}, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def rollback(deploy, tmp_path):
    """The source tree as a clone of an origin whose next commit replaces deploy-production-rpi.sh."""
    run, src, _ = deploy
    _git(src, "init", "-q", "-b", "main")
    _git(src, "add", "-A")
    _git(src, "commit", "-qm", "current")
    upstream = tmp_path / "upstream"
    _git(tmp_path, "clone", "-q", "--bare", str(src), str(upstream))
    shutil.rmtree(src)
    _git(tmp_path, "clone", "-q", str(upstream), str(src))
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(upstream), str(work))
    target = work / "tools" / "scripts" / "deploy-production-rpi.sh"

    def push_target(content: str | None) -> str:
        if content is None:
            target.unlink()
        else:
            target.write_text(content)
        _git(work, "add", "-A")
        _git(work, "commit", "-qm", "target")
        _git(work, "push", "-q", "origin", "HEAD:main")
        return _git(work, "rev-parse", "HEAD")

    def deploy_ref(sha: str):
        return run(src / "tools" / "scripts" / "deploy-production-rpi.sh", MIA_DEPLOY_SKIP_FETCH="0", MIA_DEPLOY_REF=sha)

    return push_target, deploy_ref


def test_a_rollback_to_a_script_without_the_safe_step_one_keeps_running_the_current_copy(rollback):
    push_target, deploy_ref = rollback
    sha = push_target('#!/bin/bash\necho OLD-SCRIPT-RAN\ngit pull origin main\nexit 3\n')
    result = deploy_ref(sha)
    assert result.returncode == 0, result.output
    assert "OLD-SCRIPT-RAN" not in result.output
    assert "predates the safe deploy" in result.output
    assert result.record["sha"] == sha
    assert result.record["ref"] == sha


def test_a_rollback_to_a_commit_without_the_script_keeps_running_the_current_copy(rollback):
    push_target, deploy_ref = rollback
    result = deploy_ref(push_target(None))
    assert result.returncode == 0, result.output
    assert "predates the safe deploy" in result.output


def test_an_updated_copy_with_the_safe_step_one_runs_from_the_top(rollback):
    push_target, deploy_ref = rollback
    sha = push_target('#!/bin/bash\n# MIA_DEPLOY_CHECKOUT_DONE\necho "UPDATED-COPY-RAN $MIA_DEPLOY_CHECKOUT_DONE"\n')
    result = deploy_ref(sha)
    assert result.returncode == 0, result.output
    assert "UPDATED-COPY-RAN 1" in result.output
