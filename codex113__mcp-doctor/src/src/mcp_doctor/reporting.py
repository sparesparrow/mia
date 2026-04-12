from __future__ import annotations

import json
from pathlib import Path

from .models import ConfigReport, Finding, ServerReport, WorkspaceReport


def render_report(report: WorkspaceReport, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    if output_format == "markdown":
        return _render_markdown(report)
    return _render_text(report)


def _render_text(report: WorkspaceReport) -> str:
    counts = report.counts()
    lines = [
        "MCP Doctor",
        f"Workspace: {report.workspace}",
        f"Status: {report.status}",
        f"Configs: {counts['configs']}  Servers: {counts['servers']}  Errors: {counts['errors']}  Warnings: {counts['warnings']}  Info: {counts['info']}",
    ]
    if report.findings:
        lines.append("")
        lines.append("Global findings")
        lines.extend(_render_findings(report.findings, indent="  - "))
    for config in report.configs:
        lines.append("")
        lines.append(f"[{config.status.upper()}] {config.path} ({config.source})")
        if config.root_key:
            lines.append(f"  root key: {config.root_key}")
        for note in config.parse_notes:
            lines.append(f"  note: {note}")
        if config.findings:
            lines.extend(_render_findings(config.findings, indent="  - "))
        for server in config.servers:
            lines.extend(_render_server_text(server))
    return "\n".join(lines)


def _render_server_text(server: ServerReport) -> list[str]:
    lines = [
        f"  server {server.name} [{server.status}]",
        f"    transport: {server.transport}",
    ]
    if server.command:
        args = " ".join(server.args)
        lines.append(f"    command: {server.command}{(' ' + args) if args else ''}")
    if server.url:
        lines.append(f"    url: {server.url}")
    if server.env_keys:
        lines.append(f"    env keys: {', '.join(server.env_keys)}")
    if server.findings:
        lines.extend(_render_findings(server.findings, indent="    - "))
    return lines


def _render_markdown(report: WorkspaceReport) -> str:
    counts = report.counts()
    lines = [
        "# MCP Doctor Report",
        "",
        f"- Workspace: `{report.workspace}`",
        f"- Status: `{report.status}`",
        f"- Configs: `{counts['configs']}`",
        f"- Servers: `{counts['servers']}`",
        f"- Errors: `{counts['errors']}`",
        f"- Warnings: `{counts['warnings']}`",
        f"- Info: `{counts['info']}`",
    ]
    if report.findings:
        lines.extend(["", "## Global Findings", ""])
        lines.extend(_render_findings(report.findings, indent="- "))
    for config in report.configs:
        lines.extend(["", f"## {config.path}", ""])
        lines.append(f"- Source: `{config.source}`")
        lines.append(f"- Status: `{config.status}`")
        if config.root_key:
            lines.append(f"- Root key: `{config.root_key}`")
        for note in config.parse_notes:
            lines.append(f"- Parse note: {note}")
        if config.findings:
            lines.append("")
            lines.append("### Config Findings")
            lines.append("")
            lines.extend(_render_findings(config.findings, indent="- "))
        if config.servers:
            lines.append("")
            lines.append("### Servers")
            for server in config.servers:
                lines.extend(["", f"#### {server.name}", ""])
                lines.append(f"- Status: `{server.status}`")
                lines.append(f"- Transport: `{server.transport}`")
                if server.command:
                    args = " ".join(server.args)
                    lines.append(f"- Command: `{server.command}{(' ' + args) if args else ''}`")
                if server.url:
                    lines.append(f"- URL: `{server.url}`")
                if server.env_keys:
                    lines.append(f"- Env keys: `{', '.join(server.env_keys)}`")
                if server.findings:
                    lines.append("")
                    lines.extend(_render_findings(server.findings, indent="- "))
    return "\n".join(lines)


def _render_findings(findings: list[Finding], indent: str) -> list[str]:
    lines: list[str] = []
    for finding in findings:
        scope = f" ({finding.scope})" if finding.scope else ""
        line = f"{indent}`{finding.severity}` `{finding.code}`{scope}: {finding.message}"
        lines.append(line)
        if finding.hint:
            child_indent = " " * len(indent)
            lines.append(f"{child_indent}Hint: {finding.hint}")
    return lines
