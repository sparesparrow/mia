#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import sys
import time
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

from utils import CommandResult, create_whole_dir_path, execute_command


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.ai_self_improvement import (  # noqa: E402
    CycleMetrics,
    IMPROVEMENT_TARGETS,
    INITIAL_METRICS,
    KnowledgeBase,
    Pattern,
)


ANDROID_BUILD_FILE = PROJECT_ROOT / "apps/android/app/build.gradle"
ANDROID_MANIFEST = PROJECT_ROOT / "apps/android/app/src/main/AndroidManifest.xml"
ANDROID_ARTIFACT_ROOT = PROJECT_ROOT / "apps/android/test-artifacts"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "test-artifacts/integration"
DEFAULT_KB_PATH = (
    PROJECT_ROOT / "orchestration/ai_self_improvement/data/integration_harness_knowledge_base.json"
)
DEFAULT_STATE_PATH = (
    PROJECT_ROOT / "orchestration/ai_self_improvement/data/integration_harness_state.json"
)
REQUIRED_PI_SERVICES = [
    "bluetooth",
    "zmq-broker",
    "mia-api",
    "mia-gpio-worker",
    "mia-ble-advertiser",
    "mia-ble-obd",
]
OPTIONAL_PI_SERVICES = [
    "mia-serial-bridge",
    "mia-obd-worker",
]
BLE_DEVICE_NAME = "MIA OBD-II Adapter"


@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    duration_s: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)


@dataclass
class HarnessConfig:
    rpi_host: str
    rpi_user: str
    device_serial: Optional[str]
    scenario: str
    output_root: Path
    deploy_pi: bool
    run_android: bool
    run_agent_analysis: bool
    ssh_port: int
    ssh_key: Optional[Path]
    subnet: str
    deploy_timeout: int
    android_timeout: int
    kb_path: Path
    state_path: Path


class PrototypeIntegrationHarness:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.output_dir = create_whole_dir_path(self.config.output_root / self.timestamp)
        self.android_dir = create_whole_dir_path(self.output_dir / "android")
        self.pi_dir = create_whole_dir_path(self.output_dir / "pi")
        self.reports_dir = create_whole_dir_path(self.output_dir / "reports")
        self.meta_dir = create_whole_dir_path(self.output_dir / "meta")
        self.checks: List[CheckResult] = []
        self.package_name = self._extract_package_name()
        self.main_activity = self._extract_main_activity()
        self.resolved_rpi_host = self._resolve_host(self.config.rpi_host)
        self.api_base_url = f"http://{self.resolved_rpi_host}:8000/"
        self.ws_base_url = f"ws://{self.resolved_rpi_host}:8000"
        self.android_artifact_source: Optional[Path] = None
        self.android_artifact_copy: Optional[Path] = None
        self.summary_path = self.reports_dir / "summary.json"
        self.report_path = self.reports_dir / "report.md"

    def _append_check(
        self,
        name: str,
        status: str,
        message: str,
        duration_s: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[Path]] = None,
    ) -> None:
        self.checks.append(
            CheckResult(
                name=name,
                status=status,
                message=message,
                duration_s=round(duration_s, 3),
                details=details or {},
                artifacts=[str(path) for path in (artifacts or [])],
            )
        )

    def _extract_package_name(self) -> str:
        content = ANDROID_BUILD_FILE.read_text(encoding="utf-8")
        match = re.search(r'applicationId\s+"([^"]+)"', content)
        if not match:
            raise RuntimeError(f"Could not determine Android package from {ANDROID_BUILD_FILE}")
        return match.group(1)

    def _extract_main_activity(self) -> str:
        tree = ElementTree.parse(ANDROID_MANIFEST)
        root = tree.getroot()
        android_ns = "{http://schemas.android.com/apk/res/android}"

        for activity in root.findall("application/activity"):
            name = activity.attrib.get(f"{android_ns}name")
            intent_filter = activity.find("intent-filter")
            if not name or intent_filter is None:
                continue

            has_main = any(
                action.attrib.get(f"{android_ns}name") == "android.intent.action.MAIN"
                for action in intent_filter.findall("action")
            )
            has_launcher = any(
                category.attrib.get(f"{android_ns}name") == "android.intent.category.LAUNCHER"
                for category in intent_filter.findall("category")
            )
            if has_main and has_launcher:
                return name

        raise RuntimeError(f"Could not determine launcher activity from {ANDROID_MANIFEST}")

    def _resolve_host(self, host: str) -> str:
        try:
            return socket.gethostbyname(host)
        except OSError:
            return host

    def _ssh_command(self, remote_command: str, timeout: int = 30) -> CommandResult:
        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=6",
            "-p",
            str(self.config.ssh_port),
        ]
        if self.config.ssh_key:
            command.extend(["-i", str(self.config.ssh_key)])
        command.append(f"{self.config.rpi_user}@{self.config.rpi_host}")
        command.append(remote_command)
        return execute_command(command, cwd=PROJECT_ROOT, timeout=timeout)

    def _write_command_logs(self, prefix: str, result: CommandResult, directory: Path) -> List[Path]:
        stdout_path = directory / f"{prefix}.stdout.log"
        stderr_path = directory / f"{prefix}.stderr.log"
        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        return [stdout_path, stderr_path]

    def _load_json_file(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _latest_android_artifacts(self) -> Dict[str, Path]:
        if not ANDROID_ARTIFACT_ROOT.exists():
            return {}
        return {
            path.name: path
            for path in ANDROID_ARTIFACT_ROOT.iterdir()
            if path.is_dir()
        }

    def _record_static_context(self) -> None:
        self._append_check(
            "config.android_package",
            "pass",
            f"Using Android package {self.package_name} and activity {self.main_activity}",
            details={
                "package_name": self.package_name,
                "launcher_activity": self.main_activity,
            },
        )
        network_status = "pass" if self.resolved_rpi_host.startswith("192.168.200.") else "warning"
        self._append_check(
            "config.network_topology",
            network_status,
            f"Pi host resolves to {self.resolved_rpi_host}",
            details={
                "input_host": self.config.rpi_host,
                "resolved_host": self.resolved_rpi_host,
                "expected_subnet": self.config.subnet,
                "api_base_url": self.api_base_url,
                "ws_base_url": self.ws_base_url,
            },
        )

    def run_local_preflight(self) -> bool:
        required_commands = ["adb", "ssh", "curl", "bash"]
        all_ok = True
        for command_name in required_commands:
            result = execute_command(["bash", "-lc", f"command -v {command_name}"])
            status = "pass" if result.succeeded else "fail"
            message = result.stdout.strip() or f"{command_name} not found"
            self._append_check(
                f"local.command.{command_name}",
                status,
                message,
                duration_s=result.duration_s,
            )
            all_ok &= result.succeeded

        device_serial = self.config.device_serial or self._detect_android_device()
        if device_serial:
            self.config.device_serial = device_serial
            transport = "USB" if ":" not in device_serial else "network-adb"
            status = "pass" if transport == "USB" else "warning"
            self._append_check(
                "android.device.selected",
                status,
                f"Using Android device {device_serial} via {transport}",
                details={"device_serial": device_serial},
            )
        else:
            self._append_check(
                "android.device.selected",
                "fail",
                "No authorized Android device detected",
            )
            return False

        device_ok = self._check_android_device_ready(device_serial)
        network_ok = self._check_android_network(device_serial)
        root_ok = self._check_android_root(device_serial)
        return all_ok and device_ok and network_ok and root_ok

    def _detect_android_device(self) -> Optional[str]:
        result = execute_command(["adb", "devices"])
        for line in result.stdout.splitlines():
            if line.endswith("\tdevice"):
                return line.split()[0]
        return None

    def _check_android_device_ready(self, device_serial: str) -> bool:
        result = execute_command(
            ["adb", "-s", device_serial, "shell", "getprop", "ro.product.model"],
            timeout=15,
        )
        status = "pass" if result.succeeded else "fail"
        message = result.stdout.strip() if result.succeeded else result.stderr.strip() or "ADB shell unavailable"
        self._append_check(
            "android.device.ready",
            status,
            message,
            duration_s=result.duration_s,
        )
        return result.succeeded

    def _check_android_network(self, device_serial: str) -> bool:
        result = execute_command(
            ["adb", "-s", device_serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"],
            timeout=15,
        )
        if not result.succeeded:
            self._append_check(
                "android.device.network",
                "warning",
                "Could not determine Android Wi-Fi address",
                duration_s=result.duration_s,
                details={"stderr": result.stderr.strip()},
            )
            return True

        match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
        if not match:
            self._append_check(
                "android.device.network",
                "warning",
                "Android Wi-Fi address not available",
                duration_s=result.duration_s,
            )
            return True

        ip_address = match.group(1)
        status = "pass" if ip_address.startswith("192.168.200.") else "warning"
        self._append_check(
            "android.device.network",
            status,
            f"Android Wi-Fi address {ip_address}",
            duration_s=result.duration_s,
            details={"ip_address": ip_address},
        )
        return True

    def _check_android_root(self, device_serial: str) -> bool:
        result = execute_command(
            ["adb", "-s", device_serial, "shell", "su", "-c", "id"],
            timeout=20,
        )
        status = "pass" if result.succeeded and "uid=0" in result.stdout else "warning"
        message = (
            result.stdout.strip()
            if result.succeeded and result.stdout.strip()
            else "Root shell not confirmed via adb shell su -c id"
        )
        self._append_check(
            "android.device.root",
            status,
            message,
            duration_s=result.duration_s,
        )
        return True

    def run_pi_preflight(self) -> bool:
        checks = [
            ("pi.ssh.access", "uname -srmo", "Remote host reachable over SSH"),
            ("pi.os.release", "source /etc/os-release && printf '%s %s' \"$ID\" \"$VERSION_ID\"", "Remote OS detected"),
            ("pi.systemd.available", "systemctl --version | head -1", "systemd available"),
            ("pi.apt.available", "command -v apt-get", "apt-get available"),
            ("pi.sudo.noninteractive", "sudo -n true", "Passwordless sudo available"),
            ("pi.bluetooth.adapter", "hciconfig hci0", "Bluetooth adapter visible"),
        ]
        all_ok = True
        for name, remote_command, success_message in checks:
            result = self._ssh_command(remote_command)
            is_kali = name == "pi.os.release" and "kali" in result.stdout.lower()
            status = "pass" if result.succeeded else "fail"
            if name == "pi.os.release" and result.succeeded and not is_kali:
                status = "warning"
            if name == "pi.bluetooth.adapter" and not result.succeeded:
                status = "warning"
            if name == "pi.sudo.noninteractive" and not result.succeeded:
                status = "fail"
            message = success_message if result.succeeded else result.stderr.strip() or result.stdout.strip() or success_message
            if name == "pi.os.release" and result.succeeded:
                message = f"Remote OS: {result.stdout.strip()}"
            artifacts = self._write_command_logs(name.replace(".", "_"), result, self.pi_dir)
            self._append_check(
                name,
                status,
                message,
                duration_s=result.duration_s,
                details={
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                },
                artifacts=artifacts,
            )
            if status == "fail":
                all_ok = False
        return all_ok

    def deploy_pi(self) -> bool:
        env = {
            "RPI_PORT": str(self.config.ssh_port),
            "SUBNET": self.config.subnet,
        }
        if self.config.ssh_key:
            env["SSH_KEY"] = str(self.config.ssh_key)

        deploy_script = PROJECT_ROOT / "scripts/deploy-mia-rpi.sh"
        result = execute_command(
            ["bash", str(deploy_script), self.config.rpi_host, self.config.rpi_user],
            cwd=PROJECT_ROOT,
            env=env,
            timeout=self.config.deploy_timeout,
        )
        artifacts = self._write_command_logs("deploy_mia_rpi", result, self.pi_dir)
        self._append_check(
            "pi.deploy",
            "pass" if result.succeeded else "fail",
            "Pi deploy completed" if result.succeeded else "Pi deploy failed",
            duration_s=result.duration_s,
            details={
                "returncode": result.returncode,
                "host": self.config.rpi_host,
            },
            artifacts=artifacts,
        )
        return result.succeeded

    def collect_pi_health(self) -> None:
        for service_name in REQUIRED_PI_SERVICES + OPTIONAL_PI_SERVICES:
            service_check = self._wait_for_remote_service(service_name)
            artifacts = self._write_command_logs(f"service_{service_name}", service_check, self.pi_dir)
            final_state = service_check.stdout.strip() or service_check.stderr.strip() or "unknown"
            if final_state == "active":
                status = "pass"
            elif final_state == "activating":
                status = "warning"
            elif service_name in OPTIONAL_PI_SERVICES:
                status = "warning"
            else:
                status = "fail"
            self._append_check(
                f"pi.service.{service_name}",
                status,
                final_state,
                duration_s=service_check.duration_s,
                details={
                    "observed_states": service_check.stderr.strip().splitlines(),
                },
                artifacts=artifacts,
            )

            journal = self._ssh_command(
                f"journalctl -u {service_name} --no-pager -n 80",
                timeout=45,
            )
            journal_path = self.pi_dir / f"journal_{service_name}.log"
            journal_path.write_text(journal.stdout or journal.stderr, encoding="utf-8")

        status_result = self._wait_for_http_endpoint(f"http://{self.resolved_rpi_host}:8000/status")
        artifacts = self._write_command_logs("pi_status_endpoint", status_result, self.pi_dir)
        self._append_check(
            "pi.api.status",
            "pass" if status_result.succeeded else "fail",
            "Pi /status responded" if status_result.succeeded else "Pi /status unavailable",
            duration_s=status_result.duration_s,
            details={
                "response": status_result.stdout.strip(),
                "attempt_log": status_result.stderr.strip().splitlines(),
            },
            artifacts=artifacts,
        )

        features_result = execute_command(["curl", "-fsS", f"http://{self.resolved_rpi_host}:8000/features"], timeout=20)
        artifacts = self._write_command_logs("pi_features_endpoint", features_result, self.pi_dir)
        self._append_check(
            "pi.api.features",
            "pass" if features_result.succeeded else "warning",
            "Pi /features responded" if features_result.succeeded else "Pi /features unavailable",
            duration_s=features_result.duration_s,
            artifacts=artifacts,
        )

    def _wait_for_remote_service(self, service_name: str, retries: int = 5, delay_s: int = 5) -> CommandResult:
        observations: List[str] = []
        total_duration = 0.0
        last_result = CommandResult(command="", returncode=1, stdout="", stderr="", duration_s=0.0)

        for attempt in range(1, retries + 1):
            result = self._ssh_command(f"systemctl is-active {service_name}")
            total_duration += result.duration_s
            state = result.stdout.strip() or result.stderr.strip() or "unknown"
            observations.append(f"attempt {attempt}: {state}")
            last_result = result
            if state == "active":
                break
            if attempt < retries:
                time.sleep(delay_s)

        return CommandResult(
            command=last_result.command,
            returncode=last_result.returncode,
            stdout=last_result.stdout,
            stderr="\n".join(observations),
            duration_s=round(total_duration, 3),
        )

    def _wait_for_http_endpoint(self, url: str, retries: int = 6, delay_s: int = 5) -> CommandResult:
        attempts: List[str] = []
        total_duration = 0.0
        last_result = CommandResult(command="", returncode=1, stdout="", stderr="", duration_s=0.0)

        for attempt in range(1, retries + 1):
            result = execute_command(["curl", "-fsS", url], timeout=20)
            total_duration += result.duration_s
            last_result = result
            if result.succeeded:
                attempts.append(f"attempt {attempt}: success")
                break
            attempts.append(f"attempt {attempt}: {result.stderr.strip() or result.stdout.strip() or 'failed'}")
            if attempt < retries:
                time.sleep(delay_s)

        return CommandResult(
            command=last_result.command,
            returncode=last_result.returncode,
            stdout=last_result.stdout,
            stderr="\n".join(attempts),
            duration_s=round(total_duration, 3),
        )

    def run_android_orchestrator(self) -> None:
        if not self.config.device_serial:
            self._append_check(
                "android.orchestrator",
                "skip",
                "Android orchestrator skipped because no device was selected",
            )
            return

        before = self._latest_android_artifacts()
        env = {
            "MIA_API_BASE_URL": self.api_base_url,
            "MIA_WS_BASE_URL": self.ws_base_url,
        }
        result = execute_command(
            [
                "bash",
                str(PROJECT_ROOT / "scripts/test-orchestrator.sh"),
                self.config.device_serial,
                self.config.scenario,
                "1",
            ],
            cwd=PROJECT_ROOT,
            env=env,
            timeout=self.config.android_timeout,
        )
        artifacts = self._write_command_logs("android_orchestrator", result, self.android_dir)
        self._append_check(
            "android.orchestrator",
            "pass" if result.succeeded else "fail",
            "Android orchestrator finished" if result.succeeded else "Android orchestrator failed",
            duration_s=result.duration_s,
            details={
                "returncode": result.returncode,
                "api_base_url": self.api_base_url,
                "ws_base_url": self.ws_base_url,
                "package_name": self.package_name,
            },
            artifacts=artifacts,
        )

        self._capture_android_artifacts(before)
        self._verify_android_installation()
        self._analyze_android_logs()

    def _capture_android_artifacts(self, previous: Dict[str, Path]) -> None:
        after = self._latest_android_artifacts()
        new_paths = [path for name, path in after.items() if name not in previous]
        source = None
        if new_paths:
            source = sorted(new_paths, key=lambda item: item.stat().st_mtime)[-1]
        elif after:
            source = sorted(after.values(), key=lambda item: item.stat().st_mtime)[-1]

        if source is None:
            self._append_check(
                "android.artifacts.capture",
                "warning",
                "No Android test artifacts were produced",
            )
            return

        destination = self.android_dir / source.name
        shutil.copytree(source, destination, dirs_exist_ok=True)
        self.android_artifact_source = source
        self.android_artifact_copy = destination
        self._append_check(
            "android.artifacts.capture",
            "pass",
            f"Copied Android artifacts from {source.name}",
            artifacts=[destination],
        )

    def _verify_android_installation(self) -> None:
        if not self.config.device_serial:
            return

        result = execute_command(
            [
                "adb",
                "-s",
                self.config.device_serial,
                "shell",
                "pm",
                "list",
                "packages",
                self.package_name,
            ],
            timeout=20,
        )
        installed = self.package_name in result.stdout
        self._append_check(
            "android.package.installation",
            "pass" if installed else "fail",
            f"Package {self.package_name} installed" if installed else f"Package {self.package_name} not found on device",
            duration_s=result.duration_s,
        )

    def _find_logcat_file(self) -> Optional[Path]:
        if not self.android_artifact_copy:
            return None
        matches = sorted(self.android_artifact_copy.rglob("logcat*.txt"))
        return matches[-1] if matches else None

    def _analyze_android_logs(self) -> None:
        logcat_path = self._find_logcat_file()
        if logcat_path is None:
            self._append_check(
                "android.logcat.analysis",
                "warning",
                "No logcat artifact found for Android analysis",
            )
            return

        content = logcat_path.read_text(encoding="utf-8", errors="ignore")
        lowered = content.lower()
        crash_count = len(re.findall(r"fatal exception|androidruntime", lowered))
        ble_mentions = len(re.findall(r"ble|bluetooth|gatt|obd", lowered))
        device_seen = BLE_DEVICE_NAME.lower() in lowered
        websocket_seen = "websocket" in lowered and ("connected" in lowered or "established" in lowered)

        status = "pass"
        message = "Android logcat captured BLE and backend evidence"
        if crash_count > 0:
            status = "fail"
            message = f"Android logcat contains {crash_count} crash indicators"
        elif not device_seen and ble_mentions == 0:
            status = "warning"
            message = "Android logcat did not capture BLE discovery evidence"
        elif not websocket_seen:
            status = "warning"
            message = "Android logcat did not capture WebSocket connection evidence"

        self._append_check(
            "android.logcat.analysis",
            status,
            message,
            details={
                "logcat_path": str(logcat_path),
                "crash_count": crash_count,
                "ble_mentions": ble_mentions,
                "device_seen": device_seen,
                "websocket_seen": websocket_seen,
            },
            artifacts=[logcat_path],
        )

    def _build_recommendations(self) -> List[str]:
        recommendations: List[str] = []
        failed_checks = [check for check in self.checks if check.status == "fail"]
        warning_checks = [check for check in self.checks if check.status == "warning"]

        if any(check.name == "pi.sudo.noninteractive" for check in failed_checks):
            recommendations.append("Enable passwordless sudo for the Pi deploy user before rerunning the harness.")
        if any(check.name.startswith("pi.service.") for check in failed_checks):
            recommendations.append("Inspect the collected Pi journal logs and fix inactive systemd services before trusting Android results.")
        if any(check.name == "pi.api.status" for check in failed_checks):
            recommendations.append("Confirm the Pi API listens on port 8000 and that the phone-facing host resolves to the same 192.168.200.x address.")
        if any(check.name == "android.logcat.analysis" for check in failed_checks):
            recommendations.append("Triage Android crashes first; a failing app run invalidates BLE and backend findings.")
        if any(check.name == "android.logcat.analysis" for check in warning_checks):
            recommendations.append("Refine the Android scenario so BLE discovery and WebSocket evidence are visible in logcat for automated verification.")
        if any(check.name == "android.device.network" for check in warning_checks):
            recommendations.append("Keep the phone on the 192.168.200.0/24 Wi-Fi network during the run so app traffic uses the Pi directly.")
        if any(check.name == "pi.os.release" for check in warning_checks):
            recommendations.append("If the Pi is not on Kali, label the run clearly so environment-specific findings do not pollute the Kali prototype baseline.")

        if not recommendations:
            recommendations.append("Promote this configuration to the next prototype test stage and add richer BLE/OBD assertions to the harness.")
        return recommendations

    def _metrics_from_checks(self) -> CycleMetrics:
        relevant = [check for check in self.checks if check.status in {"pass", "fail", "warning"}]
        total = len(relevant) or 1
        passed = sum(1 for check in relevant if check.status == "pass")
        warnings = sum(1 for check in relevant if check.status == "warning")
        failed = sum(1 for check in relevant if check.status == "fail")

        success_rate = passed / total
        coverage = min(1.0, (passed + (warnings * 0.5)) / total)
        quality_score = max(0.0, min(100.0, 55.0 + (success_rate * 35.0) - (failed * 4.0) - (warnings * 1.5)))
        efficiency = max(0.0, min(1.0, 1.0 - ((failed * 0.08) + (warnings * 0.03))))
        error_rate = failed / total
        return CycleMetrics(
            success_rate=success_rate,
            coverage=coverage,
            quality_score=quality_score,
            efficiency=efficiency,
            error_rate=error_rate,
        ).clamp()

    def _select_improvement_target(self, metrics: CycleMetrics) -> str:
        target_map = {
            "success_rate": metrics.success_rate,
            "generation_quality": metrics.quality_score / 100.0,
            "coverage_increase": metrics.coverage,
            "execution_efficiency": metrics.efficiency,
            "error_reduction": 1.0 - metrics.error_rate,
        }
        thresholds = {
            "success_rate": 0.90,
            "generation_quality": 0.85,
            "coverage_increase": 0.95,
            "execution_efficiency": 0.90,
            "error_reduction": 0.95,
        }
        gaps = {
            target: thresholds[target] - value
            for target, value in target_map.items()
        }
        return max(gaps, key=gaps.get)

    def _record_learning(self, recommendations: List[str]) -> Dict[str, Any]:
        kb = KnowledgeBase(self.config.kb_path)
        current_metrics = kb.get_current_metrics() or INITIAL_METRICS
        metrics_before = CycleMetrics(
            success_rate=current_metrics.get("success_rate", INITIAL_METRICS["success_rate"]),
            coverage=current_metrics.get("coverage", INITIAL_METRICS["coverage"]),
            quality_score=current_metrics.get("quality_score", INITIAL_METRICS["quality_score"]),
            efficiency=current_metrics.get("efficiency", INITIAL_METRICS["efficiency"]),
            error_rate=current_metrics.get("error_rate", INITIAL_METRICS["error_rate"]),
        )
        metrics_after = self._metrics_from_checks()
        improvement_target = self._select_improvement_target(metrics_after)
        cycle_number = kb.get_total_cycles() + 1

        phase_results = []
        for prefix, phase_name in [
            ("local.", "local_preflight"),
            ("pi.", "pi_validation"),
            ("android.", "android_validation"),
        ]:
            phase_checks = [check for check in self.checks if check.name.startswith(prefix)]
            if not phase_checks:
                continue
            phase_results.append(
                {
                    "phase_name": phase_name,
                    "success": all(check.status != "fail" for check in phase_checks),
                    "duration_ms": round(sum(check.duration_s for check in phase_checks) * 1000.0, 2),
                    "patterns_learned": [],
                    "metrics_delta": {},
                    "insights": [check.message for check in phase_checks if check.status != "pass"],
                    "details": {
                        "checks": [asdict(check) for check in phase_checks],
                    },
                }
            )

        kb.record_cycle(
            {
                "cycle_number": cycle_number,
                "improvement_target": improvement_target,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed": True,
                "metrics_before": metrics_before.to_dict(),
                "metrics_after": metrics_after.to_dict(),
                "phase_results": phase_results,
                "improvement_actions_applied": [],
                "next_cycle_recommendation": improvement_target,
                "knowledge_boost_used": kb.get_knowledge_boost(improvement_target),
                "improvement_rate": metrics_after.overall_health() - metrics_before.overall_health(),
            }
        )

        recorded_patterns: List[str] = []
        for check in self.checks:
            if check.status not in {"fail", "warning"}:
                continue
            environment_specific = check.name.startswith("pi.os.") or check.name.startswith("pi.bluetooth")
            target = "error_reduction" if check.status == "fail" else "execution_efficiency"
            pattern = Pattern(
                pattern_id=f"integration:{check.name}:{check.status}",
                pattern_type="error" if check.status == "fail" else "meta",
                improvement_target=target,
                description=(
                    f"{check.name}: {check.message}"
                    + (" [environment]" if environment_specific else "")
                ),
            )
            kb.add_pattern(pattern)
            recorded_patterns.append(pattern.pattern_id)

        if not recorded_patterns:
            success_pattern = Pattern(
                pattern_id="integration:successful_full_flow",
                pattern_type="optimization",
                improvement_target="success_rate",
                description="Prototype integration harness completed without warnings or failures.",
            )
            kb.add_pattern(success_pattern)
            recorded_patterns.append(success_pattern.pattern_id)

        for recommendation in recommendations:
            kb.add_insight(recommendation, cycle_number)

        state_payload = {
            "cycle_number": cycle_number,
            "target_index": IMPROVEMENT_TARGETS.index(improvement_target),
            "current_metrics": metrics_after.to_dict(),
            "completed_cycles": [
                {
                    "cycle_number": cycle_number,
                    "summary_path": str(self.summary_path),
                    "overall_status": self._overall_status(),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.state_path.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")

        return {
            "kb_path": str(self.config.kb_path),
            "state_path": str(self.config.state_path),
            "cycle_number": cycle_number,
            "improvement_target": improvement_target,
            "metrics_before": metrics_before.to_dict(),
            "metrics_after": metrics_after.to_dict(),
            "patterns_recorded": recorded_patterns,
        }

    def _overall_status(self) -> str:
        statuses = {check.status for check in self.checks}
        if "fail" in statuses:
            return "fail"
        if "warning" in statuses:
            return "warning"
        return "pass"

    def _status_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"pass": 0, "warning": 0, "fail": 0, "skip": 0}
        for check in self.checks:
            counts[check.status] = counts.get(check.status, 0) + 1
        return counts

    def _run_agent_analysis(self) -> Dict[str, Any]:
        if not self.config.run_agent_analysis:
            return {"status": "skipped", "reason": "agent analysis disabled"}
        if execute_command(["bash", "-lc", "command -v sessions_spawn"]).returncode != 0:
            return {"status": "skipped", "reason": "sessions_spawn not available"}

        prompt = textwrap.dedent(
            f"""
            Analyze the latest MIA prototype integration harness result.

            Summary file: {self.summary_path}
            Focus areas:
            1. Android over USB ADB behavior
            2. Raspberry Pi Kali deployment and systemd health
            3. BLE advertiser and BLE OBD service evidence
            4. Ranked code-change proposals, not code edits
            5. Environment-specific blockers vs product regressions

            Return JSON with: status, top_findings, ranked_recommendations, environment_blockers.
            """
        ).strip()
        result = execute_command(
            ["sessions_spawn", "--label", "prototype-integration-review", "--task", prompt],
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        artifacts = self._write_command_logs("agent_analysis", result, self.meta_dir)
        self._append_check(
            "meta.agent_analysis",
            "pass" if result.succeeded else "warning",
            "Queued agent analysis" if result.succeeded else "Agent analysis could not be queued",
            duration_s=result.duration_s,
            artifacts=artifacts,
        )
        return {
            "status": "queued" if result.succeeded else "warning",
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    def _summary_dict(self, recommendations: List[str], meta: Dict[str, Any], agent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "metadata": {
                "timestamp": self.timestamp,
                "scenario": self.config.scenario,
                "device_serial": self.config.device_serial,
                "rpi_host": self.config.rpi_host,
                "resolved_rpi_host": self.resolved_rpi_host,
                "rpi_user": self.config.rpi_user,
                "package_name": self.package_name,
                "launcher_activity": self.main_activity,
                "api_base_url": self.api_base_url,
                "ws_base_url": self.ws_base_url,
                "output_dir": str(self.output_dir),
            },
            "checks": [asdict(check) for check in self.checks],
            "status_counts": self._status_counts(),
            "overall_status": self._overall_status(),
            "artifacts": {
                "android_source": str(self.android_artifact_source) if self.android_artifact_source else None,
                "android_copy": str(self.android_artifact_copy) if self.android_artifact_copy else None,
                "pi_dir": str(self.pi_dir),
                "report_path": str(self.report_path),
            },
            "recommendations": recommendations,
            "meta_harness": meta,
            "agent_analysis": agent_analysis,
        }

    def _write_summary(self, summary: Dict[str, Any]) -> None:
        self.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def _write_report(self, summary: Dict[str, Any]) -> None:
        lines = [
            "# MIA Prototype Integration Harness",
            "",
            f"- Overall status: **{summary['overall_status']}**",
            f"- Scenario: `{self.config.scenario}`",
            f"- Android device: `{self.config.device_serial}`",
            f"- Raspberry Pi host: `{self.config.rpi_host}` ({self.resolved_rpi_host})",
            f"- Android package: `{self.package_name}`",
            "",
            "## Checks",
            "",
            "| Check | Status | Message |",
            "| --- | --- | --- |",
        ]
        for check in self.checks:
            lines.append(f"| {check.name} | {check.status} | {check.message} |")
        lines.extend(["", "## Recommendations", ""])
        for recommendation in summary["recommendations"]:
            lines.append(f"- {recommendation}")
        self.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run(self) -> int:
        self._record_static_context()
        local_ok = self.run_local_preflight()
        pi_ok = self.run_pi_preflight()

        if self.config.deploy_pi and pi_ok:
            pi_ok = self.deploy_pi() and pi_ok
        elif not self.config.deploy_pi:
            self._append_check("pi.deploy", "skip", "Pi deploy skipped by configuration")

        if pi_ok:
            self.collect_pi_health()
        else:
            self._append_check("pi.health", "skip", "Pi health checks skipped because preflight or deploy failed")

        if self.config.run_android and local_ok:
            self.run_android_orchestrator()
        elif not self.config.run_android:
            self._append_check("android.orchestrator", "skip", "Android run skipped by configuration")
        else:
            self._append_check(
                "android.orchestrator",
                "skip",
                "Android run skipped because local preflight failed",
            )

        recommendations = self._build_recommendations()
        meta = self._record_learning(recommendations)
        summary = self._summary_dict(recommendations, meta, {"status": "pending"})
        self._write_summary(summary)
        agent_analysis = self._run_agent_analysis()
        summary = self._summary_dict(recommendations, meta, agent_analysis)
        self._write_summary(summary)
        self._write_report(summary)
        print(json.dumps(summary["status_counts"], indent=2))
        print(f"Summary written to {self.summary_path}")
        print(f"Report written to {self.report_path}")
        return 1 if summary["overall_status"] == "fail" else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prototype integration harness for USB Android + Raspberry Pi MIA bring-up",
    )
    parser.add_argument("--rpi-host", default="mia.local", help="Raspberry Pi host or IP")
    parser.add_argument("--rpi-user", default="sparrow", help="Raspberry Pi SSH user")
    parser.add_argument("--device", dest="device_serial", default=None, help="ADB device serial")
    parser.add_argument("--scenario", default="full-flow", help="Android scenario to run")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory for integration artifacts",
    )
    parser.add_argument("--skip-pi-deploy", action="store_true", help="Skip Pi deploy")
    parser.add_argument("--skip-android", action="store_true", help="Skip Android orchestration")
    parser.add_argument(
        "--skip-agent-analysis",
        action="store_true",
        help="Skip optional OpenClaw sessions_spawn analysis",
    )
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port for Raspberry Pi")
    parser.add_argument("--ssh-key", type=Path, default=None, help="Optional SSH private key path")
    parser.add_argument("--subnet", default="192.168.200.0/24", help="Expected LAN subnet")
    parser.add_argument("--deploy-timeout", type=int, default=1800, help="Timeout for Pi deploy in seconds")
    parser.add_argument("--android-timeout", type=int, default=3600, help="Timeout for Android orchestration in seconds")
    parser.add_argument("--kb-path", type=Path, default=DEFAULT_KB_PATH, help="Path to dedicated integration KB JSON")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH, help="Path to dedicated integration state JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = HarnessConfig(
        rpi_host=args.rpi_host,
        rpi_user=args.rpi_user,
        device_serial=args.device_serial,
        scenario=args.scenario,
        output_root=args.output_root,
        deploy_pi=not args.skip_pi_deploy,
        run_android=not args.skip_android,
        run_agent_analysis=not args.skip_agent_analysis,
        ssh_port=args.ssh_port,
        ssh_key=args.ssh_key,
        subnet=args.subnet,
        deploy_timeout=args.deploy_timeout,
        android_timeout=args.android_timeout,
        kb_path=args.kb_path,
        state_path=args.state_path,
    )
    harness = PrototypeIntegrationHarness(config)
    return harness.run()


if __name__ == "__main__":
    raise SystemExit(main())