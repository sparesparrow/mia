from __future__ import annotations

from pathlib import Path


EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
}

KNOWN_WORKSPACE_RELATIVE = (
    ".cursor/mcp.json",
    ".cursor/mcp.jsonc",
    ".vscode/mcp.json",
    ".vscode/mcp.jsonc",
    "mcp.json",
    "mcp.jsonc",
    ".mcp.json",
    ".mcp.jsonc",
    "claude_desktop_config.json",
)

KNOWN_HOME_FILES = (
    "~/.cursor/mcp.json",
    "~/.cursor/mcp.jsonc",
    "~/Library/Application Support/Claude/claude_desktop_config.json",
    "~/.config/Claude/claude_desktop_config.json",
    "~/AppData/Roaming/Claude/claude_desktop_config.json",
)


def _is_candidate_file(path: Path) -> bool:
    suffixes = {suffix.lower() for suffix in path.suffixes}
    if not {".json", ".jsonc"} & suffixes:
        return False
    return "mcp" in path.name.lower() or path.name == "claude_desktop_config.json"


def _walk_directory(directory: Path) -> list[Path]:
    matches: list[Path] = []
    for path in directory.rglob("*"):
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.is_file() and _is_candidate_file(path):
            matches.append(path)
    return matches


def _dedupe(paths: list[tuple[Path, str]]) -> list[tuple[Path, str]]:
    seen: set[Path] = set()
    deduped: list[tuple[Path, str]] = []
    for path, source in paths:
        if path in seen:
            continue
        seen.add(path)
        deduped.append((path, source))
    return deduped


def collect_scan_targets(
    workspace: Path,
    provided_paths: list[str] | None = None,
    include_home: bool = True,
) -> list[tuple[Path, str]]:
    if provided_paths:
        targets: list[tuple[Path, str]] = []
        for raw_path in provided_paths:
            path = Path(raw_path).expanduser()
            if not path.is_absolute():
                path = (workspace / path).resolve()
            if path.is_dir():
                targets.extend((candidate.resolve(), "explicit-directory") for candidate in _walk_directory(path))
            else:
                targets.append((path.resolve(), "explicit-file"))
        return _dedupe(targets)

    discovered: list[tuple[Path, str]] = []
    for relative in KNOWN_WORKSPACE_RELATIVE:
        candidate = (workspace / relative).resolve()
        if candidate.exists():
            discovered.append((candidate, "workspace-known"))

    discovered.extend((path.resolve(), "workspace-discovered") for path in _walk_directory(workspace))

    if include_home:
        for raw_home_path in KNOWN_HOME_FILES:
            candidate = Path(raw_home_path).expanduser().resolve()
            if candidate.exists():
                discovered.append((candidate, "home-known"))

    return _dedupe(discovered)
