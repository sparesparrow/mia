from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _register_namespace_package(name: str, path: Path) -> None:
    """Expose a directory as an importable package under an arbitrary name.

    ``apps/rpi-backend`` is not a valid Python identifier and the repository
    ships a ``apps/rpi_backend`` symlink for it. Symlinks are not materialised on
    checkouts without symlink support (notably Windows), so register the alias
    explicitly to keep imports working everywhere.
    """
    if name in sys.modules or not path.is_dir():
        return

    spec = importlib.machinery.ModuleSpec(name, None, is_package=True)
    spec.submodule_search_locations = [str(path)]
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    parent_name, _, child_name = name.rpartition(".")
    if parent_name and parent_name in sys.modules:
        setattr(sys.modules[parent_name], child_name, module)


_register_namespace_package("apps", REPO_ROOT / "apps")
_register_namespace_package("apps.rpi_backend", REPO_ROOT / "apps" / "rpi-backend")

SOURCE_PATHS = [
    REPO_ROOT / "apps" / "rpi-backend" / "py-api",
    REPO_ROOT / "apps" / "rpi-backend" / "py-api" / "hardware",
    REPO_ROOT / "orchestration" / "mia-agents",
    REPO_ROOT / "orchestration" / "mcp" / "modules",
    REPO_ROOT / "orchestration" / "mcp" / "modules" / "core-orchestrator",
    REPO_ROOT / "orchestration" / "meta_harness",
    REPO_ROOT / "tools",
]

for source_path in reversed(SOURCE_PATHS):
    source_path_str = str(source_path)
    if source_path_str not in sys.path:
        sys.path.insert(0, source_path_str)


# These tests are legacy snapshots that depend on relative imports from
# a hyphenated directory name (tests/unit/rpi-backend), which pytest cannot
# import as a normal Python package.
collect_ignore_glob = ["unit/rpi-backend/test_*.py"]