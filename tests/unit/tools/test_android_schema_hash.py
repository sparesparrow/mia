"""The Android build must not silently bake in a wrong schema hash (REQ-UPD-002, ADR-0023)."""

import importlib.machinery
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.req("REQ-UPD-002")

ROOT = Path(__file__).resolve().parents[3]
GRADLE = (ROOT / "apps" / "android" / "app" / "build.gradle").read_text(encoding="utf-8")


def _tool():
    loader = importlib.machinery.SourceFileLoader("mia_apply_update", str(ROOT / "bin" / "mia-apply-update"))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("mia_apply_update", loader))
    loader.exec_module(mod)
    return mod


def test_the_ci_helper_prints_the_hash_the_pi_computes():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "ci" / "schema_hash.py")], capture_output=True, text=True, check=True)
    files = {p.name: p.read_bytes() for p in (ROOT / "schemas").glob("*.fbs")}
    assert out.stdout.strip() == _tool().schema_hash(files)


def test_gradle_fails_when_the_schemas_are_missing_and_no_hash_is_supplied():
    body = GRADLE[GRADLE.index("def getMiaSchemaHash()"):]
    body = body[: body.index("\ndef getVersionCode")]
    assert "throw new GradleException" in body and 'System.getenv("MIA_SCHEMA_HASH")' in body
    assert body.index("isDirectory()") < body.index("MessageDigest")
    assert "has no *.fbs files" in body


@pytest.mark.parametrize("name", ["Dockerfile", "Dockerfile.test"])
def test_docker_builds_receive_the_hash(name):
    text = (ROOT / "apps" / "android" / name).read_text(encoding="utf-8")
    assert re.search(r"^ARG MIA_SCHEMA_HASH$", text, re.M) and "ENV MIA_SCHEMA_HASH=${MIA_SCHEMA_HASH}" in text
