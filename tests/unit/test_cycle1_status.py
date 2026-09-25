from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_cycle1_status_is_evidence_based():
    status = yaml.safe_load((ROOT / "docs" / "status" / "cycle1.yaml").read_text())
    assert status["cycle"] == 1
    assert status["safety"]["active_uds"] is False
    assert status["safety"]["actuation"] is False
    assert status["safety"]["vehicle_transmit_allowed"] is False
    states = {
        "implemented_and_ci_tested",
        "simulation_tested",
        "bench_tested",
        "hardware_tested",
        "vehicle_installed",
        "planned",
        "blocked",
    }
    for entry in status["specialists"].values():
        assert entry["state"] in states
        assert entry["claim"] and entry["proof"] and "not_proven" in entry
