"""Tests for FlatBuffers Vehicle schema"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVehicleFlatBuffers(unittest.TestCase):
    """Test FlatBuffers schema generation and usage"""
    
    def test_import_citroen_telemetry(self):
        """Test that CitroenTelemetry can be imported"""
        try:
            from Mia.Vehicle import CitroenTelemetry
            self.assertIsNotNone(CitroenTelemetry)
        except ImportError as e:
            self.skipTest(f"FlatBuffers not generated: {e}")
    
    def test_import_dpf_status(self):
        """Test that DpfStatus enum can be imported"""
        try:
            from Mia.Vehicle import DpfStatus
            self.assertIsNotNone(DpfStatus)
        except ImportError as e:
            self.skipTest(f"FlatBuffers not generated: {e}")
    
    def test_create_telemetry_message(self):
        """Test creating a telemetry message"""
        try:
            import flatbuffers
            from Mia.Vehicle import CitroenTelemetry
            
            builder = flatbuffers.Builder(256)
            CitroenTelemetry.CitroenTelemetryStart(builder)
            CitroenTelemetry.CitroenTelemetryAddRpm(builder, 2500.0)
            CitroenTelemetry.CitroenTelemetryAddSpeedKmh(builder, 60.0)
            CitroenTelemetry.CitroenTelemetryAddCoolantTempC(builder, 85.0)
            telemetry = CitroenTelemetry.CitroenTelemetryEnd(builder)
            builder.Finish(telemetry)
            
            buf = builder.Output()
            self.assertGreater(len(buf), 0)
        except ImportError as e:
            self.skipTest(f"FlatBuffers not available: {e}")
    
    def test_dpf_status_values(self):
        """Test DPF status enum values"""
        try:
            from Mia.Vehicle.DpfStatus import DpfStatus
            self.assertEqual(DpfStatus.Normal, 0)
            self.assertEqual(DpfStatus.Regenerating, 1)
            self.assertEqual(DpfStatus.Warning, 2)
        except ImportError as e:
            self.skipTest(f"FlatBuffers not generated: {e}")


if __name__ == '__main__':
    unittest.main()
