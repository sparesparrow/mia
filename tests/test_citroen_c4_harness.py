"""Test harness for citroen-c4-bridge: CitroenC4Telemetry, CitroenC4State, DPFStatus.

Covers telemetry dataclass defaults (all Optional fields = None, dtc_codes = []),
enum value existence, and DPF status enum ordering.

zmq and zmq.asyncio are mocked before module load to avoid hardware deps.
"""

import importlib.util
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock zmq before loading the module
# ---------------------------------------------------------------------------
sys.modules["zmq"] = MagicMock()
sys.modules["zmq.asyncio"] = MagicMock()

_C4_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "citroen-c4-bridge",
    "main.py",
)

_c4_spec = importlib.util.spec_from_file_location("citroen_c4_main", _C4_PATH)
_c4_module = importlib.util.module_from_spec(_c4_spec)
_c4_module.__package__ = "modules.citroen_c4_bridge"
sys.modules.setdefault("modules.citroen_c4_bridge", MagicMock())
_c4_spec.loader.exec_module(_c4_module)

CitroenC4State = _c4_module.CitroenC4State
DPFStatus = _c4_module.DPFStatus
CitroenC4Telemetry = _c4_module.CitroenC4Telemetry


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCitroenC4StateEnum:
    """CitroenC4State enum completeness."""

    def test_eco_mode_exists(self):
        assert CitroenC4State.ECO_MODE.value == "eco_mode"

    def test_sport_mode_exists(self):
        assert CitroenC4State.SPORT_MODE.value == "sport_mode"

    def test_dpf_regeneration_exists(self):
        assert CitroenC4State.DPF_REGENERATION.value == "dpf_regeneration"

    def test_maintenance_due_exists(self):
        assert CitroenC4State.MAINTENANCE_DUE.value == "maintenance_due"

    def test_battery_low_exists(self):
        assert CitroenC4State.BATTERY_LOW.value == "battery_low"

    def test_engine_warning_exists(self):
        assert CitroenC4State.ENGINE_WARNING.value == "engine_warning"

    def test_all_six_states_present(self):
        assert len(CitroenC4State) == 6


@pytest.mark.unit
class TestDPFStatusEnum:
    """DPFStatus enum completeness and ordering."""

    def test_ok_value(self):
        assert DPFStatus.OK.value == "ok"

    def test_soot_high_value(self):
        assert DPFStatus.SOOT_HIGH.value == "soot_high"

    def test_regeneration_needed_value(self):
        assert DPFStatus.REGENERATION_NEEDED.value == "regeneration_needed"

    def test_regeneration_in_progress_value(self):
        assert DPFStatus.REGENERATION_IN_PROGRESS.value == "regeneration_in_progress"

    def test_filter_closing_value(self):
        assert DPFStatus.FILTER_CLOSING.value == "filter_closing"

    def test_error_value(self):
        assert DPFStatus.ERROR.value == "error"

    def test_all_six_statuses_present(self):
        assert len(DPFStatus) == 6

    def test_ok_is_not_regeneration_needed(self):
        assert DPFStatus.OK != DPFStatus.REGENERATION_NEEDED


@pytest.mark.unit
class TestCitroenC4TelemetryDefaults:
    """CitroenC4Telemetry dataclass: all Optional fields default to None."""

    def setup_method(self):
        self.telemetry = CitroenC4Telemetry()

    def test_timestamp_is_set(self):
        assert isinstance(self.telemetry.timestamp, datetime)

    def test_speed_defaults_to_none(self):
        assert self.telemetry.speed_kmh is None

    def test_engine_rpm_defaults_to_none(self):
        assert self.telemetry.engine_rpm is None

    def test_coolant_temp_defaults_to_none(self):
        assert self.telemetry.coolant_temp_c is None

    def test_fuel_level_defaults_to_none(self):
        assert self.telemetry.fuel_level_percent is None

    def test_battery_voltage_defaults_to_none(self):
        assert self.telemetry.battery_voltage is None

    def test_dpf_soot_mass_defaults_to_none(self):
        assert self.telemetry.dpf_soot_mass_g is None

    def test_dpf_status_defaults_to_none(self):
        assert self.telemetry.dpf_status is None

    def test_vehicle_mode_defaults_to_none(self):
        assert self.telemetry.vehicle_mode is None

    def test_dtc_codes_defaults_to_empty_list(self):
        assert self.telemetry.dtc_codes == []

    def test_psa_dtc_descriptions_defaults_to_empty_dict(self):
        assert self.telemetry.psa_dtc_descriptions == {}

    def test_suspension_mode_defaults_to_none(self):
        assert self.telemetry.suspension_mode is None

    def test_gear_position_defaults_to_none(self):
        assert self.telemetry.gear_position is None


@pytest.mark.unit
class TestCitroenC4TelemetryWithValues:
    """CitroenC4Telemetry field assignment."""

    def test_assign_dpf_status(self):
        t = CitroenC4Telemetry(dpf_status=DPFStatus.REGENERATION_NEEDED)
        assert t.dpf_status == DPFStatus.REGENERATION_NEEDED

    def test_assign_vehicle_mode(self):
        t = CitroenC4Telemetry(vehicle_mode=CitroenC4State.DPF_REGENERATION)
        assert t.vehicle_mode == CitroenC4State.DPF_REGENERATION

    def test_assign_speed_and_rpm(self):
        t = CitroenC4Telemetry(speed_kmh=120.5, engine_rpm=3200.0)
        assert t.speed_kmh == 120.5
        assert t.engine_rpm == 3200.0

    def test_dtc_codes_can_be_populated(self):
        t = CitroenC4Telemetry(dtc_codes=["P0420", "P0300"])
        assert len(t.dtc_codes) == 2
        assert "P0420" in t.dtc_codes
