"""Tests for Device Registry"""
import unittest
import time
import sys
import os
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../rpi'))

from core.registry import DeviceRegistry, DeviceProfile, DeviceType, DeviceStatus


class TestDeviceProfile(unittest.TestCase):
    """Test DeviceProfile dataclass"""
    
    def test_profile_creation(self):
        """Test creating a device profile"""
        profile = DeviceProfile(
            device_id="test_device_1",
            device_type=DeviceType.GPIO,
            name="Test GPIO Device",
            capabilities=["GPIO_SET", "GPIO_GET"]
        )
        self.assertEqual(profile.device_id, "test_device_1")
        self.assertEqual(profile.device_type, DeviceType.GPIO)
        self.assertEqual(profile.name, "Test GPIO Device")
        self.assertIn("GPIO_SET", profile.capabilities)
    
    def test_profile_auto_name(self):
        """Test auto-generated name when not provided"""
        profile = DeviceProfile(
            device_id="abc12345xyz",
            device_type=DeviceType.SERIAL
        )
        self.assertIn("serial", profile.name.lower())
    
    def test_profile_status_transitions(self):
        """Test status transitions"""
        profile = DeviceProfile(
            device_id="test_device",
            device_type=DeviceType.GPIO
        )
        
        profile.set_online()
        self.assertEqual(profile.status, DeviceStatus.ONLINE)
        
        profile.set_offline()
        self.assertEqual(profile.status, DeviceStatus.OFFLINE)
        
        profile.set_error("Connection failed")
        self.assertEqual(profile.status, DeviceStatus.ERROR)
        self.assertEqual(profile.error_message, "Connection failed")
    
    def test_profile_health_check(self):
        """Test health check with timeout"""
        profile = DeviceProfile(
            device_id="test_device",
            device_type=DeviceType.GPIO
        )
        profile.set_online()
        
        # Should be healthy immediately after going online
        self.assertTrue(profile.is_healthy(timeout_seconds=30.0))
        
        # Simulate old last_seen
        profile.last_seen = datetime.now() - timedelta(seconds=60)
        self.assertFalse(profile.is_healthy(timeout_seconds=30.0))
    
    def test_profile_serialization(self):
        """Test to_dict and from_dict"""
        profile = DeviceProfile(
            device_id="test_device",
            device_type=DeviceType.OBD,
            name="OBD Adapter",
            capabilities=["query_pid"],
            metadata={"baud_rate": 38400}
        )
        profile.set_online()
        
        # Serialize
        data = profile.to_dict()
        self.assertEqual(data["device_id"], "test_device")
        self.assertEqual(data["device_type"], "obd")
        
        # Deserialize
        restored = DeviceProfile.from_dict(data)
        self.assertEqual(restored.device_id, profile.device_id)
        self.assertEqual(restored.device_type, profile.device_type)


class TestDeviceRegistry(unittest.TestCase):
    """Test DeviceRegistry"""
    
    def setUp(self):
        """Create a fresh registry for each test"""
        self.registry = DeviceRegistry(
            health_check_interval=1.0,
            device_timeout=5.0
        )
    
    def tearDown(self):
        """Stop registry after each test"""
        self.registry.stop()
    
    def test_register_device(self):
        """Test device registration"""
        profile = DeviceProfile(
            device_id="gpio_1",
            device_type=DeviceType.GPIO,
            capabilities=["GPIO_SET"]
        )
        
        result = self.registry.register(profile)
        self.assertTrue(result)
        
        retrieved = self.registry.get("gpio_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.device_id, "gpio_1")
        self.assertEqual(retrieved.status, DeviceStatus.ONLINE)
    
    def test_unregister_device(self):
        """Test device unregistration"""
        profile = DeviceProfile(
            device_id="gpio_1",
            device_type=DeviceType.GPIO
        )
        self.registry.register(profile)
        
        result = self.registry.unregister("gpio_1")
        self.assertTrue(result)
        
        retrieved = self.registry.get("gpio_1")
        self.assertIsNone(retrieved)
    
    def test_get_by_type(self):
        """Test getting devices by type"""
        self.registry.register(DeviceProfile("gpio_1", DeviceType.GPIO))
        self.registry.register(DeviceProfile("gpio_2", DeviceType.GPIO))
        self.registry.register(DeviceProfile("obd_1", DeviceType.OBD))
        
        gpio_devices = self.registry.get_by_type(DeviceType.GPIO)
        self.assertEqual(len(gpio_devices), 2)
        
        obd_devices = self.registry.get_by_type(DeviceType.OBD)
        self.assertEqual(len(obd_devices), 1)
    
    def test_get_by_capability(self):
        """Test getting devices by capability"""
        self.registry.register(DeviceProfile(
            "gpio_1", DeviceType.GPIO,
            capabilities=["GPIO_SET", "GPIO_GET"]
        ))
        self.registry.register(DeviceProfile(
            "obd_1", DeviceType.OBD,
            capabilities=["query_pid", "GPIO_GET"]  # Unusual but for testing
        ))
        
        devices = self.registry.get_by_capability("GPIO_GET")
        self.assertEqual(len(devices), 2)
        
        devices = self.registry.get_by_capability("query_pid")
        self.assertEqual(len(devices), 1)
    
    def test_heartbeat(self):
        """Test heartbeat updates last_seen"""
        profile = DeviceProfile("gpio_1", DeviceType.GPIO)
        self.registry.register(profile)
        
        # Get initial last_seen
        device = self.registry.get("gpio_1")
        initial_last_seen = device.last_seen
        
        time.sleep(0.1)
        
        # Send heartbeat
        self.registry.heartbeat("gpio_1")
        
        device = self.registry.get("gpio_1")
        self.assertGreater(device.last_seen, initial_last_seen)
    
    def test_status_summary(self):
        """Test status summary generation"""
        self.registry.register(DeviceProfile("gpio_1", DeviceType.GPIO))
        self.registry.register(DeviceProfile("gpio_2", DeviceType.GPIO))
        self.registry.register(DeviceProfile("obd_1", DeviceType.OBD))
        
        summary = self.registry.get_status_summary()
        
        self.assertEqual(summary["total_devices"], 3)
        self.assertEqual(summary["online"], 3)
        self.assertEqual(summary["by_type"]["gpio"], 2)
        self.assertEqual(summary["by_type"]["obd"], 1)
    
    def test_device_error(self):
        """Test setting device error"""
        profile = DeviceProfile("gpio_1", DeviceType.GPIO)
        self.registry.register(profile)
        
        self.registry.set_device_error("gpio_1", "Connection lost")
        
        device = self.registry.get("gpio_1")
        self.assertEqual(device.status, DeviceStatus.ERROR)
        self.assertEqual(device.error_message, "Connection lost")
    
    def test_event_callbacks(self):
        """Test event callbacks"""
        online_events = []
        offline_events = []
        
        self.registry.on_device_online(lambda d: online_events.append(d.device_id))
        self.registry.on_device_offline(lambda d: offline_events.append(d.device_id))
        
        # Register triggers online callback
        profile = DeviceProfile("gpio_1", DeviceType.GPIO)
        self.registry.register(profile)
        self.assertIn("gpio_1", online_events)
        
        # Unregister triggers offline callback
        self.registry.unregister("gpio_1")
        self.assertIn("gpio_1", offline_events)
    
    def test_persistence(self):
        """Test state persistence"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            persistence_path = f.name
        
        try:
            # Create registry with persistence
            registry1 = DeviceRegistry(persistence_path=persistence_path)
            registry1.register(DeviceProfile("gpio_1", DeviceType.GPIO))
            registry1.register(DeviceProfile("obd_1", DeviceType.OBD))
            registry1.stop()  # This saves state
            
            # Create new registry, should load saved state
            registry2 = DeviceRegistry(persistence_path=persistence_path)
            
            self.assertEqual(len(registry2.get_all()), 2)
            
            # Devices should be offline after loading (need to re-register)
            device = registry2.get("gpio_1")
            self.assertEqual(device.status, DeviceStatus.OFFLINE)
            
            registry2.stop()
        finally:
            os.unlink(persistence_path)


class TestDeviceRegistryHealthMonitoring(unittest.TestCase):
    """Test health monitoring functionality"""
    
    def test_health_check_marks_offline(self):
        """Test that health check marks timed-out devices as offline"""
        registry = DeviceRegistry(
            health_check_interval=0.5,
            device_timeout=1.0
        )
        registry.start()
        
        try:
            profile = DeviceProfile("gpio_1", DeviceType.GPIO)
            registry.register(profile)
            
            # Should be online initially
            device = registry.get("gpio_1")
            self.assertEqual(device.status, DeviceStatus.ONLINE)
            
            # Wait for timeout + health check interval
            time.sleep(2.0)
            
            # Should be marked offline
            device = registry.get("gpio_1")
            self.assertEqual(device.status, DeviceStatus.OFFLINE)
        finally:
            registry.stop()
    
    def test_heartbeat_keeps_device_online(self):
        """Test that heartbeats keep device online"""
        registry = DeviceRegistry(
            health_check_interval=0.5,
            device_timeout=1.0
        )
        registry.start()
        
        try:
            profile = DeviceProfile("gpio_1", DeviceType.GPIO)
            registry.register(profile)
            
            # Send heartbeats to keep alive
            for _ in range(4):
                time.sleep(0.4)
                registry.heartbeat("gpio_1")
            
            # Should still be online
            device = registry.get("gpio_1")
            self.assertEqual(device.status, DeviceStatus.ONLINE)
        finally:
            registry.stop()


if __name__ == '__main__':
    unittest.main()
