from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

# The real pyzmq modules, captured before any test module can replace ``sys.modules["zmq"]`` with a mock
# (``tests/unit/orchestration`` does, at import time). A second import of pyzmq makes a second copy of
# ``zmq.error``, and sockets keep raising the first copy's exceptions, so tests that need real sockets
# must put these very modules back (see the ``real_zmq`` fixture in tests/unit/rpi_backend/conftest.py).
try:
    import zmq  # noqa: F401
    import zmq.asyncio  # noqa: F401
except ImportError:  # pragma: no cover - pyzmq is a test requirement
    pass
_REAL_ZMQ_MODULES = {n: m for n, m in sys.modules.items() if n == "zmq" or n.startswith("zmq.")}


@pytest.fixture(scope="session")
def real_zmq_modules():
    return dict(_REAL_ZMQ_MODULES)


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
    REPO_ROOT / "schemas" / "generated" / "python",
]

for source_path in reversed(SOURCE_PATHS):
    source_path_str = str(source_path)
    if source_path_str not in sys.path:
        sys.path.insert(0, source_path_str)

# Requirement traceability: the req marker and --req-report (tests/plugins/req_traceability.py).
sys.path.insert(0, str(REPO_ROOT / "tests" / "plugins"))
pytest_plugins = ["req_traceability"]
