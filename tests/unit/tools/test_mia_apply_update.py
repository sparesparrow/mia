"""bin/mia-apply-update: verify, validate, deploy, roll back (REQ-UPD-001 to REQ-UPD-003, REQ-UPD-005).

Each test builds a package the way the phone does, runs the script in a temporary directory with MIA_* overrides
(as tests/unit/infra/test_pi_install.py does for the install) and a stand-in deploy script inside the bundle, so no
real unit, apt or pip is touched.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.req("REQ-UPD-001", "REQ-UPD-002", "REQ-UPD-003", "REQ-UPD-005")

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "bin" / "mia-apply-update"
SCHEMAS = sorted((ROOT / "schemas").glob("*.fbs"))
USER_SCHEMA = ROOT / "schemas" / "json" / "mia-user-config.schema.json"
REQUIREMENTS = ROOT / "apps" / "rpi-backend" / "py-api" / "requirements.txt"

_loader = importlib.machinery.SourceFileLoader("mia_apply_update", str(TOOL))
_spec = importlib.util.spec_from_loader("mia_apply_update", _loader)
tool = importlib.util.module_from_spec(_spec)
_loader.exec_module(tool)

GOOD_YAML = 'version: 1\ndevice_name: "Audi A4"\nlogging:\n  level: info\n  retention_days: 14\n'

FAKE_DEPLOY = """#!/bin/bash
set -euo pipefail
cat > /dev/null
echo "$@" >> "$MIA_INSTALL_DIR/deploy.log"
cp "$(dirname "$0")/../../VERSION.txt" "$MIA_INSTALL_DIR/VERSION.txt"
if [ -n "${DEPLOY_FAILS:-}" ]; then exit 3; fi
"""


def _add(archive: tarfile.TarFile, name: str, data: bytes, mode: int = 0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    archive.addfile(info, io.BytesIO(data))


def make_bundle(version: str, extra=None, schema_edit: bytes = b"") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path in SCHEMAS:
            data = path.read_bytes() + (schema_edit if path.name == "mia.fbs" else b"")
            _add(archive, f"schemas/{path.name}", data)
        _add(archive, "schemas/json/mia-user-config.schema.json", USER_SCHEMA.read_bytes())
        _add(archive, "apps/rpi-backend/py-api/requirements.txt", REQUIREMENTS.read_bytes())
        _add(archive, "tools/scripts/deploy-raspberry-pi.sh", FAKE_DEPLOY.encode(), 0o755)
        _add(archive, "bin/mia-apply-update", b"#!/usr/bin/env python3\n", 0o755)
        _add(archive, "VERSION.txt", f"{version}\n".encode())
        for name, data in (extra or {}).items():
            _add(archive, name, data)
    return buffer.getvalue()


def make_package(version="2.3.0", yaml_text=GOOD_YAML, bundle=None, **overrides) -> bytes:
    bundle = bundle if bundle is not None else make_bundle(version)
    name = f"mia-rpi-backend-{version}.tar.gz"
    digest = hashlib.sha256(bundle).hexdigest()
    schema_files = {p.name: p.read_bytes() for p in SCHEMAS}
    manifest = {
        "version": version,
        "package": name,
        "package_sha256": digest,
        "schema_hash": tool.schema_hash(schema_files),
    }
    manifest.update(overrides.pop("manifest", {}))
    sums = overrides.pop("sums", f"{digest}  {name}\n")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add(archive, name, bundle)
        _add(archive, "SHA256SUMS", sums.encode())
        _add(archive, "config.yaml", yaml_text.encode())
        _add(archive, "manifest.json", json.dumps(manifest).encode())
        for extra_name, data in overrides.items():
            _add(archive, extra_name, data)
    return buffer.getvalue()


@pytest.fixture
def pi(tmp_path):
    install = tmp_path / "opt" / "mia"
    (install / "apps" / "rpi-backend" / "py-api").mkdir(parents=True)
    (install / "apps" / "rpi-backend" / "py-api" / "requirements.txt").write_bytes(REQUIREMENTS.read_bytes())
    state = tmp_path / "var" / "lib" / "mia"
    state.mkdir(parents=True)
    voice = state / "voice_settings.json"
    voice.write_text('{"verbosity": "quiet"}\n')
    bin_dir = tmp_path / "shims"
    bin_dir.mkdir()
    calls = tmp_path / "systemctl.log"
    shim = bin_dir / "systemctl"
    shim.write_text(f'#!/bin/bash\necho "$@" >> "{calls}"\n')
    shim.chmod(0o755)
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "MIA_UPDATE_DIR": str(tmp_path / "var" / "lib" / "mia" / "update"),
        "MIA_CONFIG_D": str(tmp_path / "etc" / "mia" / "config.d"),
        "MIA_INSTALL_DIR": str(install),
        "MIA_STATE_DIR": str(state),
    }

    class Pi:
        pass

    p = Pi()
    p.env, p.install, p.voice, p.calls = env, install, voice, calls
    p.config = Path(env["MIA_CONFIG_D"]) / "50-phone.json"
    p.update = Path(env["MIA_UPDATE_DIR"])

    def run(package: bytes = b"", *args, extra_env=None):
        done = subprocess.run(
            [sys.executable, str(TOOL), *args],
            input=package,
            capture_output=True,
            env={**env, **(extra_env or {})},
            timeout=60,
        )
        last = done.stdout.decode().strip().splitlines()[-1]
        return done.returncode, json.loads(last)

    p.run = run
    return p


def test_a_good_package_is_deployed_and_the_config_written(pi):
    code, result = pi.run(make_package("2.3.0"))
    assert code == 0 and result == {"ok": True, "step": "done", "version": "2.3.0", "error": None}
    assert "--skip-packages" in (pi.install / "deploy.log").read_text()
    assert json.loads(pi.config.read_text()) == {
        "version": 1,
        "device_name": "Audi A4",
        "logging": {"level": "info", "retention_days": 14},
    }
    assert "zmq-broker.service mia-api.service" in pi.calls.read_text()
    assert (pi.update / "current" / "manifest.json").is_file()
    assert not (pi.update / "staging").exists()


def test_a_checksum_mismatch_changes_nothing(pi):
    package = make_package("2.3.0", sums=f"{'0' * 64}  mia-rpi-backend-2.3.0.tar.gz\n")
    code, result = pi.run(package)
    assert code == 1 and result["ok"] is False and result["step"] == "verify"
    assert not (pi.install / "deploy.log").exists() and not pi.config.exists()


def test_a_bundle_that_differs_from_the_manifest_digest_is_refused(pi):
    code, result = pi.run(make_package("2.3.0", manifest={"package_sha256": "1" * 64}))
    assert (code, result["step"]) == (1, "verify")
    assert not (pi.install / "deploy.log").exists()


def test_a_schema_hash_mismatch_is_refused(pi):
    code, result = pi.run(make_package("2.3.0", manifest={"schema_hash": "2" * 64}))
    assert (code, result["step"]) == (1, "schema")
    assert "schema_hash" in result["error"]
    assert not (pi.install / "deploy.log").exists() and not pi.config.exists()


def test_a_bundle_with_changed_schemas_is_refused_by_the_recomputed_hash(pi):
    bundle = make_bundle("2.3.0", schema_edit=b"\n// edited\n")
    code, result = pi.run(make_package("2.3.0", bundle=bundle))
    assert (code, result["step"]) == (1, "schema")


@pytest.mark.parametrize(
    "yaml_text",
    [
        "version: 1\n\tdevice_name: x\n",
        "version: 1\nvoice: &anchor\n",
        "version: 1\ndevice_name: !!python/object:os.system x\n",
        "version: 1\ndevice_name: {a: b}\n",
        "version: 1\ndevice_name: $(reboot)\n",
        "---\nversion: 1\n",
        "version: 1\nversion: 1\n",
        "version: 1\ndevice_name: ok # trailing comment\n",
    ],
)
def test_bad_yaml_is_refused_before_any_change(pi, yaml_text):
    code, result = pi.run(make_package("2.3.0", yaml_text=yaml_text))
    assert (code, result["step"]) == (1, "config")
    assert not (pi.install / "deploy.log").exists() and not pi.config.exists()


@pytest.mark.parametrize(
    "yaml_text",
    [
        "device_name: x\n",
        "version: 2\n",
        'version: 1\nunknown: 1\n',
        'version: 1\ndevice_name: "; reboot"\n',
        "version: 1\nlogging:\n  retention_days: 500\n",
        "version: 1\nlogging:\n  level: loud\n",
        "version: 1\ntelemetry:\n  enabled: 1\n",
    ],
)
def test_a_config_the_schema_rejects_is_refused(pi, yaml_text):
    code, result = pi.run(make_package("2.3.0", yaml_text=yaml_text))
    assert (code, result["step"]) == (1, "config")
    assert not pi.config.exists()


def test_config_values_are_data_and_never_reach_a_shell(pi, tmp_path):
    marker = tmp_path / "pwned"
    # Shell metacharacters in a string are refused by the schema pattern; in an accepted string they stay data.
    code, result = pi.run(make_package("2.3.0", yaml_text='version: 1\ndevice_name: "Car $(touch ' + str(marker) + ')"\n'))
    assert code == 1 and not marker.exists()
    code, _ = pi.run(make_package("2.3.0", yaml_text='version: 1\ndevice_name: "Car 1"\n'))
    assert code == 0 and not marker.exists()


@pytest.mark.parametrize("member", ["../evil", "/etc/evil", "a/../../evil"])
def test_a_traversing_bundle_member_is_refused(pi, tmp_path, member):
    bundle = make_bundle("2.3.0", extra={member: b"x"})
    code, result = pi.run(make_package("2.3.0", bundle=bundle))
    assert (code, result["step"]) == (1, "unpack")
    assert not (tmp_path / "evil").exists()


def test_a_symlink_in_the_bundle_is_refused(pi):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        link = tarfile.TarInfo("schemas/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        archive.addfile(link)
    code, result = pi.run(make_package("2.3.0", bundle=buffer.getvalue()))
    assert (code, result["step"]) == (1, "unpack")


def test_an_unexpected_outer_member_is_refused(pi):
    code, result = pi.run(make_package("2.3.0", **{"evil.sh": b"#!/bin/sh\n"}))
    assert (code, result["step"]) == (1, "extract")


def test_garbage_and_empty_input_fail_cleanly(pi):
    assert pi.run(b"not a tar")[1]["step"] == "extract"
    assert pi.run(b"")[1]["step"] == "receive"


def test_an_oversized_package_is_refused(pi):
    code, result = pi.run(make_package("2.3.0"), extra_env={"MIA_MAX_PACKAGE_MB": "0"})
    assert (code, result["step"]) == (1, "receive")


def test_changed_requirements_need_the_full_install(pi):
    (pi.install / "apps" / "rpi-backend" / "py-api" / "requirements.txt").write_text("something-else\n")
    code, result = pi.run(make_package("2.3.0"))
    assert (code, result["step"]) == (1, "requirements")
    assert not (pi.install / "deploy.log").exists()


def test_a_failing_deploy_leaves_config_and_current_alone(pi):
    assert pi.run(make_package("2.3.0"))[0] == 0
    before = pi.config.read_text()
    code, result = pi.run(
        make_package("2.4.0", yaml_text="version: 1\ndevice_name: Other\n"), extra_env={"DEPLOY_FAILS": "1"}
    )
    assert (code, result["step"]) == (1, "deploy")
    assert pi.config.read_text() == before
    assert json.loads((pi.update / "current" / "manifest.json").read_text())["version"] == "2.3.0"


def test_rollback_redeploys_the_previous_package_and_config(pi):
    assert pi.run(make_package("2.3.0"))[0] == 0
    assert pi.run(make_package("2.4.0", yaml_text="version: 1\ndevice_name: Newer\n"))[0] == 0
    assert (pi.install / "VERSION.txt").read_text().strip() == "2.4.0"
    assert json.loads(pi.config.read_text())["device_name"] == "Newer"

    code, result = pi.run(b"", "--rollback")
    assert (code, result["ok"], result["version"]) == (0, True, "2.3.0")
    assert (pi.install / "VERSION.txt").read_text().strip() == "2.3.0"
    assert json.loads(pi.config.read_text())["device_name"] == "Audi A4"
    assert json.loads((pi.update / "current" / "manifest.json").read_text())["version"] == "2.3.0"
    assert json.loads((pi.update / "previous" / "manifest.json").read_text())["version"] == "2.4.0"


def test_rollback_without_a_previous_package_says_so(pi):
    assert pi.run(make_package("2.3.0"))[0] == 0
    code, result = pi.run(b"", "--rollback")
    assert (code, result["step"]) == (1, "rollback")


def test_a_damaged_previous_package_is_not_rolled_back_to(pi):
    assert pi.run(make_package("2.3.0"))[0] == 0
    assert pi.run(make_package("2.4.0"))[0] == 0
    (pi.update / "previous" / "mia-rpi-backend-2.3.0.tar.gz").write_bytes(b"tampered")
    code, result = pi.run(b"", "--rollback")
    assert (code, result["step"]) == (1, "verify")
    assert (pi.install / "VERSION.txt").read_text().strip() == "2.4.0"


def test_pi_owned_state_is_never_touched(pi):
    before = pi.voice.read_bytes()
    stamp = pi.voice.stat().st_mtime_ns
    time.sleep(0.01)
    assert pi.run(make_package("2.3.0"))[0] == 0
    assert pi.run(make_package("2.4.0"))[0] == 0
    assert pi.run(b"", "--rollback")[0] == 0
    pi.run(make_package("2.5.0", sums="bad\n"))
    assert pi.voice.read_bytes() == before and pi.voice.stat().st_mtime_ns == stamp
    assert sorted(p.name for p in pi.voice.parent.iterdir() if p.is_file()) == ["voice_settings.json"]
    assert "voice_settings" not in TOOL.read_text().replace("voice_settings.json, ADR-0019", "")


def test_the_result_is_one_json_line_on_stdout(pi):
    done = subprocess.run([sys.executable, str(TOOL)], input=make_package("2.3.0"), capture_output=True, env=pi.env)
    lines = done.stdout.decode().strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["ok"] is True


def test_unknown_arguments_are_refused(pi):
    code, result = pi.run(b"", "--evil")
    assert (code, result["step"]) == (2, "args")


def test_the_unit_list_matches_the_deploy_script():
    script = (ROOT / "tools" / "scripts" / "deploy-raspberry-pi.sh").read_text()
    block = re.search(r"CORE_UNITS=\(\n(.*?)\n\)", script, re.S).group(1)
    assert tuple(block.split()) == tool.CORE_UNITS


def test_the_shipped_schema_is_valid_and_the_validator_agrees_with_jsonschema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(USER_SCHEMA.read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    good = [
        {"version": 1},
        {"version": 1, "device_name": "Audi A4", "logging": {"level": "debug", "retention_days": 90}},
        {"version": 1, "telemetry": {"interval_ms": 100, "enabled": False}},
    ]
    bad = [
        {},
        {"version": True},
        {"version": 1, "device_name": ""},
        {"version": 1, "device_name": "x" * 33},
        {"version": 1, "device_name": "a;b"},
        {"version": 1, "extra": 1},
        {"version": 1, "logging": {"level": "trace"}},
        {"version": 1, "logging": {"retention_days": 0}},
        {"version": 1, "telemetry": {"interval_ms": 99}},
        {"version": 1, "telemetry": {"enabled": "yes"}},
    ]
    for doc in good:
        jsonschema.validate(doc, schema)
        tool.validate(doc, schema)
    for doc in bad:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)
        with pytest.raises(tool.Fail):
            tool.validate(doc, schema)


def test_the_schema_hash_has_a_fixed_golden_value():
    # The Kotlin SchemaHash test asserts the same value for the same input.
    assert tool.schema_hash({"a.fbs": b"table A {}\n", "b.fbs": b"table B {}\n"}) == GOLDEN_SCHEMA_HASH


GOLDEN_SCHEMA_HASH = "36f8bc162b7316679c41da930a62b9f201d9236ac7939e7239e8e41427bbefc2"
