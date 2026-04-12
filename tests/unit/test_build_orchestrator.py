"""Targeted tests for build orchestrator security scan parsing."""

import pytest

import build_orchestrator


class DummyProcess:
    """Simple async subprocess stub for scanner tests."""

    def __init__(self, returncode, stdout, stderr=b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


def test_parse_json_output_rejects_invalid_json():
    """Invalid scanner output should be ignored instead of raising."""
    parsed = build_orchestrator.SecurityScanner._parse_json_output(
        "semgrep",
        b"not-json",
        b"scanner warning",
    )

    assert parsed is None


def test_summarize_trivy_results_counts_nested_vulnerabilities():
    """Trivy summaries should count vulnerabilities, not result sections."""
    summary = build_orchestrator.SecurityScanner._summarize_trivy_results(
        {
            "Results": [
                {
                    "Target": "image",
                    "Vulnerabilities": [
                        {"Severity": "CRITICAL"},
                        {"Severity": "HIGH"},
                    ],
                },
                {
                    "Target": "library",
                    "Vulnerabilities": [{"Severity": "HIGH"}],
                },
            ]
        }
    )

    assert summary["total_vulns"] == 3
    assert summary["critical"] == 1
    assert summary["high"] == 2


@pytest.mark.asyncio
async def test_scan_source_code_keeps_nonzero_findings(tmp_path, monkeypatch):
    """Bandit and Semgrep findings should still be parsed on exit code 1."""
    source_path = tmp_path / "project"
    source_path.mkdir()
    (source_path / "app.py").write_text("print('hello')\n", encoding="utf-8")

    processes = [
        DummyProcess(1, b'{"results": [{"issue_text": "example"}]}'),
        DummyProcess(1, b'{"results": [{"check_id": "example"}]}'),
    ]

    async def fake_create_subprocess_exec(*args, **kwargs):
        return processes.pop(0)

    monkeypatch.setattr(build_orchestrator.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    scanner = build_orchestrator.SecurityScanner()
    results = await scanner.scan_source_code(source_path)

    assert results["bandit"]["results"][0]["issue_text"] == "example"
    assert results["semgrep"]["results"][0]["check_id"] == "example"