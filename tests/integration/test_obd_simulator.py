"""
Integration tests for OBD Simulator components
Tests serial bridge, OBD worker, and ZeroMQ integration
"""
<<<<<<< HEAD
import pytest
import json
import time
import threading
import zmq
from unittest.mock import Mock, patch, MagicMock

# Import OBD components
import sys
import os
=======
import json
import os
import sys
import threading
import time

import pytest
import zmq
from unittest.mock import patch

# Import OBD components
>>>>>>> 5376269 (rebase)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rpi'))

from hardware.serial_bridge import SerialBridge
from services.obd_worker import MIAOBDWorker, DynamicCarState


class TestDynamicCarState:
    """Test the dynamic car state management"""
    
    def test_initial_state(self):
        """Test initial car state values"""
        state = DynamicCarState()
        assert state.get_rpm() == 800
        assert state.get_speed() == 0
        assert state.get_coolant_temp() == 85
    
    def test_update_from_telemetry(self):
        """Test updating state from telemetry data"""
        state = DynamicCarState()
        
        # Test RPM update (pot1: 0-1023 -> 0-4000 RPM)
        state.update_from_telemetry({"pot1": 512})
        assert 800 <= state.get_rpm() <= 4000
        
        # Test speed update (pot2: 0-1023 -> 0-120 km/h)
        state.update_from_telemetry({"pot2": 500})
        assert 0 <= state.get_speed() <= 120
    
    def test_thread_safety(self):
        """Test thread-safe state updates"""
        state = DynamicCarState()
        
        def update_loop():
            for i in range(100):
                state.update_from_telemetry({"pot1": i * 10, "pot2": i * 5})
                time.sleep(0.001)
        
        threads = [threading.Thread(target=update_loop) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # State should be valid after concurrent updates
        assert 800 <= state.get_rpm() <= 4000
        assert 0 <= state.get_speed() <= 120


class TestSerialBridge:
    """Test serial bridge component"""
    
    @patch('hardware.serial_bridge.serial')
    def test_serial_bridge_initialization(self, mock_serial):
        """Test serial bridge initialization"""
        bridge = SerialBridge(serial_port="/dev/ttyUSB0", baud_rate=115200)
        assert bridge.serial_port == "/dev/ttyUSB0"
        assert bridge.baud_rate == 115200
    
    def test_serial_bridge_mock_mode(self):
        """Test serial bridge in mock mode (no hardware)"""
        bridge = SerialBridge(serial_port=None)
        # Should not raise error
        assert bridge.serial_port is None
    
    @patch('hardware.serial_bridge.serial')
    def test_serial_bridge_publish_telemetry(self, mock_serial):
        """Test telemetry publishing to ZeroMQ"""
        bridge = SerialBridge(serial_port="/dev/ttyUSB0")
        bridge.context = zmq.Context()
        bridge.pub_socket = bridge.context.socket(zmq.PUB)
        
        # Bind to inproc for testing
        test_url = "inproc://test_pub"
        bridge.pub_socket.bind(test_url)
        
        # Create subscriber
        sub = bridge.context.socket(zmq.SUB)
        sub.connect(test_url)
        sub.subscribe("mcu/telemetry")
        
        # Publish test data
        test_data = {"pot1": 512, "pot2": 256}
        bridge._publish_telemetry(test_data)
        
        # Receive with timeout
        sub.setsockopt(zmq.RCVTIMEO, 1000)
        try:
            topic, message = sub.recv_multipart()
            data = json.loads(message.decode('utf-8'))
            assert topic.decode('utf-8') == "mcu/telemetry"
            assert data == test_data
        except zmq.Again:
            pytest.fail("Failed to receive published message")
        finally:
            bridge.pub_socket.close()
            sub.close()
            bridge.context.term()


class TestOBDWorker:
    """Test OBD worker component"""
    
    @patch('services.obd_worker.ELM327_AVAILABLE', False)
    def test_obd_worker_no_elm327(self):
        """Test OBD worker initialization without ELM327"""
        worker = MIAOBDWorker()
        assert not worker.start()  # Should fail without ELM327
    
    @patch('services.obd_worker.ELM327_AVAILABLE', True)
<<<<<<< HEAD
    @patch('services.obd_worker.elm327')
    def test_obd_worker_initialization(self, mock_elm327):
=======
    @patch('services.obd_worker.Elm')
    def test_obd_worker_initialization(self, mock_elm):
>>>>>>> 5376269 (rebase)
        """Test OBD worker initialization"""
        worker = MIAOBDWorker()
        assert worker.car_state is not None
        assert worker.broker_url == "tcp://localhost:5555"
        assert worker.telemetry_url == "tcp://localhost:5556"
    
    def test_obd_worker_car_state_integration(self):
        """Test OBD worker updates car state from telemetry"""
        worker = MIAOBDWorker()
        
        # Simulate telemetry update
        telemetry_data = {"pot1": 600, "pot2": 400}
        worker.car_state.update_from_telemetry(telemetry_data)
        
        assert worker.car_state.get_rpm() > 800
        assert worker.car_state.get_speed() > 0


class TestOBDIntegration:
    """Integration tests for OBD simulator components"""
    
    @pytest.fixture
    def zmq_context(self):
        """Create ZMQ context for testing"""
        ctx = zmq.Context()
        yield ctx
        ctx.term()
    
    def test_telemetry_flow(self, zmq_context):
        """Test complete telemetry flow: Serial Bridge -> OBD Worker"""
        # Create PUB socket (simulating serial bridge)
        pub = zmq_context.socket(zmq.PUB)
        pub.bind("inproc://test_telemetry")
        time.sleep(0.1)  # Allow binding
        
        # Create SUB socket (simulating OBD worker)
        sub = zmq_context.socket(zmq.SUB)
        sub.connect("inproc://test_telemetry")
        sub.subscribe("mcu/telemetry")
        time.sleep(0.1)  # Allow connection
        
        # Publish telemetry
        test_data = {"pot1": 512, "pot2": 256}
        pub.send_multipart([
            b"mcu/telemetry",
            json.dumps(test_data).encode('utf-8')
        ])
        
        # Receive telemetry
        sub.setsockopt(zmq.RCVTIMEO, 1000)
        try:
            topic, message = sub.recv_multipart()
            received_data = json.loads(message.decode('utf-8'))
            assert topic == b"mcu/telemetry"
            assert received_data == test_data
        except zmq.Again:
            pytest.fail("Failed to receive telemetry")
        finally:
            pub.close()
            sub.close()
    
    def test_car_state_pid_mapping(self):
        """Test that car state values map correctly to OBD PIDs"""
        state = DynamicCarState()
        
        # Set specific values
        state.update_from_telemetry({"pot1": 500})  # Should map to ~2000 RPM
        rpm = state.get_rpm()
        
        # Verify RPM is in expected range
        assert 800 <= rpm <= 4000
        
        # Test PID encoding (simplified)
        # PID 0x0C: RPM = (A*256 + B) / 4
        rpm_val = rpm * 4
        a = (rpm_val >> 8) & 0xFF
        b = rpm_val & 0xFF
        
        # Verify encoding is valid
        assert 0 <= a <= 255
        assert 0 <= b <= 255
        
        # Decode back
        decoded_rpm = (a * 256 + b) // 4
        assert abs(decoded_rpm - rpm) < 4  # Allow small rounding error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
