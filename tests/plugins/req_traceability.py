"""pytest plugin linking tests to the requirements in spec/requirements (see spec/README.md).

- ``@pytest.mark.req("REQ-AUTO-010", ...)`` or a module-level ``pytestmark = pytest.mark.req(...)``
  names the requirements a test covers. An ID that is not in the registry stops the run.
- ``--req-report=PATH`` writes every test's requirements and outcome as JSON for
  ``tools/ci/traceability.py check --pytest-report PATH``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKER = "req(*ids): requirement IDs from spec/requirements that this test covers"

_reqs: dict[str, list[str]] = {}
_outcomes: dict[str, str] = {}


def _registry_ids() -> set[str]:
    spec = importlib.util.spec_from_file_location("mia_traceability", REPO_ROOT / "tools" / "ci" / "traceability.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.requirement_ids(REPO_ROOT)


def pytest_addoption(parser):
    parser.addoption(
        "--req-report",
        metavar="PATH",
        default=None,
        help="write each test's requirement IDs and outcome as JSON (for tools/ci/traceability.py)",
    )


def pytest_configure(config):
    if not any(line.startswith("req") for line in config.getini("markers")):
        config.addinivalue_line("markers", MARKER)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    # tryfirst: see every collected test, including those -m deselects afterwards.
    known = _registry_ids()
    unknown = []
    for item in items:
        ids = [rid for mark in item.iter_markers("req") for rid in mark.args]
        _reqs[item.nodeid] = sorted(set(ids))
        unknown += [f"{item.nodeid}: {rid!r}" for rid in ids if rid not in known]
    if unknown:
        raise pytest.UsageError("tests name requirements that are not in spec/requirements:\n  " + "\n  ".join(unknown))


def pytest_runtest_logreport(report):
    if report.failed:
        _outcomes[report.nodeid] = "failed"
    elif _outcomes.get(report.nodeid) == "failed":
        return
    elif report.skipped:
        _outcomes[report.nodeid] = "skipped"
    elif report.when == "call":
        _outcomes[report.nodeid] = "passed"


def pytest_sessionfinish(session, exitstatus):
    path = session.config.getoption("--req-report")
    if not path:
        return
    tests = [
        {"nodeid": nodeid, "file": nodeid.split("::", 1)[0], "reqs": _reqs.get(nodeid, []), "outcome": outcome}
        for nodeid, outcome in sorted(_outcomes.items())
    ]
    Path(path).write_text(json.dumps({"tests": tests}, indent=1) + "\n", encoding="utf-8")
