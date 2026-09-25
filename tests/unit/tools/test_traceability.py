"""tools/ci/traceability.py and the req marker plugin keep requirement claims honest (ADR-0010)."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.req("REQ-NFR-004")

REPO_ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "traceability_under_test", REPO_ROOT / "tools" / "ci" / "traceability.py"
)
traceability = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = traceability
_spec.loader.exec_module(traceability)


def _requirement(rid="REQ-TST-001", evidence="implemented_and_ci_tested", **extra):
    req = {
        "id": rid,
        "title": "Thing",
        "statement": "The thing shall work.",
        "evidence": evidence,
        "implemented_in": ["src/thing.py"],
    }
    if evidence not in traceability.UNTESTED_STATES:
        req["acceptance"] = ["It works"]
    req.update(extra)
    return req


@pytest.fixture
def repo(tmp_path):
    """A minimal repository: schema, one ADR, one source file and a writable registry."""
    (tmp_path / "spec" / "requirements").mkdir(parents=True)
    shutil.copy(REPO_ROOT / "spec" / "requirements" / "schema.json", tmp_path / "spec" / "requirements")
    (tmp_path / "spec" / "decisions").mkdir()
    (tmp_path / "spec" / "decisions" / "0001-a-decision.md").write_text("# ADR-0001\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "thing.py").write_text("")

    def write(*requirements):
        doc = {"area": "test", "title": "Test", "requirements": list(requirements)}
        (tmp_path / "spec" / "requirements" / "test.yaml").write_text(yaml.safe_dump(doc))
        return tmp_path

    return write


def _report(*tests):
    return [
        {"nodeid": f"tests/test_x.py::{n}", "file": "tests/test_x.py", "reqs": r, "outcome": o} for n, r, o in tests
    ]


def test_ci_tested_requirement_with_a_passing_test_passes(repo):
    root = repo(_requirement(decisions=["ADR-0001"]))
    result = traceability.check(root, _report(("t", ["REQ-TST-001"], "passed")))
    assert result.errors == []


def test_ci_tested_requirement_without_a_test_fails(repo):
    root = repo(_requirement())
    errors = traceability.check(root, _report(("t", [], "passed"))).errors
    assert any("REQ-TST-001" in e and "no test" in e for e in errors)


def test_a_failing_linked_test_fails_the_check(repo):
    root = repo(_requirement())
    report = _report(("ok", ["REQ-TST-001"], "passed"), ("broken", ["REQ-TST-001"], "failed"))
    errors = traceability.check(root, report).errors
    assert any("linked tests fail" in e and "broken" in e for e in errors)


def test_a_skipped_test_is_not_evidence(repo):
    root = repo(_requirement())
    assert traceability.check(root, _report(("t", ["REQ-TST-001"], "skipped"))).errors


def test_bench_tested_needs_an_evidence_record(repo):
    root = repo(_requirement(evidence="bench_tested"))
    report = _report(("t", ["REQ-TST-001"], "passed"))
    assert any("spec/evidence/REQ-TST-001" in e for e in traceability.check(root, report).errors)

    record = root / "spec" / "evidence" / "REQ-TST-001" / "2026-09-25-bench_tested.md"
    record.parent.mkdir(parents=True)
    record.write_text("# REQ-TST-001: bench_tested\n")
    assert traceability.check(root, report).errors == []


def test_registry_problems_are_errors(repo):
    root = repo(
        _requirement(implemented_in=["src/missing.py"], decisions=["ADR-0042"]),
        _requirement(),  # duplicate ID
        {"id": "REQ-TST-002", "title": "No statement", "evidence": "planned", "implemented_in": []},
    )
    errors = traceability.check(root, _report(("t", ["REQ-TST-001"], "passed"))).errors
    assert any("src/missing.py" in e for e in errors)
    assert any("ADR-0042" in e for e in errors)
    assert any("also defined" in e for e in errors)
    assert any("'statement' is a required property" in e for e in errors)


def test_unknown_ids_in_comment_tags_and_reports_are_errors(repo):
    root = repo(_requirement())
    kotlin = root / "apps" / "android" / "app" / "src" / "test" / "ThingTest.kt"
    kotlin.parent.mkdir(parents=True)
    kotlin.write_text("package x\n\n// @req REQ-TST-001 REQ-TST-999\n")
    errors = traceability.check(root, _report(("t", ["REQ-TST-001", "REQ-TST-998"], "passed"))).errors
    assert any("REQ-TST-999" in e and "ThingTest.kt" in e for e in errors)
    assert any("REQ-TST-998" in e for e in errors)


def test_android_unit_test_tag_links_but_instrumented_tag_does_not(repo):
    root = repo(_requirement())
    instrumented = root / "apps" / "android" / "app" / "src" / "androidTest" / "ThingTest.kt"
    instrumented.parent.mkdir(parents=True)
    instrumented.write_text("// @req REQ-TST-001\n")
    assert traceability.check(root, []).errors

    unit = root / "apps" / "android" / "app" / "src" / "test" / "ThingTest.kt"
    unit.parent.mkdir(parents=True)
    unit.write_text("// @req REQ-TST-001\n")
    assert traceability.check(root, []).errors == []


def test_untested_requirements_are_reported_as_gaps_not_errors(repo):
    root = repo(
        _requirement(evidence="implemented_untested"), _requirement("REQ-TST-002", "planned", implemented_in=[])
    )
    result = traceability.check(root, _report(("t", [], "passed")))
    assert result.errors == []
    assert result.untested == ["REQ-TST-001"]
    assert any("tests/test_x.py" in w for w in result.warnings)


def test_matrix_lists_code_tests_and_records(repo):
    root = repo(_requirement())
    table = traceability.matrix(root, _report(("t", ["REQ-TST-001"], "passed")))
    assert (
        "| **REQ-TST-001** Thing | `implemented_and_ci_tested` | `src/thing.py` | `tests/test_x.py` (1/1 passed)"
        in table
    )


def test_the_repository_registry_passes_the_static_check():
    result = traceability.check(REPO_ROOT)
    assert result.errors == []


def _run_pytest(tmp_path, body, *args):
    test_file = tmp_path / "test_tagged.py"
    test_file.write_text("import pytest\n\n" + body)
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "tests" / "plugins")}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "req_traceability",
            "-p",
            "no:cacheprovider",
            "-q",
            "--rootdir",
            str(tmp_path),
            "-c",
            os.devnull,
            str(test_file),
            *args,
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=120,
    )


def test_an_unknown_requirement_id_stops_the_pytest_run(tmp_path):
    bogus = "REQ-X-" + "999"  # split so the static scan of this file does not see it
    proc = _run_pytest(tmp_path, f'@pytest.mark.req("{bogus}")\ndef test_x():\n    pass\n')
    assert proc.returncode != 0
    assert bogus in proc.stdout + proc.stderr


def test_req_report_records_ids_and_outcomes(tmp_path):
    body = (
        'pytestmark = pytest.mark.req("REQ-NFR-004")\n\n'
        "def test_ok():\n    pass\n\n"
        "def test_broken():\n    assert False\n"
    )
    report = tmp_path / "req.json"
    proc = _run_pytest(tmp_path, body, f"--req-report={report}")
    assert proc.returncode == 1
    tests = {t["nodeid"].split("::")[-1]: t for t in json.loads(report.read_text())["tests"]}
    assert tests["test_ok"]["outcome"] == "passed"
    assert tests["test_broken"]["outcome"] == "failed"
    assert tests["test_ok"]["reqs"] == ["REQ-NFR-004"]
