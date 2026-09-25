#!/usr/bin/env python3
"""
ESP32 Serial Monitor for MIA Universal
Monitors serial output and extracts connection status, sensor data, and system health
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Please install pyserial: pip install pyserial")
    raise


@dataclass
class MIAMonitorResult:
    wifi_connected: bool = False
    esp32_ip: Optional[str] = None
    server_started: bool = False
    zeromq_broker_started: bool = False
    audio_active: bool = False
    sensors_active: List[str] = field(default_factory=list)
    bpm_values: List[float] = field(default_factory=list)
    sensor_readings: dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    raw_log: str = ""
    duration: float = 0.0

    def is_success(self) -> bool:
        return self.wifi_connected and self.esp32_ip is not None and self.server_started


class MIASerialMonitor:
    """Monitor ESP32 serial output for MIA Universal status"""

    # Patterns to detect in serial output
    WIFI_CONNECTED_PATTERNS = [
        r"WiFi connected",
        r"WiFi connected successfully",
        r"Connected to WiFi",
        r"Wi-Fi connected",
    ]

    IP_ADDRESS_PATTERN = r"IP address:\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    HTTP_SERVER_PATTERN = r"HTTP server started.*?:(\d+)"
    ZEROMQ_BROKER_PATTERN = r"ZeroMQ broker.*?(?:started|running).*?(\d+)"
    AUDIO_ACTIVE_PATTERN = r"Audio.*?(?:active|started|recording)"
    SENSOR_ACTIVE_PATTERN = r"Sensor\s+(\w+).*?(?:active|detected|initialized)"

    BPM_PATTERN = r"BPM[:\s]+(\d+\.?\d*)"
    TEMPERATURE_PATTERN = r"Temperature[:\s]+(\d+\.?\d*)°?C"
    HUMIDITY_PATTERN = r"Humidity[:\s]+(\d+\.?\d*)%"
    PRESSURE_PATTERN = r"Pressure[:\s]+(\d+\.?\d*).*(?:hPa|Pa)"
    LIGHT_PATTERN = r"Light[:\s]+(\d+\.?\d*).*(?:lux|%)"

    ERROR_PATTERNS = [
        r"Error",
        r"FAILED",
        r"Exception",
        r"Guru Meditation",
        r"Backtrace:",
        r"assert failed",
        r"ESP_ERROR",
    ]

    def __init__(self, port: str = "/dev/ttyACM0", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate

    @staticmethod
    def find_esp32_port() -> Optional[str]:
        """Auto-detect ESP32 serial port"""
        esp32_vids = [0x303A, 0x10C4, 0x1A86]  # Common ESP32 USB VIDs

        for port in serial.tools.list_ports.comports():
            if port.vid in esp32_vids:
                return port.device

            # Also check for ACM ports on Linux
            if "ttyACM" in port.device or "ttyUSB" in port.device:
                return port.device

        return None

    def monitor_sync(self, duration: int = 30) -> MIAMonitorResult:
        """Synchronous version of monitor (for non-async contexts)"""
        result = MIAMonitorResult()
        start_time = time.time()

        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=1)
            ser.reset_input_buffer()

            while (time.time() - start_time) < duration:
                if ser.in_waiting:
                    try:
                        line = ser.readline().decode('utf-8', errors='replace')
                        result.raw_log += line
                        self._parse_line(line, result)

                        # Early exit if all criteria met
                        if result.is_success():
                            break

                    except Exception as e:
                        result.errors.append(f"Read error: {e}")

                time.sleep(0.05)

            ser.close()

        except serial.SerialException as e:
            result.errors.append(f"Serial error: {e}")

        result.duration = time.time() - start_time
        return result

    async def monitor(self, duration: int = 30) -> MIAMonitorResult:
        """Monitor serial port for specified duration (async version)"""
        result = MIAMonitorResult()
        start_time = asyncio.get_event_loop().time()

        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            ser.reset_input_buffer()

            while (asyncio.get_event_loop().time() - start_time) < duration:
                if ser.in_waiting:
                    try:
                        line = ser.readline().decode('utf-8', errors='replace')
                        result.raw_log += line
                        self._parse_line(line, result)

                        # Early exit if all criteria met
                        if result.is_success():
                            break

                    except Exception as e:
                        result.errors.append(f"Read error: {e}")

                await asyncio.sleep(0.05)

            ser.close()

        except serial.SerialException as e:
            result.errors.append(f"Serial error: {e}")

        result.duration = asyncio.get_event_loop().time() - start_time
        return result

    def _parse_line(self, line: str, result: MIAMonitorResult):
        """Parse a single line of serial output"""
        # Check for WiFi connection
        for pattern in self.WIFI_CONNECTED_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                result.wifi_connected = True
                break

        # Extract IP address
        ip_match = re.search(self.IP_ADDRESS_PATTERN, line)
        if ip_match:
            result.esp32_ip = ip_match.group(1)

        # Check for HTTP server start
        server_match = re.search(self.HTTP_SERVER_PATTERN, line, re.IGNORECASE)
        if server_match:
            result.server_started = True

        # Check for ZeroMQ broker
        zmq_match = re.search(self.ZEROMQ_BROKER_PATTERN, line, re.IGNORECASE)
        if zmq_match:
            result.zeromq_broker_started = True

        # Check for audio activity
        if re.search(self.AUDIO_ACTIVE_PATTERN, line, re.IGNORECASE):
            result.audio_active = True

        # Check for sensor activity
        sensor_match = re.search(self.SENSOR_ACTIVE_PATTERN, line, re.IGNORECASE)
        if sensor_match:
            sensor_name = sensor_match.group(1)
            if sensor_name not in result.sensors_active:
                result.sensors_active.append(sensor_name)

        # Extract BPM values
        bpm_match = re.search(self.BPM_PATTERN, line)
        if bpm_match:
            bpm = float(bpm_match.group(1))
            if 40 <= bpm <= 200:  # Valid BPM range
                result.bpm_values.append(bpm)

        # Extract sensor readings
        temp_match = re.search(self.TEMPERATURE_PATTERN, line)
        if temp_match:
            result.sensor_readings['temperature'] = float(temp_match.group(1))

        humid_match = re.search(self.HUMIDITY_PATTERN, line)
        if humid_match:
            result.sensor_readings['humidity'] = float(humid_match.group(1))

        press_match = re.search(self.PRESSURE_PATTERN, line)
        if press_match:
            result.sensor_readings['pressure'] = float(press_match.group(1))

        light_match = re.search(self.LIGHT_PATTERN, line)
        if light_match:
            result.sensor_readings['light'] = float(light_match.group(1))

        # Check for errors
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                result.errors.append(line.strip())
                break


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="MIA Universal ESP32 Serial Monitor")
    parser.add_argument("-p", "--port", help="Serial port", default=None)
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("-d", "--duration", type=int, default=30, help="Monitor duration (seconds)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    port = args.port
    if not port:
        port = MIASerialMonitor.find_esp32_port()
        if not port:
            print("ERROR: No ESP32 device found")
            return 1

    print(f"Monitoring MIA ESP32 on {port} at {args.baud} baud for {args.duration}s...")

    monitor = MIASerialMonitor(port, args.baud)
    result = await monitor.monitor(args.duration)

    print()
    print("=" * 70)
    print("MIA Universal ESP32 Monitor Results")
    print("=" * 70)
    print(f"WiFi Connected:      {'Yes' if result.wifi_connected else 'No'}")
    print(f"ESP32 IP:           {result.esp32_ip or 'Not found'}")
    print(f"HTTP Server:        {'Running' if result.server_started else 'Not started'}")
    print(f"ZeroMQ Broker:      {'Running' if result.zeromq_broker_started else 'Not started'}")
    print(f"Audio Active:       {'Yes' if result.audio_active else 'No'}")
    print(f"Active Sensors:     {len(result.sensors_active)} ({', '.join(result.sensors_active) if result.sensors_active else 'None'})")
    print(f"BPM Values:         {len(result.bpm_values)} samples")
    print(f"Sensor Readings:    {len(result.sensor_readings)} types")
    print(f"Errors:             {len(result.errors)}")
    print(f"Duration:           {result.duration:.1f}s")
    print()

    if result.sensor_readings:
        print("Current Sensor Readings:")
        for sensor, value in result.sensor_readings.items():
            print(f"  {sensor.capitalize()}: {value}")
        print()

    if result.bpm_values:
        latest_bpm = result.bpm_values[-1] if result.bpm_values else None
        print(f"Latest BPM: {latest_bpm}")
        print(f"BPM Range: {min(result.bpm_values):.1f} - {max(result.bpm_values):.1f}")
        print()

    if result.errors:
        print("Errors detected:")
        for err in result.errors[:5]:  # Show first 5 errors
            print(f"  - {err[:80]}")
        print()

    if result.is_success():
        print("✅ SUCCESS: MIA ESP32 is operational and connected")
        return 0
    else:
        print("❌ ISSUES: ESP32 not fully operational")
        if not result.wifi_connected:
            print("  - WiFi connection failed")
        if not result.esp32_ip:
            print("  - No IP address assigned")
        if not result.server_started:
            print("  - HTTP server not started")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))