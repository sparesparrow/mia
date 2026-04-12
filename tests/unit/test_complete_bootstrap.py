"""Targeted tests for the complete bootstrap script."""

import importlib.util
import io
import sys
import tarfile
from pathlib import Path

import pytest


def load_complete_bootstrap_module():
    """Import the script module so its helpers can be tested."""
    module_path = Path(__file__).resolve().parents[2] / "complete-bootstrap.py"
    spec = importlib.util.spec_from_file_location("complete_bootstrap", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_extract_archive_rejects_tar_path_traversal(tmp_path):
    """Bootstrap archive extraction should reject path traversal members."""
    module = load_complete_bootstrap_module()
    manager = module.BootstrapManager(str(tmp_path))

    archive_path = tmp_path / "malicious.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        payload = b"malicious"
        info = tarfile.TarInfo(name="../escape.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))

    extract_to = tmp_path / "extract"
    extract_to.mkdir()

    assert manager.extract_archive(archive_path, extract_to) is False
    assert not (tmp_path / "escape.txt").exists()


def test_verify_installation_succeeds_with_required_tools(tmp_path, monkeypatch):
    """Verification mode should succeed when Conan and required Python packages exist."""
    module = load_complete_bootstrap_module()
    manager = module.BootstrapManager(str(tmp_path))

    conan_dir = tmp_path / "tools" / "conan"
    conan_dir.mkdir(parents=True)
    (conan_dir / "conan").write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(module.importlib.util, "find_spec", lambda name: object())

    assert manager.verify_installation() is True