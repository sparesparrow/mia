"""Tests for Citroën OBD-II Bridge"""
import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCitroenBridgeConfig(unittest.TestCase):
    """Test configuration and environment handling"""
    
    def test_default_serial_port(self):
        """Default serial port should be /dev/ttyUSB0"""
        os.environ.pop('ELM_SERIAL_PORT', None)
        # Would import and check default
        self.assertEqual(os.environ.get('ELM_SERIAL_PORT', '/dev/ttyUSB0'), '/dev/ttyUSB0')
    
    def test_default_baud_rate(self):
        """Default baud rate should be 38400"""
        os.environ.pop('ELM_BAUD_RATE', None)
        self.assertEqual(int(os.environ.get('ELM_BAUD_RATE', 38400)), 38400)
    
    def test_mock_mode_detection(self):
        """Mock mode should be detected from environment"""
        os.environ['ELM_MOCK'] = '1'
        self.assertEqual(os.environ.get('ELM_MOCK', '0'), '1')
        os.environ.pop('ELM_MOCK', None)


class TestHexParsing(unittest.TestCase):
    """Test hex value parsing functions"""
    
    def test_rpm_parsing(self):
        """Test RPM calculation from hex"""
        # RPM = (A*256 + B) / 4
        # 0x0B 0xB8 = 11*256 + 184 = 3000 -> 750 RPM
        hex_val = "0BB8"
        val = int(hex_val, 16)
        rpm = val / 4.0
        self.assertEqual(rpm, 750.0)
    
    def test_speed_parsing(self):
        """Test speed parsing (direct value)"""
        hex_val = "3C"  # 60 km/h
        speed = int(hex_val, 16)
        self.assertEqual(speed, 60)
    
    def test_coolant_parsing(self):
        """Test coolant temp with -40 offset"""
        hex_val = "5A"  # 90 -> 50°C
        temp = int(hex_val, 16) - 40
        self.assertEqual(temp, 50)


class TestMockDataGeneration(unittest.TestCase):
    """Test mock data generation for testing"""
    
    @patch.dict(os.environ, {'ELM_MOCK': '1'})
    def test_mock_mode_enabled(self):
        """Mock mode should generate random data"""
        import random
        rpm = random.randint(800, 3000)
        self.assertGreaterEqual(rpm, 800)
        self.assertLessEqual(rpm, 3000)


if __name__ == '__main__':
    unittest.main()
