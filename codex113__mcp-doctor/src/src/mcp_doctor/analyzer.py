from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .jsonc import parse_jsonc
from .models import ConfigReport, Finding, ServerReport, WorkspaceReport


ROOT_KEYS = ("mcpServers", "mcp_servers", "servers")
PLACEHOLDER_RE = re.compile(
    r"(?i)^(your[_-]?|replace[_-]?me|changeme|todo|example|sample|placeholder|xxx|<.+>|put[_-]?token|set[_-]?me)"
)
ENV_REFERENCE_RE = re.compile(r"^\$(\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_][A-Za-z0-9_]*%)$")
SECRET_KEY_RE = re.compile(r"(?i)(api|auth|token|secret|password|key)")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def analyze_paths(paths: list[tuple[Path, str]], workspace: Path) -> WorkspaceReport:
    configs = [analyze_config(path, source, workspace) for path, source in paths]
    report = WorkspaceReport(
        workspace=workspace,
        scanned_paths=[path for path, _ in paths],
        configs=configs,
    )
    if not paths:
        report.findings.append(
            Finding(
                severity="warning",
                code="no_configs_found",
                message="No MCP config files were found in the workspace or known home locations",
                hint="Try passing an explicit path or create .cursor/mcp.json, mcp.json, or a Claude Desktop config file",
            )
        )
        return report
    _attach_duplicate_findings(report)
    return report


def analyze_config(path: Path, source: str, workspace: Path) -> ConfigReport:
    report = ConfigReport(path=path, source=source)
    if not path.exists():
        report.findings.append(
            Finding(
                severity="error",
                code="missing_file",
                message=f"Config file does not exist: {path}",
                hint="Check the path or generate the config before scanning",
            )
        )
        return report

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.findings.append(
            Finding(
                severity="error",
                code="read_failed",
                message=f"Could not read config file: {exc}",
                hint="Fix file permissions or pass a different path",
            )
        )
        return report

    try:
        data, notes = parse_jsonc(raw_text)
        report.parse_notes.extend(notes)
    except Exception as exc:
        report.findings.append(
            Finding(
                severity="error",
                code="json_parse_failed",
                message=f"JSON parsing failed: {exc}",
                hint="Fix broken JSON or remove unsupported syntax before retrying",
            )
        )
        return report

    if not isinstance(data, dict):
        report.findings.append(
            Finding(
                severity="error",
                code="root_not_object",
                message="Config root must be a JSON object",
                hint="Wrap servers inside an object with mcpServers as the top-level key",
            )
        )
        return report

    root_key = next((key for key in ROOT_KEYS if key in data), None)
    if root_key is None:
        report.findings.append(
            Finding(
                severity="error",
                code="missing_mcp_servers",
                message="Config does not expose mcpServers, mcp_servers, or servers",
                hint="Use the standard {\"mcpServers\": { ... }} shape",
            )
        )
        return report

    report.root_key = root_key
    servers = data.get(root_key)
    if not isinstance(servers, dict):
        report.findings.append(
            Finding(
                severity="error",
                code="servers_not_object",
                message=f"The {root_key} field must be an object keyed by server name",
                hint="Convert array-based server definitions into a name => config object map",
            )
        )
        return report

    if not servers:
        report.findings.append(
            Finding(
                severity="warning",
                code="no_servers_defined",
                message=f"The {root_key} object is empty",
                hint="Add at least one MCP server or remove the file",
            )
        )
        return report

    for name, payload in servers.items():
        report.servers.append(analyze_server(name, payload, path, workspace))

    return report


def analyze_server(name: str, payload: Any, config_path: Path, workspace: Path) -> ServerReport:
    if not isinstance(payload, dict):
        server = ServerReport(name=name, transport="unknown")
        server.findings.append(
            Finding(
                severity="error",
                code="server_not_object",
                message=f"Server {name} must be an object",
                hint="Use a JSON object with command/url/env fields",
                scope=name,
            )
        )
        return server

    command = payload.get("command")
    args = payload.get("args", [])
    url = payload.get("url")
    env = payload.get("env", {})
    disabled = bool(payload.get("disabled", False))

    transport = "unknown"
    if command and url:
        transport = "mixed"
    elif command:
        transport = "stdio"
    elif url:
        transport = "remote"

    server = ServerReport(
        name=name,
        transport=transport,
        command=command if isinstance(command, str) else None,
        args=args if isinstance(args, list) else [],
        url=url if isinstance(url, str) else None,
        env_keys=sorted(env.keys()) if isinstance(env, dict) else [],
        disabled=disabled,
    )

    if disabled:
        server.findings.append(
            Finding(
                severity="info",
                code="server_disabled",
                message=f"Server {name} is marked disabled",
                hint="Ignore this if the server is intentionally staged for later",
                scope=name,
            )
        )

    if command is not None and not isinstance(command, str):
        server.findings.append(
            Finding(
                severity="error",
                code="command_not_string",
                message=f"Server {name} has a non-string command field",
                hint="Use a string executable name or absolute path",
                scope=name,
            )
        )
    if url is not None and not isinstance(url, str):
        server.findings.append(
            Finding(
                severity="error",
                code="url_not_string",
                message=f"Server {name} has a non-string url field",
                hint="Use a full http, https, ws, or wss URL",
                scope=name,
            )
        )
    if args is not None and not isinstance(args, list):
        server.findings.append(
            Finding(
                severity="error",
                code="args_not_list",
                message=f"Server {name} has a non-list args field",
                hint="Represent each CLI argument as a separate array item",
                scope=name,
            )
        )
    if env is not None and not isinstance(env, dict):
        server.findings.append(
            Finding(
                severity="error",
                code="env_not_object",
                message=f"Server {name} has a non-object env field",
                hint="Use a JSON object of key/value pairs",
                scope=name,
            )
        )

    if command and url:
        server.findings.append(
            Finding(
                severity="warning",
                code="mixed_transport",
                message=f"Server {server.name} defines both command and url",
                hint="Pick one transport per server to avoid ambiguous client behavior",
                scope=server.name,
            )
        )
    elif not command and not url:
        server.findings.append(
            Finding(
                severity="error",
                code="missing_transport",
                message=f"Server {server.name} defines neither command nor url",
                hint="Add a local command for stdio or a remote URL for HTTP/SSE transport",
                scope=server.name,
            )
        )

    if command:
        _analyze_command(server, command, args if isinstance(args, list) else [], config_path, workspace)
    if url:
        _analyze_url(server, url)
    if isinstance(env, dict):
        _analyze_env(server, env)

    return server


def _attach_duplicate_findings(report: WorkspaceReport) -> None:
    by_name: dict[str, list[tuple[ConfigReport, ServerReport]]] = {}
    for config in report.configs:
        for server in config.servers:
            by_name.setdefault(server.name, []).append((config, server))

    for name, entries in by_name.items():
        if len(entries) < 2:
            continue
        fingerprints = {_server_fingerprint(server) for _, server in entries}
        if len(fingerprints) == 1:
            severity = "warning"
            code = "duplicate_server_name"
            message = f"Server name {name} appears in multiple config files"
            hint = "Keep only one canonical definition to avoid duplicated loading or unclear precedence"
        else:
            severity = "warning"
            code = "conflicting_server_name"
            message = f"Server name {name} is reused with different definitions across config files"
            hint = "Rename one definition or consolidate them into a single source of truth"
        report.findings.append(Finding(severity=severity, code=code, message=message, hint=hint, scope=name))


def _server_fingerprint(server: ServerReport) -> str:
    digest = hashlib.sha256()
    digest.update((server.command or "").encode("utf-8"))
    digest.update("\n".join(server.args).encode("utf-8"))
    digest.update((server.url or "").encode("utf-8"))
    digest.update("\n".join(server.env_keys).encode("utf-8"))
    digest.update(server.transport.encode("utf-8"))
    return digest.hexdigest()


def _resolve_command(command: str, config_path: Path, workspace: Path) -> Path | None:
    expanded = Path(command).expanduser()
    command_has_separator = any(separator in command for separator in ("/", "\\"))
    if command_has_separator:
        if not expanded.is_absolute():
            config_relative = (config_path.parent / expanded).resolve()
            if config_relative.exists():
                return config_relative
            workspace_relative = (workspace / expanded).resolve()
            return workspace_relative
        return expanded
    resolved = shutil.which(command)
    return Path(resolved) if resolved else None


def _analyze_command(server: ServerReport, command: str, args: list[Any], config_path: Path, workspace: Path) -> None:
    resolved = _resolve_command(command, config_path, workspace)
    if resolved is None or not resolved.exists():
        server.findings.append(
            Finding(
                severity="error",
                code="command_not_found",
                message=f"Server {server.name} points to a command that is not available: {command}",
                hint="Install the binary, fix the path, or switch to a command that exists on PATH",
                scope=server.name,
            )
        )
        return

    if resolved.is_file() and "/" in command and not resolved.exists():
        server.findings.append(
            Finding(
                severity="error",
                code="command_path_missing",
                message=f"Server {server.name} references a missing command path: {resolved}",
                hint="Check whether the script or executable was moved",
                scope=server.name,
            )
        )

    string_args = [str(arg) for arg in args]
    if not string_args:
        if Path(command).name in {"npx", "pnpm", "pnpx", "bunx", "uvx"}:
            server.findings.append(
                Finding(
                    severity="error",
                    code="package_runner_missing_target",
                    message=f"Server {server.name} uses {command} without a package name or script",
                    hint="Add the package or executable as the first arg",
                    scope=server.name,
                )
            )
        return

    file_checked = False
    first_arg = string_args[0]
    command_name = Path(command).name
    if command_name in {"python", "python3", "node", "bun", "deno"}:
        if first_arg.startswith("-"):
            return
        if any(separator in first_arg for separator in ("/", "\\")) or first_arg.endswith((".py", ".js", ".mjs", ".cjs", ".ts")):
            candidate = Path(first_arg).expanduser()
            if not candidate.is_absolute():
                config_relative = (config_path.parent / candidate).resolve()
                workspace_relative = (workspace / candidate).resolve()
                candidate = config_relative if config_relative.exists() else workspace_relative
            file_checked = True
            if not candidate.exists():
                server.findings.append(
                    Finding(
                        severity="error",
                        code="script_missing",
                        message=f"Server {server.name} references a missing script: {candidate}",
                        hint="Fix the relative path or ship the script next to the config",
                        scope=server.name,
                    )
                )
    if not file_checked and isinstance(resolved, Path) and resolved.is_file() and not resolved.exists():
        server.findings.append(
            Finding(
                severity="error",
                code="resolved_command_missing",
                message=f"Server {server.name} resolves to a command path that no longer exists: {resolved}",
                hint="Reinstall the command or update the config",
                scope=server.name,
            )
        )


def _analyze_url(server: ServerReport, raw_url: str) -> None:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https", "ws", "wss"}:
        server.findings.append(
            Finding(
                severity="error",
                code="unsupported_url_scheme",
                message=f"Server {server.name} uses an unsupported URL scheme: {raw_url}",
                hint="Use http, https, ws, or wss",
                scope=server.name,
            )
        )
        return
    if not parsed.netloc:
        server.findings.append(
            Finding(
                severity="error",
                code="url_missing_host",
                message=f"Server {server.name} has a URL with no host: {raw_url}",
                hint="Include a hostname such as localhost or an HTTPS domain",
                scope=server.name,
            )
        )
        return
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        server.findings.append(
            Finding(
                severity="warning",
                code="remote_http_url",
                message=f"Server {server.name} uses plain HTTP for a non-local endpoint",
                hint="Switch to HTTPS unless the server is intentionally private and local to your network",
                scope=server.name,
            )
        )


def _analyze_env(server: ServerReport, env: dict[str, Any]) -> None:
    for key, value in env.items():
        if not isinstance(key, str):
            server.findings.append(
                Finding(
                    severity="error",
                    code="env_key_not_string",
                    message=f"Server {server.name} has a non-string env key",
                    hint="Use plain string keys such as API_KEY",
                    scope=server.name,
                )
            )
            continue
        if not isinstance(value, str):
            server.findings.append(
                Finding(
                    severity="error",
                    code="env_value_not_string",
                    message=f"Server {server.name} uses a non-string env value for {key}",
                    hint="Most MCP clients expect env values to be strings",
                    scope=server.name,
                )
            )
            continue
        cleaned = value.strip()
        if not cleaned:
            server.findings.append(
                Finding(
                    severity="error",
                    code="empty_env_value",
                    message=f"Server {server.name} leaves {key} empty",
                    hint="Populate the value or remove the env entry until the secret exists",
                    scope=server.name,
                )
            )
            continue
        if PLACEHOLDER_RE.match(cleaned):
            server.findings.append(
                Finding(
                    severity="warning",
                    code="placeholder_env_value",
                    message=f"Server {server.name} still uses a placeholder value for {key}",
                    hint="Replace the placeholder with a real secret or an environment reference",
                    scope=server.name,
                )
            )
            continue
        if SECRET_KEY_RE.search(key) and not ENV_REFERENCE_RE.match(cleaned):
            server.findings.append(
                Finding(
                    severity="warning",
                    code="literal_secret_in_config",
                    message=f"Server {server.name} appears to store a literal secret in config key {key}",
                    hint="Prefer injecting secrets from the environment instead of committing them to JSON",
                    scope=server.name,
                )
            )
