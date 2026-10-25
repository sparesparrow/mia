"""The release workflow builds from paths that exist and keeps tag builds as drafts (REQ-DEP-007).

The workflow itself only runs when a tag is pushed, so a path that disappeared in a restructure
(`Mia`, `contracts`) or a source file with a syntax error stays hidden until release day. These checks
run on every pull request instead.
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.req("REQ-DEP-007")

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = yaml.safe_load(
    (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
)
SOURCE_ROOTS = ("apps/rpi-backend", "orchestration")
SKIP_PARTS = {"__pycache__", "node_modules", ".pio", "build"}


def _step(job, name):
    for step in WORKFLOW["jobs"][job]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"release.yml: job {job!r} has no step named {name!r}")


def _bundle_paths():
    """Paths after `-czf <archive>` in the backend bundle's tar command."""
    lines = _step("backend", "Build deployment bundle")["run"].splitlines()
    start = next(i for i, line in enumerate(lines) if "-czf" in line)
    paths = []
    for line in lines[start + 1 :]:
        token = line.strip().rstrip("\\").strip()
        if token and not token.startswith(("ls ", "mkdir ", "-")):
            paths.append(token)
        if not line.rstrip().endswith("\\"):
            break
    return paths


def test_the_bundle_archives_only_paths_that_exist():
    paths = _bundle_paths()
    assert paths, "could not read the tar paths from release.yml"
    assert [p for p in paths if not (ROOT / p).exists()] == []


def test_the_bundle_still_ships_the_backend_the_schemas_and_the_version():
    paths = _bundle_paths()
    for required in ("apps/rpi-backend", "orchestration", "schemas", "VERSION.txt"):
        assert required in paths


def test_the_compile_check_lists_only_paths_that_exist():
    run = _step("backend", "Verify backend imports")["run"]
    match = re.search(r"compileall -q ([^\n]+)", run)
    assert match, "release.yml no longer runs compileall"
    targets = match.group(1).split()
    assert targets and [t for t in targets if not (ROOT / t).exists()] == []


def test_every_backend_source_compiles():
    failures = []
    for base in SOURCE_ROOTS:
        for path in (ROOT / base).rglob("*.py"):
            if SKIP_PARTS & set(path.relative_to(ROOT).parts):
                continue
            try:
                compile(path.read_bytes(), str(path), "exec")
            except SyntaxError as exc:
                failures.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
    assert failures == []


def test_a_pushed_tag_builds_a_draft_and_only_a_manual_run_can_opt_out():
    expression = _step("publish", "Publish GitHub Release")["with"]["draft"]
    assert "github.event_name != 'workflow_dispatch'" in expression
    assert "inputs.draft" in expression
    assert (
        "== 'workflow_dispatch' &&" not in expression
    )  # the old rule: draft only when run by hand
