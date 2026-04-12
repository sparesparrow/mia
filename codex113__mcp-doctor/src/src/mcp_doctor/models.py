from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def status_from_findings(findings: list["Finding"]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "error"
    if any(finding.severity == "warning" for finding in findings):
        return "warning"
    return "healthy"


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    hint: str | None = None
    scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.hint:
            payload["hint"] = self.hint
        if self.scope:
            payload["scope"] = self.scope
        return payload


@dataclass
class ServerReport:
    name: str
    transport: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    env_keys: list[str] = field(default_factory=list)
    disabled: bool = False
    findings: list[Finding] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_findings(self.findings)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "transport": self.transport,
            "disabled": self.disabled,
            "envKeys": self.env_keys,
            "findings": [finding.to_dict() for finding in self.findings],
        }
        if self.command is not None:
            payload["command"] = self.command
        if self.args:
            payload["args"] = self.args
        if self.url is not None:
            payload["url"] = self.url
        return payload


@dataclass
class ConfigReport:
    path: Path
    source: str
    root_key: str | None = None
    parse_notes: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    servers: list[ServerReport] = field(default_factory=list)

    @property
    def status(self) -> str:
        return status_from_findings(self.findings + [finding for server in self.servers for finding in server.findings])

    def all_findings(self) -> list[Finding]:
        return self.findings + [finding for server in self.servers for finding in server.findings]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": str(self.path),
            "source": self.source,
            "status": self.status,
            "servers": [server.to_dict() for server in self.servers],
            "findings": [finding.to_dict() for finding in self.findings],
        }
        if self.root_key:
            payload["rootKey"] = self.root_key
        if self.parse_notes:
            payload["parseNotes"] = self.parse_notes
        return payload


@dataclass
class WorkspaceReport:
    workspace: Path
    scanned_paths: list[Path]
    configs: list[ConfigReport]
    findings: list[Finding] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def all_findings(self) -> list[Finding]:
        bundle = list(self.findings)
        for config in self.configs:
            bundle.extend(config.all_findings())
        return bundle

    def counts(self) -> dict[str, int]:
        all_findings = self.all_findings()
        return {
            "errors": sum(1 for finding in all_findings if finding.severity == "error"),
            "warnings": sum(1 for finding in all_findings if finding.severity == "warning"),
            "info": sum(1 for finding in all_findings if finding.severity == "info"),
            "configs": len(self.configs),
            "servers": sum(len(config.servers) for config in self.configs),
        }

    @property
    def status(self) -> str:
        return status_from_findings(self.all_findings())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": str(self.workspace),
            "generatedAt": self.generated_at,
            "status": self.status,
            "summary": self.counts(),
            "scannedPaths": [str(path) for path in self.scanned_paths],
            "findings": [finding.to_dict() for finding in self.findings],
            "configs": [config.to_dict() for config in self.configs],
        }
