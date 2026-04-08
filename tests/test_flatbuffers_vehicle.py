"""Tests for the Citroen vehicle FlatBuffers helpers."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVehicleFlatBuffers(unittest.TestCase):
    """Test FlatBuffers schema generation and vehicle codec usage."""

    def test_import_vehicle_codec(self):
        """Test that the shared vehicle codec can be imported."""
        try:
            from Mia.vehicle_codec import (
                build_citroen_telemetry,
                build_vehicle_telemetry,
                parse_citroen_telemetry,
                parse_vehicle_telemetry,
            )

            self.assertIsNotNone(build_citroen_telemetry)
            self.assertIsNotNone(build_vehicle_telemetry)
            self.assertIsNotNone(parse_citroen_telemetry)
            self.assertIsNotNone(parse_vehicle_telemetry)
        except ImportError as error:
            self.skipTest(f"FlatBuffers vehicle codec not available: {error}")

    def test_round_trip_vehicle_telemetry(self):
        """Test encoding and decoding canonical vehicle telemetry fields."""
        try:
            from Mia.DpfStatus import DpfStatus
            from Mia.vehicle_codec import (
                VEHICLE_FILE_IDENTIFIER,
                buffer_has_vehicle_identifier,
                build_vehicle_telemetry,
                parse_citroen_telemetry,
                parse_vehicle_telemetry,
            )

            original = {
                "rpm": 2500.0,
                "speed_kmh": 60.0,
                "coolant_temp_c": 85.0,
                "dpf_soot_load_percent": 42.5,
                "dpf_soot_mass_g": 12.34,
                "dpf_regeneration_status": DpfStatus.Critical,
                "eolys_additive_level_percent": 76.5,
                "eolys_additive_level_l": 2.25,
                "battery_voltage": 12.6,
                "oil_temperature_c": 91.0,
                "intake_air_temp_c": 24.5,
                "fuel_level_percent": 48.0,
                "engine_load_percent": 39.5,
                "timestamp": 1710000000123,
            }

            buf = build_vehicle_telemetry(original)
            parsed = parse_vehicle_telemetry(buf, require_identifier=True)
            legacy = parse_citroen_telemetry(buf, require_identifier=True)

            self.assertGreater(len(buf), 0)
            self.assertEqual(buf[4:8], VEHICLE_FILE_IDENTIFIER)
            self.assertTrue(buffer_has_vehicle_identifier(buf))
            self.assertEqual(parsed, original)
            self.assertEqual(legacy["dpf_status"], DpfStatus.Critical)
            self.assertEqual(legacy["eolys_level_pct"], original["eolys_additive_level_percent"])
            self.assertEqual(legacy["eolys_level_l"], original["eolys_additive_level_l"])
            self.assertEqual(legacy["oil_temp_c"], original["oil_temperature_c"])
            self.assertEqual(legacy["timestamp"], original["timestamp"])
        except ImportError as error:
            self.skipTest(f"FlatBuffers not available: {error}")

    def test_build_citroen_telemetry_accepts_legacy_aliases(self):
        """Test that legacy payload field names still map to the evolved schema."""
        try:
            from Mia.DpfStatus import DpfStatus
            from Mia.vehicle_codec import build_citroen_telemetry, parse_vehicle_telemetry

            legacy_payload = {
                "rpm": 1800.0,
                "speed_kmh": 42.0,
                "coolant_temp_c": 83.0,
                "dpf_soot_load_percent": 22.5,
                "dpf_soot_mass_g": 8.75,
                "dpf_status": DpfStatus.Regenerating,
                "eolys_level_pct": 64.0,
                "eolys_level_l": 1.75,
                "battery_voltage": 12.4,
                "oil_temp_c": 87.0,
                "timestamp": 1710000000999,
            }

            parsed = parse_vehicle_telemetry(
                build_citroen_telemetry(legacy_payload),
                require_identifier=True,
            )

            self.assertEqual(parsed["dpf_regeneration_status"], DpfStatus.Regenerating)
            self.assertEqual(parsed["eolys_additive_level_percent"], legacy_payload["eolys_level_pct"])
            self.assertEqual(parsed["eolys_additive_level_l"], legacy_payload["eolys_level_l"])
            self.assertEqual(parsed["oil_temperature_c"], legacy_payload["oil_temp_c"])
            self.assertEqual(parsed["timestamp"], legacy_payload["timestamp"])
        except ImportError as error:
            self.skipTest(f"FlatBuffers not available: {error}")

    def test_dpf_status_values(self):
        """Test DPF status enum values."""
        try:
            from Mia.DpfStatus import DpfStatus

            self.assertEqual(DpfStatus.Normal, 0)
            self.assertEqual(DpfStatus.Regenerating, 1)
            self.assertEqual(DpfStatus.Warning, 2)
            self.assertEqual(DpfStatus.Critical, 3)
        except ImportError as error:
            self.skipTest(f"FlatBuffers not generated: {error}")

    def test_parse_vehicle_telemetry_requires_identifier(self):
        """Test that strict decoding rejects buffers without the vehicle identifier."""
        try:
            from Mia.vehicle_codec import parse_vehicle_telemetry

            with self.assertRaises(ValueError):
                parse_vehicle_telemetry(b"not-a-vehicle-buffer", require_identifier=True)
        except ImportError as error:
            self.skipTest(f"FlatBuffers not available: {error}")


if __name__ == '__main__':
    unittest.main()
