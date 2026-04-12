"""Test harness for automotive-mcp-bridge: signal_router.py.

Covers CANSignalMetadata.is_broadcast(), ECURange initialization and contains(),
DIDEntry readability/writability, and enum value existence.

Note: safety_wrapper.py is intentionally excluded — it requires hardware-level
relative imports (.triple_buffers, .automotive_timing).
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Module loading — signal_router.py has no external deps (pure stdlib)
# ---------------------------------------------------------------------------

_SR_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "automotive-mcp-bridge",
    "signal_router.py",
)

_sr_spec = importlib.util.spec_from_file_location("signal_router", _SR_PATH)
_sr_module = importlib.util.module_from_spec(_sr_spec)
_sr_spec.loader.exec_module(_sr_module)

MessageType = _sr_module.MessageType
AddressingMode = _sr_module.AddressingMode
CANSignalMetadata = _sr_module.CANSignalMetadata
ECURange = _sr_module.ECURange
DIDCategory = _sr_module.DIDCategory
DIDEntry = _sr_module.DIDEntry


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMessageTypeEnum:
    """MessageType enum completeness."""

    def test_all_expected_values_exist(self):
        expected = {"DIAGNOSTIC", "SENSOR_DATA", "CONTROL_COMMAND", "STATUS_INFO", "BROADCAST"}
        actual = {m.name for m in MessageType}
        assert expected.issubset(actual)

    def test_diagnostic_value(self):
        assert MessageType.DIAGNOSTIC.value == "diagnostic"

    def test_broadcast_value(self):
        assert MessageType.BROADCAST.value == "broadcast"


@pytest.mark.unit
class TestAddressingModeEnum:
    """AddressingMode enum values."""

    def test_physical_value(self):
        assert AddressingMode.PHYSICAL.value == "physical"

    def test_functional_value(self):
        assert AddressingMode.FUNCTIONAL.value == "functional"


@pytest.mark.unit
class TestCANSignalMetadataIsBroadcast:
    """CANSignalMetadata.is_broadcast() logic."""

    def _make_signal(self, mode, targets=None):
        sig = CANSignalMetadata(
            message_id=0x7DF,
            signal_name="engine_rpm",
            message_type=MessageType.DIAGNOSTIC,
            addressing_mode=mode,
        )
        if targets is not None:
            sig.ecu_targets = targets
        return sig

    def test_functional_addressing_is_broadcast(self):
        sig = self._make_signal(AddressingMode.FUNCTIONAL)
        assert sig.is_broadcast() is True

    def test_physical_with_no_targets_is_broadcast(self):
        sig = self._make_signal(AddressingMode.PHYSICAL, targets=set())
        assert sig.is_broadcast() is True

    def test_physical_with_targets_is_not_broadcast(self):
        sig = self._make_signal(AddressingMode.PHYSICAL, targets={0x7E8})
        assert sig.is_broadcast() is False

    def test_ecu_targets_defaults_to_empty_set(self):
        sig = CANSignalMetadata(
            message_id=0x7DF,
            signal_name="test",
            message_type=MessageType.STATUS_INFO,
            addressing_mode=AddressingMode.PHYSICAL,
        )
        assert sig.ecu_targets == set()

    def test_default_data_length(self):
        sig = self._make_signal(AddressingMode.PHYSICAL)
        assert sig.data_length == 8

    def test_default_priority(self):
        sig = self._make_signal(AddressingMode.PHYSICAL)
        assert sig.priority == 0

    def test_default_cycle_time_ms(self):
        sig = self._make_signal(AddressingMode.PHYSICAL)
        assert sig.cycle_time_ms == 100


@pytest.mark.unit
class TestECURange:
    """ECURange initialization and boundary checks."""

    def setup_method(self):
        self.ecu_range = ECURange(start_id=0x600, end_id=0x6FF, ecu_name="BSI")

    def test_attributes_stored_correctly(self):
        assert self.ecu_range.start_id == 0x600
        assert self.ecu_range.end_id == 0x6FF
        assert self.ecu_range.ecu_name == "BSI"

    def test_range_size_computed(self):
        assert self.ecu_range.range_size == 0x100  # 256

    def test_contains_lower_bound(self):
        assert self.ecu_range.contains(0x600) is True

    def test_contains_upper_bound(self):
        assert self.ecu_range.contains(0x6FF) is True

    def test_contains_midpoint(self):
        assert self.ecu_range.contains(0x650) is True

    def test_does_not_contain_below_range(self):
        assert self.ecu_range.contains(0x5FF) is False

    def test_does_not_contain_above_range(self):
        assert self.ecu_range.contains(0x700) is False

    def test_get_ecu_name(self):
        assert self.ecu_range.get_ecu_name() == "BSI"


@pytest.mark.unit
class TestDIDEntry:
    """DIDEntry readability and writability flags."""

    def test_did_with_read_handler_is_readable(self):
        entry = DIDEntry(
            did=0xF190,
            name="VIN",
            category=DIDCategory.IDENTIFICATION,
            data_length=17,
            description="Vehicle Identification Number",
            read_handler=lambda: b"\x00" * 17,
        )
        assert entry.is_readable() is True
        assert entry.is_writable() is False

    def test_did_without_handlers_not_readable_or_writable(self):
        entry = DIDEntry(
            did=0xFD01,
            name="OEM_DATA",
            category=DIDCategory.OEM_SPECIFIC,
            data_length=4,
            description="OEM specific data",
        )
        assert entry.is_readable() is False
        assert entry.is_writable() is False

    def test_identification_category_range(self):
        entry = DIDEntry(
            did=0xF190, name="VIN", category=DIDCategory.IDENTIFICATION, data_length=17, description=""
        )
        low, high = entry.get_category_range()
        assert low == 0xF100
        assert high == 0xF1FF
