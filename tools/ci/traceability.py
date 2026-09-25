#!/usr/bin/env python3
"""Check that the evidence each requirement claims is backed by tests and records.

    python tools/ci/traceability.py check [--pytest-report req-report.json]
    python tools/ci/traceability.py matrix --pytest-report req-report.json [--out build/traceability.md]

The pytest report comes from `pytest tests/ --req-report=req-report.json` (tests/plugins/req_traceability.py).
Rules are in spec/README.md and ADR-0010: CI can support a claim up to simulation_tested; anything
stronger also needs a record in spec/evidence/<REQ-ID>/.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

UNTESTED_STATES = ("planned", "blocked", "implemented_untested")
CI_STATES = ("implemented_and_ci_tested", "simulation_tested")
RECORD_STATES = ("bench_tested", "hardware_tested", "vehicle_installed")

REQ_ID = re.compile(r"REQ-[A-Z]+-\d{3}")
# `@req REQ-AND-012` comment tags in tests that pytest does not run.
REQ_TAG = re.compile(r"@req\b([^\n]*)")
# pytest.mark.req("REQ-…", …) in Python tests, used when no pytest report is given.
PY_REQ_MARK = re.compile(r"mark\.req\(([^)]*)\)")

# Tag globs whose tests run in CI (android-test.yml runs ./gradlew testDebugUnitTest).
CI_TAG_GLOBS = ("apps/android/app/src/test/**/*.kt",)
# Tag globs whose tests exist but no CI job runs yet: they link, but never count as CI evidence.
OTHER_TAG_GLOBS = (
    "apps/android/app/src/androidTest/**/*.kt",
    "apps/rpi-backend/cpp-audio/core/tests/**/*.cpp",
    "web/**/*.test.js",
)
PY_TEST_GLOB = "tests/**/test_*.py"


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    untested: list[str] = field(default_factory=list)


def load_registry(root: Path = REPO_ROOT) -> tuple[dict[str, dict], list[str]]:
    """Return ({REQ-ID: requirement + '_file'}, errors) for spec/requirements/*.yaml."""
    from jsonschema import Draft202012Validator

    req_dir = root / "spec" / "requirements"
    validator = Draft202012Validator(json.loads((req_dir / "schema.json").read_text(encoding="utf-8")))
    requirements: dict[str, dict] = {}
    errors: list[str] = []
    for path in sorted(req_dir.glob("*.yaml")):
        rel = path.relative_to(root).as_posix()
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for err in validator.iter_errors(doc):
            where = "/".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"{rel}: {where}: {err.message}")
        for req in (doc or {}).get("requirements") or []:
            rid = req.get("id") if isinstance(req, dict) else None
            if not rid:
                continue
            if rid in requirements:
                errors.append(f"{rel}: {rid} is also defined in {requirements[rid]['_file']}")
                continue
            requirements[rid] = {**req, "_file": rel}
    return requirements, errors


def requirement_ids(root: Path = REPO_ROOT) -> set[str]:
    return set(load_registry(root)[0])


def _scan(root: Path, globs: tuple[str, ...], pattern: re.Pattern) -> dict[str, list[str]]:
    """Return {REQ-ID: [repo-relative file]} for IDs found by `pattern` in files matching `globs`."""
    found: dict[str, list[str]] = defaultdict(list)
    for glob in globs:
        for path in sorted(root.glob(glob)):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in pattern.finditer(text):
                for rid in REQ_ID.findall(match.group(1)):
                    rel = path.relative_to(root).as_posix()
                    if rel not in found[rid]:
                        found[rid].append(rel)
    return found


def load_pytest_report(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["tests"]


def check(root: Path = REPO_ROOT, report: list[dict] | None = None) -> Result:
    result = Result()
    requirements, result.errors = load_registry(root)
    known = set(requirements)

    ci_tags = _scan(root, CI_TAG_GLOBS, REQ_TAG)
    other_tags = _scan(root, OTHER_TAG_GLOBS, REQ_TAG)
    py_marks = _scan(root, (PY_TEST_GLOB,), PY_REQ_MARK)

    # Outcomes per requirement from the pytest report: {REQ: [(nodeid, outcome)]}.
    outcomes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for test in report or []:
        for rid in test["reqs"]:
            outcomes[rid].append((test["nodeid"], test["outcome"]))

    for source, tags in (("comment tag", ci_tags), ("comment tag", other_tags), ("pytest marker", py_marks)):
        for rid, files in tags.items():
            if rid not in known:
                result.errors.append(f"{', '.join(files)}: {source} names unknown requirement {rid}")
    for rid in sorted(set(outcomes) - known):
        result.errors.append(f"pytest report names unknown requirement {rid}")

    decisions_dir = root / "spec" / "decisions"
    for rid, req in sorted(requirements.items()):
        where = f"{req['_file']}: {rid}"
        for rel in req.get("implemented_in") or []:
            if not (root / rel).exists():
                result.errors.append(f"{where}: implemented_in path does not exist: {rel}")
        for adr in req.get("decisions") or []:
            if not list(decisions_dir.glob(f"{adr.split('-')[1]}-*.md")):
                result.errors.append(f"{where}: decision {adr} has no spec/decisions/{adr.split('-')[1]}-*.md")

        state = req.get("evidence")
        passed = [n for n, o in outcomes.get(rid, []) if o == "passed"]
        failed = [n for n, o in outcomes.get(rid, []) if o == "failed"]
        linked = bool(passed) or bool(ci_tags.get(rid)) or (report is None and bool(py_marks.get(rid)))

        if state in UNTESTED_STATES:
            if state == "implemented_untested":
                if passed or ci_tags.get(rid):
                    result.warnings.append(f"{where}: implemented_untested but has passing linked tests; promote?")
                else:
                    result.untested.append(rid)
            continue

        if failed:
            result.errors.append(f"{where}: claims {state} but linked tests fail: {', '.join(failed)}")
        if not linked:
            hint = " (no passing test in the pytest report)" if report is not None else ""
            result.errors.append(f"{where}: claims {state} but no test that runs in CI links to it{hint}")
        if state in RECORD_STATES:
            records = list((root / "spec" / "evidence" / rid).glob(f"*-{state}.md"))
            if not records:
                result.errors.append(f"{where}: claims {state} but spec/evidence/{rid}/ has no *-{state}.md record")

    if report is not None:
        untagged = sorted({t["file"] for t in report if not t["reqs"]})
        for rel in untagged:
            result.warnings.append(f"{rel}: no test in this file names a requirement")
    return result


def matrix(root: Path = REPO_ROOT, report: list[dict] | None = None) -> str:
    requirements, _ = load_registry(root)
    ci_tags = _scan(root, CI_TAG_GLOBS, REQ_TAG)
    other_tags = _scan(root, OTHER_TAG_GLOBS, REQ_TAG)
    per_req: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for test in report or []:
        for rid in test["reqs"]:
            per_req[rid][test["file"]].append(test["outcome"])

    lines = [
        "# Requirements traceability",
        "",
        "Generated by `tools/ci/traceability.py matrix`. Do not edit.",
        "",
        "| Requirement | Evidence | Implemented in | Tests | Evidence records |",
        "|---|---|---|---|---|",
    ]
    for rid, req in sorted(requirements.items()):
        tests = [f"`{f}` ({o.count('passed')}/{len(o)} passed)" for f, o in sorted(per_req[rid].items())]
        tests += [f"`{f}`" for f in ci_tags.get(rid, [])]
        tests += [f"`{f}` (not run in CI)" for f in other_tags.get(rid, [])]
        records = sorted(p.name for p in (root / "spec" / "evidence" / rid).glob("*.md"))
        code = "<br>".join(f"`{p}`" for p in req.get("implemented_in") or [])
        lines.append(
            f"| **{rid}** {req['title']} | `{req['evidence']}` | {code} | "
            f"{'<br>'.join(tests) or '—'} | {'<br>'.join(records) or '—'} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="fail when a requirement claims more than its tests and records support")
    p_check.add_argument("--pytest-report", type=Path, help="JSON written by pytest --req-report")
    p_matrix = sub.add_parser("matrix", help="write the requirement -> code -> tests -> evidence table")
    p_matrix.add_argument("--pytest-report", type=Path)
    p_matrix.add_argument("--out", type=Path, default=REPO_ROOT / "build" / "traceability.md")
    args = parser.parse_args(argv)

    report = load_pytest_report(args.pytest_report) if args.pytest_report else None
    if args.command == "matrix":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(matrix(REPO_ROOT, report), encoding="utf-8")
        print(f"wrote {args.out}")
        return 0

    result = check(REPO_ROOT, report)
    for warning in result.warnings:
        print(f"warning: {warning}")
    if result.untested:
        print(f"gap: {len(result.untested)} requirements are implemented_untested: {' '.join(result.untested)}")
    for error in result.errors:
        print(f"error: {error}")
    if report is None:
        print("note: no --pytest-report given; Python test links were read from source, outcomes not checked")
    print(f"traceability: {len(result.errors)} error(s), {len(result.warnings)} warning(s)")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
