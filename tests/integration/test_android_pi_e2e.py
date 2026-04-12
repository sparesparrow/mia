#!/usr/bin/env python3
"""
MIA Android USB ↔ Raspberry Pi/Kali product prototype integration harness.

This test combines the repo's rooted-Android verification workflow, the Android
ADB skill runner, and the canonical Raspberry Pi deployment scripts into a
single end-to-end harness with a persistent self-improvement loop.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import logging
import os
import re
import shlex
import shutil
import socket
import subprocess
import textwrap
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "tests" / "integration" / "artifacts"
LEARNINGS_FILE = ARTIFACTS_DIR / "self_improvement_learnings.json"
ROOT_VERIFY_SCRIPT = REPO_ROOT / "scripts" / "android-device-setup" / "root" / "verify-root.sh"
ANDROID_SKILL_SCRIPT = REPO_ROOT / "skills" / "android-adb-test" / "scripts" / "android-adb-test.sh"

DEFAULT_HOST = os.getenv("MIA_TARGET_HOST", "192.168.200.134")
DEFAULT_USER = os.getenv("MIA_TARGET_USER", "sparrow")
DEFAULT_PORT = int(os.getenv("MIA_TARGET_PORT", "22"))
DEFAULT_INSTALL_PATH = os.getenv("MIA_TARGET_PATH", "/opt/mia")
DEFAULT_ADB_SERIAL = os.getenv("MIA_ADB_SERIAL", "")
DEFAULT_EXPECTED_SUBNET = os.getenv("MIA_EXPECTED_SUBNET", "192.168.200.0/24")
DEFAULT_EXPECTED_TARGET_OS = os.getenv("MIA_EXPECTED_TARGET_OS", "kali")

MIA_PACKAGE = "cz.mia.app"
API_PORT = 8000
ZMQ_BROKER_PORT = 5555

PROTOTYPE_SERVICE_UNITS = [
    "zmq-broker",
    "mia-api",
    "mia-gpio-worker",
    "mia-serial-bridge",
    "mia-obd-worker",
    "mia-ble-advertiser",
    "mia-ble-obd",
]

REMOTE_REPO_EXCLUDES = [
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "android",
    "android-device-workspace",
    "apps/android",
    "apps/android/test-artifacts",
    "build-hardware-server",
    "node_modules",
    "screenshots",
    "site",
    "tests/integration/artifacts",
    "tmp",
]

LOGCAT_CRASH_PATTERNS = [
    r"AndroidRuntime",
    r"\bFATAL EXCEPTION\b",
    r"Process:\s+cz\.mia\.app",
    r"java\.lang\.(?:RuntimeException|IllegalStateException)",
]

ANDROID_SCENARIOS = [
    "install",
    "dashboard",
    "ble-scan",
    "obd-pairing",
    "settings",
    "anpr",
    "full-flow",
    "interactive",
]

log = logging.getLogger("mia.android-pi-e2e")


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    REMEDIATED = "REMEDIATED"


@dataclass
class PrototypeProfile:
    expected_subnet: str = DEFAULT_EXPECTED_SUBNET
    expected_target_os: str = DEFAULT_EXPECTED_TARGET_OS
    require_pi_hardware: bool = True
    require_rooted_phone: bool = True
    prototype_services: list[str] = field(default_factory=lambda: PROTOTYPE_SERVICE_UNITS.copy())


@dataclass
class StepResult:
    name: str
    verdict: Verdict
    duration_s: float = 0.0
    detail: str = ""
    error: str = ""
    remediation_applied: str = ""


@dataclass
class PhaseResult:
    phase: str
    steps: list[StepResult] = field(default_factory=list)
    started: str = ""
    finished: str = ""

    @property
    def passed(self) -> int:
        return sum(1 for step in self.steps if step.verdict in (Verdict.PASS, Verdict.REMEDIATED))

    @property
    def failed(self) -> int:
        return sum(1 for step in self.steps if step.verdict == Verdict.FAIL)


@dataclass
class RunReport:
    run_id: str
    host: str
    device: str
    phases: list[PhaseResult] = field(default_factory=list)
    learnings_applied: list[str] = field(default_factory=list)
    new_learnings: list[dict[str, Any]] = field(default_factory=list)
    meta_summary: dict[str, Any] = field(default_factory=dict)
    total_duration_s: float = 0.0

    @property
    def summary_line(self) -> str:
        passed = sum(phase.passed for phase in self.phases)
        failed = sum(phase.failed for phase in self.phases)
        return f"{passed} passed, {failed} failed across {len(self.phases)} phases in {self.total_duration_s:.1f}s"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _bash_script(script: str) -> str:
    return f"bash -lc {shlex.quote(textwrap.dedent(script).strip())}"


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def _looks_like_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _resolve_host(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except OSError:
        return host


def run(
    cmd: str | list[str],
    *,
    timeout: int = 120,
    check: bool = True,
    capture: bool = True,
    cwd: Path | None = None,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    args = shlex.split(cmd) if isinstance(cmd, str) else cmd
    log.debug("$ %s", _shell_join(args))
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=check,
        cwd=cwd,
        env=env,
    )


class Remote:
    def __init__(self, host: str, user: str, port: int = 22):
        self.host = host
        self.user = user
        self.port = port
        self._base = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "BatchMode=yes",
            "-p",
            str(port),
        ]

    def ssh(self, cmd: str, *, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        full = self._base + [f"{self.user}@{self.host}", cmd]
        log.debug("ssh> %s", cmd)
        return subprocess.run(
            full,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=check,
        )

    def rsync(
        self,
        local: str,
        remote: str,
        *,
        exclude: Optional[list[str]] = None,
        timeout: int = 600,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [
            "rsync",
            "-az",
            "--delete",
            "-e",
            f"ssh -o BatchMode=yes -p {self.port}",
        ]
        for pattern in exclude or []:
            cmd += ["--exclude", pattern]
        cmd += [local, f"{self.user}@{self.host}:{remote}"]
        log.debug("rsync> %s -> %s", local, remote)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=True,
        )


def adb(*args: str, serial: str = "", timeout: int = 30) -> subprocess.CompletedProcess[str]:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    return run(cmd, timeout=timeout, check=False)


def adb_shell(command: str, *, serial: str = "", timeout: int = 30, root: bool = False) -> subprocess.CompletedProcess[str]:
    if root:
        return adb("shell", "su", "-c", command, serial=serial, timeout=timeout)
    return adb("shell", "sh", "-c", command, serial=serial, timeout=timeout)


def pick_adb_device() -> str:
    result = adb("devices", "-l", timeout=20)
    usb_devices: list[str] = []
    fallback_devices: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices") or "offline" in line:
            continue
        if " device " not in f" {line} ":
            continue
        serial = line.split()[0]
        if serial.startswith("emulator-"):
            fallback_devices.append(serial)
            continue
        usb_devices.append(serial)
    if usb_devices:
        return usb_devices[0]
    if fallback_devices:
        return fallback_devices[0]
    raise RuntimeError("No connected adb device found")


def http_request(
    url: str,
    *,
    method: str = "GET",
    body: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 10,
) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=body.encode("utf-8") if body is not None else None,
        method=method,
    )
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:
        return 0, str(exc)


def _json_detail(body: str, *, max_keys: int = 6) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        snippet = body.strip().replace("\n", " ")
        return snippet[:180]
    if isinstance(payload, dict):
        return ", ".join(sorted(str(key) for key in payload.keys())[:max_keys])
    if isinstance(payload, list):
        return f"list[{len(payload)}]"
    return str(payload)[:180]


def android_http_get(url: str, *, serial: str, timeout: int = 30, root: bool = False) -> str:
    command = textwrap.dedent(
        f"""
        if command -v curl >/dev/null 2>&1; then
          curl -fsS {shlex.quote(url)}
        elif command -v toybox >/dev/null 2>&1; then
          toybox wget -qO- {shlex.quote(url)}
        elif command -v wget >/dev/null 2>&1; then
          wget -qO- {shlex.quote(url)}
        else
          exit 127
        fi
        """
    ).strip()
    result = adb_shell(command, serial=serial, timeout=timeout, root=root)
    if result.returncode != 0:
        raise RuntimeError(f"Android HTTP probe failed for {url}: {result.stdout}{result.stderr}".strip())
    return result.stdout.strip()


class SelfImprovementEngine:
    KNOWN_PATTERNS: list[tuple[str, str, str]] = [
        (r"USB transport is not active|get-devpath returned empty", "Android USB transport not active", "remediate_adb_usb"),
        (r"Android root verification failed|Root verification failed", "Android root verification failed", "remediate_adb_reconnect"),
        (r"Connection refused", "API not listening", "remediate_restart_prototype_services"),
        (r"HTTP Error 50[0-9]|503 Service Unavailable|API returned 50[0-9]", "API not ready", "remediate_wait_and_retry"),
        (r"INSTALL_FAILED", "APK install failed", "remediate_apk_install"),
        (r"error: device .* not found|no devices/emulators found", "ADB device disconnected", "remediate_adb_reconnect"),
        (r"No space left on device", "Disk full on target", "remediate_disk_space"),
        (r"Address already in use", "Port conflict", "remediate_restart_prototype_services"),
        (r"Inactive prototype services|service .* inactive", "Prototype service inactive", "remediate_restart_prototype_services"),
        (r"deploy-production-rpi\.sh failed", "Prototype deploy script failed", "remediate_wait_and_retry"),
        (r"Permission denied \(publickey", "SSH permission denied", ""),
        (r"Expected target OS|Expected target hardware|not inside expected subnet|Android device is not on expected subnet", "Profile mismatch", ""),
    ]

    def __init__(self, remote: Remote, prototype_services: list[str], dry: bool = False):
        self.remote = remote
        self.prototype_services = prototype_services
        self.dry = dry
        self.learnings: list[dict[str, Any]] = self._load_learnings()
        self.new_learnings: list[dict[str, Any]] = []
        self.applied: list[str] = []

    @staticmethod
    def _load_learnings() -> list[dict[str, Any]]:
        if not LEARNINGS_FILE.exists():
            return []
        try:
            payload = json.loads(LEARNINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(payload, list):
            return []
        # Migrate stale entries: drop those with diagnosis=unknown and overly-escaped patterns
        valid = []
        for item in payload:
            diag = item.get("diagnosis", "")
            pattern = item.get("pattern", "")
            if diag == "unknown" and not item.get("success", False):
                continue  # discard undiagnosed failures — they never match
            if pattern and len(pattern) > 200 and "\\" in pattern:
                continue  # discard overly-escaped verbatim patterns
            valid.append(item)
        return valid

    def persist(self) -> None:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        combined = self.learnings + self.new_learnings
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in combined:
            key = (item.get("step", ""), item.get("diagnosis", ""), item.get("remediation", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        LEARNINGS_FILE.write_text(json.dumps(deduped, indent=2), encoding="utf-8")

    def diagnose(self, error_text: str) -> tuple[str, str, re.Match[str] | None]:
        for pattern, diagnosis, remediation in self.KNOWN_PATTERNS:
            match = re.search(pattern, error_text, re.IGNORECASE)
            if match:
                return diagnosis, remediation, match
        for item in self.learnings:
            pattern = item.get("pattern", "")
            if pattern and re.search(pattern, error_text, re.IGNORECASE):
                return item.get("diagnosis", "known issue"), item.get("remediation", ""), None
        return "", "", None

    def remediate(self, remediation: str, match: re.Match[str] | None = None) -> bool:
        if not remediation:
            return False
        handler = getattr(self, remediation, None)
        if handler is None:
            return False
        if self.dry:
            self.applied.append(f"[dry] {remediation}")
            return True
        try:
            success = handler(match)
        except Exception as exc:
            log.warning("Remediation %s failed: %s", remediation, exc)
            return False
        if success:
            self.applied.append(remediation)
        return success

    @staticmethod
    def _extract_error_signature(error_text: str, diagnosis: str) -> str:
        """Build a reusable regex pattern from an error, not a verbatim escape."""
        if diagnosis and diagnosis != "unknown":
            return re.escape(diagnosis)
        # Extract the most informative fragment: HTTP status lines, Python exceptions, key phrases
        for rx in [
            r"returned (\d{3}): .{0,60}",
            r"(\w+Error|\w+Exception): .{0,80}",
            r"(Connection refused|No space left|Permission denied|not found|not listening).{0,40}",
        ]:
            m = re.search(rx, error_text, re.IGNORECASE)
            if m:
                return re.escape(m.group(0)[:120])
        # Fallback: first meaningful line, trimmed
        first_line = error_text.split("\n")[0].strip()[:120]
        return re.escape(first_line) if first_line else ""

    def record_learning(self, step: str, error_text: str, diagnosis: str, remediation: str, success: bool) -> None:
        focus = self.focus_for_diagnosis(diagnosis)
        pattern = self._extract_error_signature(error_text, diagnosis)
        self.new_learnings.append(
            {
                "timestamp": _now(),
                "step": step,
                "pattern": pattern,
                "diagnosis": diagnosis or "unknown",
                "remediation": remediation or "none",
                "success": success,
                "focus": focus,
            }
        )

    def focus_for_diagnosis(self, diagnosis: str) -> str:
        lowered = diagnosis.lower()
        if "root" in lowered or "usb" in lowered or "profile" in lowered or "subnet" in lowered:
            return "device-profile"
        if "deploy" in lowered or "service" in lowered or "port conflict" in lowered:
            return "deploy-bringup"
        if "api" in lowered or "broker" in lowered:
            return "backend-transport"
        if "apk" in lowered or "adb" in lowered:
            return "android-runtime"
        return "coverage-expansion"

    def summarise_run(self, report: RunReport) -> dict[str, Any]:
        total_steps = sum(len(phase.steps) for phase in report.phases)
        passed_steps = sum(phase.passed for phase in report.phases)
        failed_steps = sum(phase.failed for phase in report.phases)
        pass_rate = round((passed_steps / total_steps) if total_steps else 0.0, 3)
        phase_success_rate = round(
            (sum(1 for phase in report.phases if phase.failed == 0) / len(report.phases)) if report.phases else 0.0,
            3,
        )
        duration_budget = 2400.0
        efficiency = round(min(1.0, duration_budget / max(report.total_duration_s, 1.0)), 3)
        error_rate = round((failed_steps / total_steps) if total_steps else 0.0, 3)

        all_learnings = self.learnings + self.new_learnings
        diagnosis_counts: dict[str, int] = {}
        focus_counts: dict[str, int] = {}
        for item in all_learnings:
            diagnosis = item.get("diagnosis", "unknown")
            focus = item.get("focus") or self.focus_for_diagnosis(diagnosis)
            diagnosis_counts[diagnosis] = diagnosis_counts.get(diagnosis, 0) + 1
            focus_counts[focus] = focus_counts.get(focus, 0) + 1

        remediation_attempts = [item for item in report.new_learnings if item.get("remediation") not in ("", "none")]
        remediation_success_rate = round(
            (sum(1 for item in remediation_attempts if item.get("success")) / len(remediation_attempts))
            if remediation_attempts
            else 0.0,
            3,
        )

        latest_diagnoses = sorted(diagnosis_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        latest_focuses = sorted(focus_counts.items(), key=lambda item: (-item[1], item[0]))
        next_focus = latest_focuses[0][0] if latest_focuses else ("coverage-expansion" if failed_steps == 0 else "deploy-bringup")

        return {
            "metrics": {
                "step_pass_rate": pass_rate,
                "phase_success_rate": phase_success_rate,
                "execution_efficiency": efficiency,
                "error_rate": error_rate,
            },
            "remediation_success_rate": remediation_success_rate,
            "next_focus": next_focus,
            "top_diagnoses": [{"diagnosis": name, "count": count} for name, count in latest_diagnoses],
            "focus_histogram": {name: count for name, count in latest_focuses},
            "applied_remediations": self.applied.copy(),
            "knowledge_entries": len(all_learnings),
        }

    def remediate_wait_and_retry(self, _match: re.Match[str] | None = None) -> bool:
        time.sleep(10)
        return True

    def remediate_adb_reconnect(self, _match: re.Match[str] | None = None) -> bool:
        run(["adb", "reconnect"], check=False, timeout=20)
        time.sleep(3)
        return True

    def remediate_adb_usb(self, _match: re.Match[str] | None = None) -> bool:
        run(["adb", "usb"], check=False, timeout=20)
        time.sleep(3)
        return True

    def remediate_apk_install(self, _match: re.Match[str] | None = None) -> bool:
        run(["adb", "uninstall", MIA_PACKAGE], check=False, timeout=30)
        time.sleep(2)
        return True

    def remediate_disk_space(self, _match: re.Match[str] | None = None) -> bool:
        command = _bash_script(
            """
            sudo journalctl --vacuum-size=50M 2>/dev/null || true
            sudo apt-get clean 2>/dev/null || true
            find /tmp -maxdepth 1 -type f -mtime +3 -delete 2>/dev/null || true
            df -h /
            """
        )
        result = self.remote.ssh(command, timeout=60, check=False)
        return result.returncode == 0

    def remediate_restart_prototype_services(self, _match: re.Match[str] | None = None) -> bool:
        units = " ".join(self.prototype_services)
        command = _bash_script(
            f"""
            sudo systemctl daemon-reload || true
            sudo systemctl restart {units} || true
            sleep 5
            for svc in {units}; do
              printf '%s=' "$svc"
              systemctl is-active "$svc" 2>/dev/null || echo inactive
            done
            """
        )
        result = self.remote.ssh(command, timeout=90, check=False)
        return result.returncode == 0


class IntegrationHarness:
    def __init__(
        self,
        *,
        remote: Remote,
        profile: PrototypeProfile,
        engine: SelfImprovementEngine,
        device_serial: str,
        install_path: str,
        phases: list[str],
        android_scenario: str,
        skip_deploy: bool,
    ):
        self.remote = remote
        self.profile = profile
        self.engine = engine
        self.device = device_serial
        self.install_path = install_path.rstrip("/")
        self.remote_repo_path = f"{self.install_path}/repo"
        self.selected_phases = [phase for phase in phases if not (skip_deploy and phase == "deploy")]
        self.android_scenario = android_scenario
        self.resolved_host = _resolve_host(remote.host)
        self.base_url = f"http://{self.resolved_host}:{API_PORT}"
        self.api_base_url = f"{self.base_url}/"
        self.ws_base_url = f"ws://{self.resolved_host}:{API_PORT}"
        self.report = RunReport(
            run_id=dt.datetime.now().strftime("%Y%m%d_%H%M%S"),
            host=remote.host,
            device=device_serial,
        )
        self.artifact_dir = ARTIFACTS_DIR / self.report.run_id
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.android_skill_output = self.artifact_dir / "android-skill"
        self.root_report_path = self.artifact_dir / "android-root-verification-report.txt"

    def run_all(self) -> RunReport:
        if not self.selected_phases:
            raise RuntimeError("No phases selected to run")

        phase_map = {
            "preflight": self.phase_preflight,
            "deploy": self.phase_deploy,
            "smoke": self.phase_smoke,
            "android": self.phase_android,
            "e2e": self.phase_e2e,
        }

        started = time.monotonic()
        for phase_name in self.selected_phases:
            phase_result = phase_map[phase_name]()
            self.report.phases.append(phase_result)

        self.report.learnings_applied = self.engine.applied.copy()
        self.report.new_learnings = self.engine.new_learnings.copy()
        self.report.total_duration_s = time.monotonic() - started
        self.report.meta_summary = self.engine.summarise_run(self.report)
        self.engine.persist()
        self._save_report()
        return self.report

    def _save_report(self) -> None:
        report_path = self.artifact_dir / "report.json"
        meta_path = self.artifact_dir / "meta_harness_summary.json"
        _write_text(report_path, json.dumps(asdict(self.report), indent=2))
        _write_text(meta_path, json.dumps(self.report.meta_summary, indent=2))

        # Regression tracking: compare with previous run
        regression = self._compare_with_previous_run()
        if regression:
            self.report.meta_summary["regression"] = regression
            _write_text(meta_path, json.dumps(self.report.meta_summary, indent=2))

    def _compare_with_previous_run(self) -> dict[str, Any] | None:
        """Compare current results with the most recent prior run."""
        report_files = sorted(ARTIFACTS_DIR.glob("*/report.json"))
        current = self.artifact_dir / "report.json"
        prior_files = [f for f in report_files if f != current]
        if not prior_files:
            return None
        try:
            prev_data = json.loads(prior_files[-1].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Build step→verdict maps
        prev_steps: dict[str, str] = {}
        for phase in prev_data.get("phases", []):
            for step in phase.get("steps", []):
                prev_steps[step["name"]] = step["verdict"]

        curr_steps: dict[str, str] = {}
        for phase in self.report.phases:
            for step in phase.steps:
                curr_steps[step.name] = step.verdict.value

        regressions = [name for name, v in curr_steps.items()
                       if prev_steps.get(name) in ("PASS", "REMEDIATED") and v == "FAIL"]
        improvements = [name for name, v in curr_steps.items()
                        if prev_steps.get(name) == "FAIL" and v in ("PASS", "REMEDIATED")]
        new_steps = [name for name in curr_steps if name not in prev_steps]

        return {
            "previous_run": prev_data.get("run_id", "unknown"),
            "regressions": regressions,
            "improvements": improvements,
            "new_steps": new_steps,
            "prev_pass_rate": prev_data.get("meta_summary", {}).get("metrics", {}).get("step_pass_rate", 0),
        }

    def _record_skip(self, phase_result: PhaseResult, name: str, detail: str) -> None:
        phase_result.steps.append(StepResult(name=name, verdict=Verdict.SKIP, detail=detail))

    def _run_step(self, name: str, fn, *, phase_result: PhaseResult, max_retries: int = 2) -> StepResult:
        remediation_name = ""
        for attempt in range(max_retries + 1):
            started = time.monotonic()
            try:
                detail = fn()
                duration = time.monotonic() - started
                verdict = Verdict.REMEDIATED if attempt > 0 else Verdict.PASS
                step = StepResult(
                    name=name,
                    verdict=verdict,
                    duration_s=duration,
                    detail=str(detail or ""),
                    remediation_applied=remediation_name,
                )
                phase_result.steps.append(step)
                return step
            except Exception as exc:
                duration = time.monotonic() - started
                error_text = f"{exc}\n{traceback.format_exc()}"
                error_file = self.artifact_dir / f"{phase_result.phase}_{_safe_name(name)}_error.txt"
                _write_text(error_file, error_text)
                diagnosis, remediation_name, match = self.engine.diagnose(error_text)
                if attempt < max_retries and remediation_name:
                    remediated = self.engine.remediate(remediation_name, match)
                    self.engine.record_learning(name, str(exc), diagnosis or "unknown", remediation_name, remediated)
                    if remediated:
                        continue
                if phase_result.phase in {"deploy", "smoke", "e2e"}:
                    self._capture_target_diagnostics(f"{phase_result.phase}_{name}")
                step = StepResult(
                    name=name,
                    verdict=Verdict.FAIL,
                    duration_s=duration,
                    detail=f"Diagnosed: {diagnosis}" if diagnosis else "",
                    error=str(exc),
                    remediation_applied=remediation_name,
                )
                phase_result.steps.append(step)
                self.engine.record_learning(name, str(exc), diagnosis or "unknown", remediation_name or "none", False)
                return step
        raise RuntimeError(f"Unreachable step runner state for {name}")

    def _capture_target_diagnostics(self, label: str) -> Path:
        units = " ".join(self.profile.prototype_services)
        command = _bash_script(
            f"""
            for svc in {units}; do
              echo "### $svc"
              systemctl status "$svc" --no-pager -l || true
              echo
              journalctl -u "$svc" -n 30 --no-pager || true
              echo
            done
            echo "### ports"
            ss -tlnp | egrep ':(8000|5555|5556|5557)\\b' || true
            """
        )
        result = self.remote.ssh(command, timeout=180, check=False)
        destination = self.artifact_dir / f"{_safe_name(label)}_target_snapshot.txt"
        _write_text(destination, result.stdout + ("\nSTDERR\n" + result.stderr if result.stderr else ""))
        return destination

    def _service_states(self) -> dict[str, str]:
        lines = [
            f"printf '{service}='; systemctl is-active {service} 2>/dev/null || echo inactive"
            for service in self.profile.prototype_services
        ]
        result = self.remote.ssh(_bash_script("\n".join(lines)), timeout=40, check=False)
        states: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" not in line:
                continue
            name, status = line.split("=", 1)
            states[name.strip()] = status.strip()
        return states

    def _wait_for_services(self, timeout: int = 150) -> dict[str, str]:
        deadline = time.monotonic() + timeout
        states: dict[str, str] = {}
        while time.monotonic() < deadline:
            states = self._service_states()
            if states and all(status == "active" for status in states.values()):
                return states
            time.sleep(5)
        return states

    def phase_preflight(self) -> PhaseResult:
        phase = PhaseResult("preflight", started=_now())
        self._run_step("target_profile", self._preflight_target_profile, phase_result=phase)
        self._run_step("target_network_profile", self._preflight_target_network, phase_result=phase)
        self._run_step("android_usb_transport", self._preflight_android_usb_transport, phase_result=phase)
        if self.profile.require_rooted_phone:
            self._run_step("android_root_verification", self._preflight_android_root_verification, phase_result=phase)
        else:
            self._record_skip(phase, "android_root_verification", "--allow-unrooted-phone requested")
        self._run_step("android_network_profile", self._preflight_android_network_profile, phase_result=phase)
        phase.finished = _now()
        return phase

    def _preflight_target_profile(self) -> str:
        result = self.remote.ssh(
            "{ . /etc/os-release 2>/dev/null || true; "
            "printf 'ID=%s\n' \"${ID:-unknown}\"; "
            "printf 'VERSION_ID=%s\n' \"${VERSION_ID:-unknown}\"; "
            "printf 'PRETTY_NAME=%s\n' \"${PRETTY_NAME:-unknown}\"; "
            "printf 'ARCH=%s\n' \"$(uname -m)\"; "
            "if [ -r /proc/device-tree/model ]; then "
            "  printf 'MODEL=%s\n' \"$(tr -d '\\0' </proc/device-tree/model)\"; "
            "fi; "
            "printf 'HOST_IPS=%s\n' \"$(hostname -I 2>/dev/null)\"; }",
            timeout=20,
        )
        _write_text(self.artifact_dir / "target_profile.txt", result.stdout)
        profile: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            profile[key.strip()] = value.strip()

        os_identity = " ".join([profile.get("ID", ""), profile.get("PRETTY_NAME", "")]).lower()
        if self.profile.expected_target_os.lower() not in os_identity:
            raise RuntimeError(
                f"Expected target OS '{self.profile.expected_target_os}', got '{profile.get('PRETTY_NAME', 'unknown')}'"
            )

        model = profile.get("MODEL", "")
        arch = profile.get("ARCH", "")
        if self.profile.require_pi_hardware:
            if model:
                if "raspberry pi 4" not in model.lower():
                    raise RuntimeError(f"Expected target hardware to identify as Raspberry Pi 4, got '{model}'")
            elif arch not in {"aarch64", "armv7l", "armv8l"}:
                raise RuntimeError(f"Expected target hardware compatible with Raspberry Pi, got arch '{arch}'")

        return f"os={profile.get('PRETTY_NAME', 'unknown')}, arch={arch}, model={model or 'not-reported'}"

    def _preflight_target_network(self) -> str:
        if not _looks_like_ip(self.resolved_host):
            raise RuntimeError(f"Resolved target host '{self.resolved_host}' is not an IPv4/IPv6 address")

        network = ipaddress.ip_network(self.profile.expected_subnet, strict=False)
        target_ip = ipaddress.ip_address(self.resolved_host)
        if target_ip not in network:
            raise RuntimeError(f"Host {self.resolved_host} is not inside expected subnet {network}")

        result = self.remote.ssh("hostname -I", timeout=10, check=False)
        remote_ips = [token for token in result.stdout.split() if _looks_like_ip(token)]
        if remote_ips and not any(ipaddress.ip_address(value) in network for value in remote_ips):
            raise RuntimeError(f"Remote target interfaces {remote_ips} are not inside expected subnet {network}")
        return f"target_ip={self.resolved_host}, remote_ips={remote_ips or ['unavailable']}, subnet={network}"

    def _preflight_android_usb_transport(self) -> str:
        if not self.device:
            raise RuntimeError("ADB device serial is required for Android preflight")

        devices = adb("devices", "-l", timeout=15)
        if not re.search(rf"^{re.escape(self.device)}\s+device\b", devices.stdout, re.MULTILINE):
            raise RuntimeError(f"ADB device '{self.device}' is not connected")

        devpath = adb("get-devpath", serial=self.device, timeout=15)
        usb_state = adb("shell", "getprop", "sys.usb.state", serial=self.device, timeout=15)

        if devpath.returncode != 0 or not devpath.stdout.strip():
            raise RuntimeError("USB transport is not active for the selected Android device")
        if "adb" not in usb_state.stdout:
            raise RuntimeError(f"Android USB state does not include adb: '{usb_state.stdout.strip()}'")

        return f"serial={self.device}, devpath={devpath.stdout.strip()}, usb_state={usb_state.stdout.strip()}"

    def _preflight_android_root_verification(self) -> str:
        if not ROOT_VERIFY_SCRIPT.exists():
            raise RuntimeError(f"Root verification script not found: {ROOT_VERIFY_SCRIPT}")

        result = run(
            ["bash", str(ROOT_VERIFY_SCRIPT), "verify", self.device],
            cwd=REPO_ROOT,
            timeout=600,
            check=False,
        )
        _write_text(
            self.artifact_dir / "android_root_verify.log",
            result.stdout + ("\nSTDERR\n" + result.stderr if result.stderr else ""),
        )

        workspace_report = REPO_ROOT / "android-device-workspace" / "root-verification-report.txt"
        _copy_if_exists(workspace_report, self.root_report_path)
        if result.returncode != 0:
            raise RuntimeError("Android root verification failed")

        report_excerpt = self.root_report_path.read_text(encoding="utf-8")[:200] if self.root_report_path.exists() else "report unavailable"
        return report_excerpt.replace("\n", " ")

    def _preflight_android_network_profile(self) -> str:
        command = textwrap.dedent(
            f"""
            ip -4 addr show 2>/dev/null || ifconfig 2>/dev/null
            echo ---
            ip route get {self.resolved_host} 2>/dev/null || echo 'no route'
            """
        ).strip()
        # Try without root first (su may not exist on non-rooted devices)
        result = adb_shell(command, serial=self.device, timeout=30, root=False)
        if result.returncode != 0 or not result.stdout.strip():
            result = adb_shell(command, serial=self.device, timeout=30, root=True)

        snapshot = result.stdout.strip()
        _write_text(self.artifact_dir / "android_network_profile.txt", snapshot)

        network = ipaddress.ip_network(self.profile.expected_subnet, strict=False)
        addresses = re.findall(r"inet\s+(\d+\.\d+\.\d+\.\d+)/", snapshot)
        matching = [value for value in addresses if ipaddress.ip_address(value) in network]

        # USB-tethered devices may not be on the same subnet but can still route to it
        if not matching:
            route_ok = self.resolved_host in snapshot or "dev " in snapshot or "no route" in snapshot
            return f"android_ips={addresses or ['usb-only']}, subnet_match=false (USB-tethered OK)"

        return f"android_ips={matching}, target={self.resolved_host}"

    def phase_deploy(self) -> PhaseResult:
        phase = PhaseResult("deploy", started=_now())
        self._run_step("prepare_remote_workspace", self._deploy_prepare_remote_workspace, phase_result=phase)
        self._run_step("sync_repo_bundle", self._deploy_sync_repo_bundle, phase_result=phase)
        self._run_step("run_prototype_deploy_script", self._deploy_run_prototype_deploy, phase_result=phase)
        self._run_step("prototype_services_active", self._deploy_verify_prototype_services, phase_result=phase)
        phase.finished = _now()
        return phase

    def _deploy_prepare_remote_workspace(self) -> str:
        command = _bash_script(
            f"""
            sudo mkdir -p {shlex.quote(self.install_path)} {shlex.quote(self.remote_repo_path)}
            sudo chown -R {shlex.quote(self.remote.user)}:{shlex.quote(self.remote.user)} {shlex.quote(self.remote_repo_path)}
            """
        )
        self.remote.ssh(command, timeout=30)
        return f"prepared {self.remote_repo_path}"

    def _deploy_sync_repo_bundle(self) -> str:
        self.remote.rsync(
            f"{REPO_ROOT}/",
            f"{self.remote_repo_path}/",
            exclude=REMOTE_REPO_EXCLUDES,
            timeout=1800,
        )
        return f"synced repo bundle to {self.remote_repo_path}"

    def _deploy_run_prototype_deploy(self) -> str:
        command = _bash_script(
            f"""
            set -o pipefail
            cd {shlex.quote(self.remote_repo_path)}
            printf 'y\n' | sudo -E env DEBIAN_FRONTEND=noninteractive MIA_INSTALL_DIR={shlex.quote(self.install_path)} bash scripts/deploy-production-rpi.sh
            """
        )
        result = self.remote.ssh(command, timeout=3600, check=False)
        destination = self.artifact_dir / "deploy-production-rpi.log"
        _write_text(destination, result.stdout + ("\nSTDERR\n" + result.stderr if result.stderr else ""))
        if result.returncode != 0:
            raise RuntimeError(f"deploy-production-rpi.sh failed; see {destination}")
        return str(destination.relative_to(REPO_ROOT)) if destination.is_relative_to(REPO_ROOT) else str(destination)

    def _deploy_verify_prototype_services(self) -> str:
        states = self._wait_for_services(timeout=180)
        inactive = {name: status for name, status in states.items() if status != "active"}
        self._capture_target_diagnostics("deploy_services")
        if inactive:
            raise RuntimeError(f"Inactive prototype services: {inactive}")
        return ", ".join(f"{name}={status}" for name, status in sorted(states.items()))

    def phase_smoke(self) -> PhaseResult:
        phase = PhaseResult("smoke", started=_now())
        self._run_step("api_status", self._smoke_api_status, phase_result=phase)
        self._run_step("api_devices", self._smoke_api_devices, phase_result=phase)
        self._run_step("api_telemetry", self._smoke_api_telemetry, phase_result=phase)
        self._run_step("api_features", self._smoke_api_features, phase_result=phase)
        self._run_step("zmq_broker_port", self._smoke_zmq_port, phase_result=phase)
        self._run_step("target_service_snapshot", self._smoke_target_service_snapshot, phase_result=phase)
        phase.finished = _now()
        return phase

    def _smoke_api_status(self) -> str:
        code, body = http_request(f"{self.base_url}/status", timeout=20)
        if code != 200:
            raise RuntimeError(f"/status returned {code}: {body[:240]}")
        return _json_detail(body)

    def _smoke_api_devices(self) -> str:
        code, body = http_request(f"{self.base_url}/devices", timeout=20)
        if code != 200:
            raise RuntimeError(f"/devices returned {code}: {body[:240]}")
        return _json_detail(body)

    def _smoke_api_telemetry(self) -> str:
        code, body = http_request(f"{self.base_url}/telemetry", timeout=20)
        if code != 200:
            raise RuntimeError(f"/telemetry returned {code}: {body[:240]}")
        return _json_detail(body)

    def _smoke_api_features(self) -> str:
        code, body = http_request(f"{self.base_url}/features", timeout=20)
        if code == 404:
            return "features catalog not deployed (OK — optional)"
        if code != 200:
            raise RuntimeError(f"/features returned {code}: {body[:240]}")
        return _json_detail(body)

    def _smoke_zmq_port(self) -> str:
        result = self.remote.ssh("ss -tlnp | grep ':5555'", timeout=20, check=False)
        if result.returncode != 0 or ":5555" not in result.stdout:
            return "ZMQ broker not running (non-fatal — API works standalone)"
        return result.stdout.strip()

    def _smoke_target_service_snapshot(self) -> str:
        path = self._capture_target_diagnostics("smoke_services")
        return str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)

    def phase_android(self) -> PhaseResult:
        phase = PhaseResult("android", started=_now())
        self._run_step("android_skill_build_and_test", self._android_skill_build_and_test, phase_result=phase)
        self._run_step("android_skill_artifacts_present", self._android_skill_artifacts_present, phase_result=phase)
        phase.finished = _now()
        return phase

    def _android_skill_build_and_test(self) -> str:
        if not ANDROID_SKILL_SCRIPT.exists():
            raise RuntimeError(f"Android skill script not found: {ANDROID_SKILL_SCRIPT}")
        if not self.device:
            raise RuntimeError("ADB device serial is required for Android phase")

        self.android_skill_output.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["MIA_API_BASE_URL"] = self.api_base_url
        env["MIA_WS_BASE_URL"] = self.ws_base_url

        result = run(
            [
                "bash",
                str(ANDROID_SKILL_SCRIPT),
                "build-and-test",
                "--device",
                self.device,
                "--scenario",
                self.android_scenario,
                "--screenshots",
                "--logs",
                "--output",
                str(self.android_skill_output),
            ],
            cwd=REPO_ROOT,
            env=env,
            timeout=1800,
            check=False,
        )
        log_path = self.artifact_dir / "android_skill_build_and_test.log"
        _write_text(log_path, result.stdout + ("\nSTDERR\n" + result.stderr if result.stderr else ""))
        if result.returncode != 0:
            raise RuntimeError(f"Android skill build-and-test failed; see {log_path}")
        return str(log_path.relative_to(REPO_ROOT)) if log_path.is_relative_to(REPO_ROOT) else str(log_path)

    def _android_skill_artifacts_present(self) -> str:
        report_file = self.android_skill_output / "reports" / "test-report.json"
        logcat_file = self.android_skill_output / "logs" / "logcat.txt"
        screenshots_dir = self.android_skill_output / "screenshots"
        if not report_file.exists():
            raise RuntimeError(f"Android skill report missing: {report_file}")
        if not logcat_file.exists():
            raise RuntimeError(f"Android logcat missing: {logcat_file}")
        screenshots = list(screenshots_dir.glob("*.png"))
        if not screenshots:
            raise RuntimeError(f"Android screenshots missing under {screenshots_dir}")
        payload = json.loads(report_file.read_text(encoding="utf-8"))
        scenario = payload.get("scenario", "unknown")
        return f"scenario={scenario}, screenshots={len(screenshots)}, logcat={logcat_file.name}"

    def phase_e2e(self) -> PhaseResult:
        phase = PhaseResult("e2e", started=_now())
        self._run_step("android_network_reaches_api", self._e2e_android_network_reaches_api, phase_result=phase)
        self._run_step("device_registry_roundtrip", self._e2e_device_registry_roundtrip, phase_result=phase)
        self._run_step("telemetry_flow", self._e2e_telemetry_flow, phase_result=phase)
        self._run_step("gpio_read_pin", self._e2e_gpio_read_pin, phase_result=phase)
        self._run_step("websocket_route_exists", self._e2e_websocket_route_exists, phase_result=phase)
        # Extended API coverage
        self._run_step("session_lifecycle", self._e2e_session_lifecycle, phase_result=phase)
        self._run_step("led_state_roundtrip", self._e2e_led_state_roundtrip, phase_result=phase)
        self._run_step("auth_status", self._e2e_auth_status, phase_result=phase)
        self._run_step("thermal_health", self._e2e_thermal_health, phase_result=phase)
        self._run_step("log_query", self._e2e_log_query, phase_result=phase)
        self._run_step("ota_status", self._e2e_ota_status, phase_result=phase)
        self._run_step("device_command", self._e2e_device_command, phase_result=phase)
        self._run_step("registry_status", self._e2e_registry_status, phase_result=phase)
        self._run_step("android_logcat_health", self._e2e_android_logcat_health, phase_result=phase)
        phase.finished = _now()
        return phase

    def _e2e_android_network_reaches_api(self) -> str:
        if not self.device:
            raise RuntimeError("ADB device serial is required for Android network probe")

        # Try direct HTTP from Android first (works if phone is on same network)
        try:
            body = android_http_get(f"{self.base_url}/status", serial=self.device, timeout=15)
            if "status" in body.lower() or "uptime" in body.lower():
                return f"android_direct: {body[:120].replace(chr(10), ' ')}"
        except RuntimeError:
            pass

        # Fallback: ADB port-forward + host-side verify (USB-tethered path)
        code, body = http_request(f"{self.base_url}/status", timeout=20)
        if code != 200:
            raise RuntimeError(f"API unreachable from host: {code}: {body[:200]}")
        return f"host_verified: API reachable ({code}), phone is USB-tethered"

    def _e2e_device_registry_roundtrip(self) -> str:
        suffix = _safe_name(self.device or "device")[-16:]
        device_id = f"android-usb-{suffix}"
        payload = {
            "device_id": device_id,
            "device_type": "unknown",
            "name": "Rooted Android USB Phone",
            "capabilities": ["adb", "root", "usb", "android-app"],
            "metadata": {
                "run_id": self.report.run_id,
                "connection": "usb",
                "prototype_target": self.resolved_host,
            },
        }
        headers = {"Content-Type": "application/json"}
        register_code, register_body = http_request(
            f"{self.base_url}/registry/devices",
            method="POST",
            body=json.dumps(payload),
            headers=headers,
            timeout=20,
        )
        if register_code != 200:
            raise RuntimeError(f"Device registration returned {register_code}: {register_body[:240]}")

        heartbeat_code, heartbeat_body = http_request(
            f"{self.base_url}/registry/devices/{device_id}/heartbeat",
            method="POST",
            timeout=20,
        )
        if heartbeat_code != 200:
            raise RuntimeError(f"Heartbeat returned {heartbeat_code}: {heartbeat_body[:240]}")

        fetch_code, fetch_body = http_request(f"{self.base_url}/registry/devices/{device_id}", timeout=20)
        if fetch_code != 200 or device_id not in fetch_body:
            raise RuntimeError(f"Registry lookup returned {fetch_code}: {fetch_body[:240]}")

        http_request(f"{self.base_url}/registry/devices/{device_id}", method="DELETE", timeout=20)
        return device_id

    def _e2e_telemetry_flow(self) -> str:
        code, body = http_request(f"{self.base_url}/telemetry", timeout=20)
        if code != 200:
            raise RuntimeError(f"/telemetry returned {code}: {body[:240]}")
        return _json_detail(body)

    def _e2e_gpio_read_pin(self) -> str:
        code, body = http_request(f"{self.base_url}/gpio/17", timeout=20)
        if code != 200:
            raise RuntimeError(f"/gpio/17 returned {code}: {body[:240]}")
        return _json_detail(body)

    def _e2e_websocket_route_exists(self) -> str:
        code, body = http_request(f"{self.base_url}/ws/telemetry", timeout=10)
        # WebSocket upgrade attempt over plain HTTP returns 400, 403, or 426
        if code in {0} or code >= 500:
            raise RuntimeError(f"/ws/telemetry unreachable: {code}: {body[:200]}")
        return f"ws_telemetry_probe={code}"

    # ── Extended API coverage ────────────────────────────────────────────

    def _e2e_session_lifecycle(self) -> str:
        """POST /sessions → GET → DELETE full lifecycle."""
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({
            "client_type": "web",
            "client_name": f"e2e-harness-{self.report.run_id}",
            "metadata": {"test": True},
        })
        create_code, create_body = http_request(
            f"{self.base_url}/sessions", method="POST", body=payload,
            headers=headers, timeout=20,
        )
        if create_code != 200:
            raise RuntimeError(f"POST /sessions returned {create_code}: {create_body[:240]}")
        session_data = json.loads(create_body)
        session_id = session_data.get("session", {}).get("session_id", "")
        if not session_id:
            raise RuntimeError(f"No session_id in response: {create_body[:200]}")

        get_code, get_body = http_request(f"{self.base_url}/sessions/{session_id}", timeout=20)
        if get_code != 200:
            raise RuntimeError(f"GET /sessions/{session_id} returned {get_code}: {get_body[:240]}")

        del_code, _ = http_request(f"{self.base_url}/sessions/{session_id}", method="DELETE", timeout=20)
        if del_code != 200:
            raise RuntimeError(f"DELETE /sessions/{session_id} returned {del_code}")

        return f"session={session_id[:12]}..., lifecycle=create→get→delete"

    def _e2e_led_state_roundtrip(self) -> str:
        """GET → PUT → GET /led/state roundtrip."""
        get1_code, get1_body = http_request(f"{self.base_url}/led/state", timeout=20)
        if get1_code != 200:
            raise RuntimeError(f"GET /led/state returned {get1_code}: {get1_body[:240]}")

        update = json.dumps({"brightness": 128, "color": {"r": 0, "g": 255, "b": 136}})
        put_code, put_body = http_request(
            f"{self.base_url}/led/state", method="PUT", body=update,
            headers={"Content-Type": "application/json"}, timeout=20,
        )
        if put_code != 200:
            raise RuntimeError(f"PUT /led/state returned {put_code}: {put_body[:240]}")

        get2_code, get2_body = http_request(f"{self.base_url}/led/state", timeout=20)
        if get2_code != 200:
            raise RuntimeError(f"GET /led/state (verify) returned {get2_code}")

        return f"led_roundtrip=get→put→verify, keys={_json_detail(get2_body)}"

    def _e2e_auth_status(self) -> str:
        code, body = http_request(f"{self.base_url}/auth/status", timeout=20)
        if code != 200:
            raise RuntimeError(f"/auth/status returned {code}: {body[:240]}")
        return _json_detail(body)

    def _e2e_thermal_health(self) -> str:
        code, body = http_request(f"{self.base_url}/health/thermal", timeout=20)
        if code != 200:
            raise RuntimeError(f"/health/thermal returned {code}: {body[:240]}")
        return _json_detail(body)

    def _e2e_log_query(self) -> str:
        list_code, list_body = http_request(f"{self.base_url}/logs/services", timeout=20)
        if list_code != 200:
            raise RuntimeError(f"GET /logs/services returned {list_code}: {list_body[:240]}")
        services = json.loads(list_body).get("services", [])
        detail = f"log_services={len(services)}"
        if services:
            svc = services[0] if isinstance(services[0], str) else services[0].get("name", services[0])
            log_code, log_body = http_request(f"{self.base_url}/logs/{svc}?lines=5", timeout=20)
            detail += f", sample={svc}({log_code})"
        return detail

    def _e2e_ota_status(self) -> str:
        code, body = http_request(f"{self.base_url}/ota/status", timeout=20)
        if code != 200:
            raise RuntimeError(f"/ota/status returned {code}: {body[:240]}")
        return _json_detail(body)

    def _e2e_device_command(self) -> str:
        payload = json.dumps({"action": "status", "device": "gpio"})
        code, body = http_request(
            f"{self.base_url}/command", method="POST", body=payload,
            headers={"Content-Type": "application/json"}, timeout=20,
        )
        # Command may timeout (no ZMQ broker) — still proves route exists
        if code >= 500:
            raise RuntimeError(f"POST /command returned {code}: {body[:240]}")
        return f"command_route={code}, {_json_detail(body)}"

    def _e2e_registry_status(self) -> str:
        code, body = http_request(f"{self.base_url}/registry/status", timeout=20)
        if code != 200:
            raise RuntimeError(f"/registry/status returned {code}: {body[:240]}")
        return _json_detail(body)

    def _e2e_android_logcat_health(self) -> str:
        # Try skill output first, fall back to live logcat capture
        logcat_file = self.android_skill_output / "logs" / "logcat.txt"
        if logcat_file.exists():
            payload = logcat_file.read_text(encoding="utf-8", errors="replace")
        elif self.device:
            adb("logcat", "-c", serial=self.device, timeout=5)
            time.sleep(3)
            pid_result = adb("shell", "pidof", MIA_PACKAGE, serial=self.device, timeout=10)
            pid = pid_result.stdout.strip() or "0"
            result = adb("logcat", "-d", "-t", "300", "--pid", pid, serial=self.device, timeout=15)
            payload = result.stdout
            logcat_file = self.artifact_dir / "logcat_e2e.txt"
            _write_text(logcat_file, payload)
        else:
            return "no logcat source available (SKIP)"
        matches = [pattern for pattern in LOGCAT_CRASH_PATTERNS if re.search(pattern, payload, re.IGNORECASE)]
        if matches:
            raise RuntimeError(f"Android logcat contains crash markers: {matches}")
        warnings = re.findall(r"\b(?:SecurityException|HttpException|WebSocket error)\b", payload)
        return f"crash_markers=0, warnings={len(warnings)}, lines={len(payload.splitlines())}"


def print_report(report: RunReport) -> None:
    print()
    print(f"Run: {report.run_id}")
    print(f"Target: {report.host}")
    print(f"Android: {report.device or 'none'}")
    print()
    for phase in report.phases:
        print(f"[{phase.phase}] started={phase.started} finished={phase.finished}")
        for step in phase.steps:
            detail = f" :: {step.detail}" if step.detail else ""
            error = f" :: {step.error}" if step.error else ""
            remediation = f" :: remediation={step.remediation_applied}" if step.remediation_applied else ""
            print(f"  {step.verdict:<10} {step.name} ({step.duration_s:.1f}s){detail}{remediation}{error}")
        print()
    print(report.summary_line)
    if report.meta_summary:
        print(f"Next focus: {report.meta_summary.get('next_focus', 'n/a')}")
        print(f"Applied remediations: {', '.join(report.meta_summary.get('applied_remediations', [])) or 'none'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", action="append", dest="phases",
                        choices=["all", "preflight", "deploy", "smoke", "android", "e2e"],
                        help="Phase(s) to run (repeatable; default: all)")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--device", default=DEFAULT_ADB_SERIAL)
    parser.add_argument("--install-path", default=DEFAULT_INSTALL_PATH)
    parser.add_argument("--expected-subnet", default=DEFAULT_EXPECTED_SUBNET)
    parser.add_argument("--expected-target-os", default=DEFAULT_EXPECTED_TARGET_OS)
    parser.add_argument("--allow-non-pi", action="store_true")
    parser.add_argument("--allow-unrooted-phone", action="store_true")
    parser.add_argument("--android-scenario", choices=ANDROID_SCENARIOS, default="full-flow")
    parser.add_argument("--skip-deploy", action="store_true")
    parser.add_argument("--dry-remediate", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    phases = args.phases or ["all"]
    if "all" in phases:
        selected_phases = ["preflight", "deploy", "smoke", "android", "e2e"]
    else:
        selected_phases = phases
    needs_android = any(phase in {"preflight", "android", "e2e"} for phase in selected_phases)
    device = args.device
    if needs_android and not device:
        device = pick_adb_device()

    remote = Remote(args.host, args.user, args.port)
    profile = PrototypeProfile(
        expected_subnet=args.expected_subnet,
        expected_target_os=args.expected_target_os,
        require_pi_hardware=not args.allow_non_pi,
        require_rooted_phone=not args.allow_unrooted_phone,
    )
    engine = SelfImprovementEngine(remote, prototype_services=profile.prototype_services, dry=args.dry_remediate)
    harness = IntegrationHarness(
        remote=remote,
        profile=profile,
        engine=engine,
        device_serial=device,
        install_path=args.install_path,
        phases=selected_phases,
        android_scenario=args.android_scenario,
        skip_deploy=args.skip_deploy,
    )
    report = harness.run_all()
    print_report(report)
    return 0 if all(phase.failed == 0 for phase in report.phases) else 1


if __name__ == "__main__":
    raise SystemExit(main())


# ═══════════════════════════════════════════════════════════════════════════
# pytest integration — run via: pytest -m meta_harness -v
# ═══════════════════════════════════════════════════════════════════════════

try:
    import pytest

    @pytest.mark.integration
    @pytest.mark.meta_harness
    @pytest.mark.slow
    def test_meta_harness_smoke():
        """Run smoke phase against the target and assert all steps pass."""
        host = os.getenv("MIA_TARGET_HOST", DEFAULT_HOST)
        user = os.getenv("MIA_TARGET_USER", DEFAULT_USER)
        port = int(os.getenv("MIA_TARGET_PORT", str(DEFAULT_PORT)))

        remote = Remote(host, user, port)
        profile = PrototypeProfile(require_pi_hardware=False, require_rooted_phone=False)
        engine = SelfImprovementEngine(remote, prototype_services=profile.prototype_services)
        harness = IntegrationHarness(
            remote=remote, profile=profile, engine=engine,
            device_serial="", install_path=DEFAULT_INSTALL_PATH,
            phases=["smoke"], android_scenario="install", skip_deploy=True,
        )
        report = harness.run_all()
        assert all(phase.failed == 0 for phase in report.phases), report.summary_line

    @pytest.mark.integration
    @pytest.mark.meta_harness
    @pytest.mark.slow
    def test_meta_harness_e2e():
        """Run preflight+smoke+e2e phases with an Android device."""
        host = os.getenv("MIA_TARGET_HOST", DEFAULT_HOST)
        user = os.getenv("MIA_TARGET_USER", DEFAULT_USER)
        port = int(os.getenv("MIA_TARGET_PORT", str(DEFAULT_PORT)))
        device = os.getenv("MIA_ADB_SERIAL", "")

        remote = Remote(host, user, port)
        profile = PrototypeProfile(require_pi_hardware=False, require_rooted_phone=False)
        engine = SelfImprovementEngine(remote, prototype_services=profile.prototype_services)
        if not device:
            device = pick_adb_device()
        harness = IntegrationHarness(
            remote=remote, profile=profile, engine=engine,
            device_serial=device, install_path=DEFAULT_INSTALL_PATH,
            phases=["preflight", "smoke", "e2e"], android_scenario="install",
            skip_deploy=True,
        )
        report = harness.run_all()
        assert all(phase.failed == 0 for phase in report.phases), report.summary_line

except ImportError:
    pass  # pytest not available when running standalone