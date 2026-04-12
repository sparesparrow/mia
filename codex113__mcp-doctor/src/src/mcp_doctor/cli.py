from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from . import __version__
from .analyzer import analyze_paths
from .discovery import collect_scan_targets
from .reporting import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-doctor",
        description="Diagnose broken MCP configs across agent workspaces",
    )
    parser.add_argument("paths", nargs="*", help="Explicit config files or directories to scan")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root used for discovery and relative path resolution",
    )
    parser.add_argument(
        "--skip-home",
        action="store_true",
        help="Do not scan known home-directory config locations",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown", "json"),
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--write",
        help="Optional output file path",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with code 2 when warnings are present",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run the built-in self-test instead of scanning real configs",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        return _run_self_test(output_format=args.format)

    workspace = Path(args.workspace).expanduser().resolve()
    targets = collect_scan_targets(
        workspace=workspace,
        provided_paths=args.paths,
        include_home=not args.skip_home,
    )
    report = analyze_paths(targets, workspace)
    output = render_report(report, args.format)
    if args.write:
        output_path = Path(args.write).expanduser()
        if not output_path.is_absolute():
            output_path = (workspace / output_path).resolve()
        output_path.write_text(output + "\n", encoding="utf-8")
    print(output)
    counts = report.counts()
    if counts["errors"]:
        return 1
    if args.fail_on_warnings and counts["warnings"]:
        return 2
    return 0


def _run_self_test(output_format: str = "text") -> int:
    with tempfile.TemporaryDirectory(prefix="mcp-doctor-") as tmp:
        root = Path(tmp)
        cursor_dir = root / ".cursor"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        helper = scripts_dir / "filesystem_server.py"
        helper.write_text("print('filesystem ok')\n", encoding="utf-8")

        healthy = cursor_dir / "mcp.json"
        healthy.write_text(
            """{
  \"mcpServers\": {
    \"filesystem\": {
      \"command\": \"python3\",
      \"args\": [\"scripts/filesystem_server.py\"],
      \"env\": {
        \"LOG_LEVEL\": \"debug\"
      }
    }
  }
}
""",
            encoding="utf-8",
        )

        broken = root / "broken.mcp.jsonc"
        broken.write_text(
            """{
  // this file intentionally mixes issues
  \"mcpServers\": {
    \"filesystem\": {
      \"command\": \"python3\",
      \"args\": [\"missing/server.py\"],
      \"env\": {
        \"API_KEY\": \"YOUR_API_KEY\"
      }
    },
    \"ghost\": {
      \"command\": \"definitely-not-a-real-binary\",
      \"args\": [],
    }
  },
}
""",
            encoding="utf-8",
        )

        targets = collect_scan_targets(root, [str(healthy), str(broken)], include_home=False)
        report = analyze_paths(targets, root)
        counts = report.counts()
        assert counts["errors"] >= 2, "Expected at least two errors in self-test"
        assert counts["warnings"] >= 2, "Expected at least two warnings in self-test"
        output = render_report(report, output_format)
        print(output)
    return 0
