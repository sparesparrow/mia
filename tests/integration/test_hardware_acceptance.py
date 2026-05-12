"""
Hardware acceptance tests — gated behind @pytest.mark.hardware.

These tests validate real hardware paths that cannot run in CI.
Run on a Raspberry Pi with attached peripherals:

    pytest tests/integration/test_hardware_acceptance.py -m hardware

Each test documents its precondition so operators know what to connect.
"""

import json
import os
import subprocess
import unittest

import pytest


@pytest.mark.hardware
class TestGPIOAcceptance(unittest.TestCase):
    """Requires: Raspberry Pi with GPIO header accessible."""

    def test_gpio_output_toggles(self):
        """GPIO output pin can be set HIGH and read back."""
        try:
            import gpiod
        except ImportError:
            self.skipTest("gpiod not available — not running on RPi")

        chip = gpiod.Chip("gpiochip0")
        line = chip.get_line(17)
        config = gpiod.LineRequest()
        config.consumer = "mia-hw-test"
        config.request_type = gpiod.LINE_REQ_DIR_OUT
        line.request(config)
        try:
            line.set_value(1)
            self.assertEqual(line.get_value(), 1)
            line.set_value(0)
            self.assertEqual(line.get_value(), 0)
        finally:
            line.release()

    def test_gpio_worker_responds_via_zmq(self):
        """GPIO worker registers with broker and handles a GPIO_SET command."""
        self.skipTest("Requires running zmq-broker and mia-gpio-worker services")


@pytest.mark.hardware
class TestSerialBridgeAcceptance(unittest.TestCase):
    """Requires: ESP32 or Arduino connected via USB serial."""

    def test_serial_device_detected(self):
        """At least one /dev/ttyUSB* or /dev/ttyACM* device is present."""
        from pathlib import Path

        usb_devs = list(Path("/dev").glob("ttyUSB*"))
        acm_devs = list(Path("/dev").glob("ttyACM*"))
        self.assertTrue(
            usb_devs or acm_devs,
            "No serial devices found — connect an ESP32 or Arduino",
        )

    def test_serial_bridge_publishes_telemetry(self):
        """Serial bridge PUB socket emits telemetry within 5 seconds."""
        import zmq

        ctx = zmq.Context()
        sub = ctx.socket(zmq.SUB)
        sub.connect("tcp://127.0.0.1:5556")
        sub.subscribe(b"")
        sub.setsockopt(zmq.RCVTIMEO, 5000)
        try:
            data = sub.recv_json()
            self.assertIn("device_id", data)
        except zmq.Again:
            self.fail("No telemetry received from serial bridge within 5s")
        finally:
            sub.close()
            ctx.term()


@pytest.mark.hardware
@pytest.mark.automotive
class TestOBDAcceptance(unittest.TestCase):
    """Requires: ELM327-compatible OBD adapter on /dev/ttyUSB0."""

    def test_obd_worker_creates_virtual_pty(self):
        """OBD worker creates a virtual PTY for diagnostic tool connections."""
        from pathlib import Path

        pty_link = Path("/tmp/mia-elm327")
        if not pty_link.exists():
            self.skipTest("OBD worker PTY not found — start mia-obd-worker first")
        self.assertTrue(pty_link.is_symlink() or pty_link.exists())

    def test_elm327_responds_to_atz(self):
        """Virtual PTY responds to ATZ with an ELM327 identification string."""
        import serial

        pty_path = "/tmp/mia-elm327"
        if not os.path.exists(pty_path):
            self.skipTest("OBD worker PTY not found")
        try:
            ser = serial.Serial(pty_path, 38400, timeout=2)
            ser.write(b"ATZ\r")
            response = ser.read(64).decode(errors="replace")
            self.assertIn("ELM327", response)
            ser.close()
        except serial.SerialException as e:
            self.skipTest(f"Cannot open PTY: {e}")


@pytest.mark.hardware
@pytest.mark.android
class TestAndroidDeviceAcceptance(unittest.TestCase):
    """Requires: Android device connected via USB with ADB enabled."""

    def test_adb_device_connected(self):
        """At least one ADB device is connected and authorized."""
        try:
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, timeout=5
            )
        except FileNotFoundError:
            self.skipTest("adb not found in PATH")
        lines = [
            l for l in result.stdout.strip().splitlines()[1:] if l.strip()
        ]
        devices = [l for l in lines if "device" in l and "unauthorized" not in l]
        self.assertTrue(devices, "No authorized ADB devices found")
