from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCE_PATHS = [
    REPO_ROOT / "apps" / "rpi-backend" / "py-api",
    REPO_ROOT / "apps" / "rpi-backend" / "py-api" / "hardware",
    REPO_ROOT / "orchestration" / "mia-agents",
    REPO_ROOT / "orchestration" / "mcp" / "modules",
    REPO_ROOT / "orchestration" / "mcp" / "modules" / "core-orchestrator",
]

for source_path in reversed(SOURCE_PATHS):
    source_path_str = str(source_path)
    if source_path_str not in sys.path:
        sys.path.insert(0, source_path_str)


# These tests are legacy snapshots that depend on relative imports from
# a hyphenated directory name (tests/unit/rpi-backend), which pytest cannot
# import as a normal Python package.
collect_ignore_glob = ["unit/rpi-backend/test_*.py"]