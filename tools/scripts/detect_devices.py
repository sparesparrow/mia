#!/usr/bin/env python3
"""
Enhanced Device Detection Script for MIA Universal

This script:
1. Detects all connected ESP32, Android, and Raspberry Pi devices
2. Identifies device types by USB VID:PID and network discovery
3. Maps devices to PlatformIO environments, Conan profiles, and deployment targets
4. Generates device manifest JSON for multi-device deployment
"""

import serial.tools.list_ports
import logging
import json
import sys
import subprocess
from typing import List, Dict, Any, Optional
import asyncio
import re


logger = logging.getLogger(__name__)

# USB VID:PID mappings for common USB-serial chips
USB_CHIP_PATTERNS = {
    'CH340': ['1A86:7523', '1A86:5523'],  # CH340/CH341 USB-Serial
    'CP210x': ['10C4:EA60'],  # Silicon Labs CP2102/CP2104
    'FTDI': ['0403:6001', '0403:6015'],  # FTDI FT232/FT231X
    'CDC_ACM': []  # Native USB CDC ACM (ESP32-S3 USB OTG)
}

# Keywords to identify device types from descriptions
ESP32_S3_KEYWORDS = ['ESP32-S3', 'ESP32S3', 'USB JTAG', 'JTAG/serial debug']
ESP32_KEYWORDS = ['CH340', 'CH341', 'CP210', 'UART', 'USB-SERIAL']
RASPBERRY_PI_KEYWORDS = ['Raspberry Pi', 'RPi', 'BCM2711', 'ttyUSB']
ANDROID_KEYWORDS = ['Android', 'ADB', 'USB debugging']

def get_vid_pid(port) -> str:
    """Extract VID:PID from port hardware ID."""
    hwid = port.hwid
    if 'VID:PID=' in hwid.upper():
        # Format: USB VID:PID=1A86:7523
        parts = hwid.upper().split('VID:PID=')
        if len(parts) > 1:
            vid_pid = parts[1].split()[0]
            return vid_pid
    return ""

def identify_device_type(port) -> Dict[str, Any]:
    """Identify device type and configuration based on port information."""
    description = port.description.upper()
    vid_pid = get_vid_pid(port)

    # Check for ESP32-S3 (usually CDC ACM or JTAG)
    if any(keyword in description for keyword in ESP32_S3_KEYWORDS):
        if 'JTAG' in description:
            return {
                "port": port.device,
                "type": "esp32s3_jtag",
                "description": port.description,
                "vid_pid": vid_pid,
                "is_jtag": True,
                "platform": "esp32"
            }
        else:
            return {
                "port": port.device,
                "type": "esp32s3",
                "description": port.description,
                "pio_env": "esp32s3",
                "conan_profile": "esp32s3",
                "baud_rate": 115200,
                "vid_pid": vid_pid,
                "is_jtag": False,
                "platform": "esp32"
            }

    # Check for generic ESP32 (usually CH340 or CP210x)
    if any(keyword in description for keyword in ESP32_KEYWORDS) or vid_pid in (
        USB_CHIP_PATTERNS['CH340'] + USB_CHIP_PATTERNS['CP210x']
    ):
        return {
            "port": port.device,
            "type": "esp32",
            "description": port.description,
            "pio_env": "esp32dev-release",
            "conan_profile": "esp32",
            "baud_rate": 115200,
            "vid_pid": vid_pid,
            "is_jtag": False,
            "platform": "esp32"
        }

    # Check for Raspberry Pi (USB serial)
    if any(keyword in description for keyword in RASPBERRY_PI_KEYWORDS):
        return {
            "port": port.device,
            "type": "raspberry_pi",
            "description": port.description,
            "vid_pid": vid_pid,
            "is_jtag": False,
            "platform": "rpi"
        }

    # Unknown device
    return {
        "port": port.device,
        "type": "unknown",
        "description": port.description,
        "vid_pid": vid_pid,
        "is_jtag": False
    }

def detect_serial_devices() -> List[Dict[str, Any]]:
    """Detect all connected serial devices."""
    ports = serial.tools.list_ports.comports()
    devices = []

    for port in ports:
        device_info = identify_device_type(port)

        if device_info["type"] != "unknown":
            devices.append({
                "port": device_info["port"],
                "type": device_info["type"],
                "description": device_info["description"],
                "pio_env": device_info.get("pio_env", ""),
                "conan_profile": device_info.get("conan_profile", ""),
                "baud_rate": device_info.get("baud_rate", 115200),
                "platform": device_info.get("platform", "unknown"),
                "connection_type": "serial"
            })

    return devices


def build_summary(devices: List[Dict[str, Any]]) -> Dict[str, int]:
    """Build a platform summary for the detected device manifest."""
    return {
        "total_devices": len(devices),
        "esp32_devices": len([d for d in devices if d.get("platform") == "esp32"]),
        "android_devices": len([d for d in devices if d.get("platform") == "android"]),
        "rpi_devices": len([d for d in devices if d.get("platform") == "rpi"]),
    }


def get_local_subnet() -> Optional[str]:
    """Get the local subnet prefix used for Raspberry Pi discovery."""
    try:
        result = subprocess.run(
            ["ip", "route", "get", "8.8.8.8"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not determine local subnet: %s", exc)
        return None

    if result.returncode != 0:
        logger.warning("Could not determine local subnet: ip route returned %s", result.returncode)
        return None

    match = re.search(r'src\s+(\d+\.\d+\.\d+)\.\d+', result.stdout)
    if match:
        return match.group(1)

    logger.warning("Could not parse local subnet from ip route output")
    return None


def get_android_model(device_id: str) -> str:
    """Get an Android device model via adb, defaulting cleanly when unavailable."""
    try:
        model_proc = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("Could not read model for Android device %s: %s", device_id, exc)
        return "Unknown"

    if model_proc.returncode == 0:
        return model_proc.stdout.strip() or "Unknown"

    logger.debug("adb getprop failed for %s with exit code %s", device_id, model_proc.returncode)
    return "Unknown"

def detect_android_devices() -> List[Dict[str, Any]]:
    """Detect connected Android devices via ADB."""
    devices = []

    try:
        proc = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        lines = proc.stdout.strip().split("\n")
        for line in lines[1:]:  # Skip header
            if "device" in line and "unauthorized" not in line and "offline" not in line:
                parts = line.split()
                device_id = parts[0]

                model = get_android_model(device_id)

                devices.append({
                    "device_id": device_id,
                    "type": "android",
                    "model": model,
                    "description": f"Android device ({model})",
                    "platform": "android",
                    "connection_type": "adb"
                })

    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not detect Android devices: %s", exc)

    return devices

async def detect_raspberry_pi_devices() -> List[Dict[str, Any]]:
    """Detect Raspberry Pi devices on the network."""
    devices = []

    subnet = get_local_subnet()
    if subnet is None:
        return devices

    tasks = [check_raspberry_pi(f"{subnet}.{i}") for i in range(1, 255)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, dict):
            devices.append(result)
        elif isinstance(result, Exception):
            logger.debug("Raspberry Pi probe task failed: %s", result)

    return devices

async def check_raspberry_pi(ip: str) -> Optional[Dict[str, Any]]:
    """Check if IP address belongs to a Raspberry Pi."""
    try:
        # Try to connect to common RPi ports
        ports_to_check = [22, 80, 8080]  # SSH, HTTP, custom

        for port in ports_to_check:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=1.0
                )
                writer.close()
                await writer.wait_closed()

                # If we can connect, it's likely a RPi
                return {
                    "ip": ip,
                    "type": "raspberry_pi",
                    "description": f"Raspberry Pi at {ip}",
                    "platform": "rpi",
                    "connection_type": "network",
                    "ssh_port": 22 if port == 22 else None,
                    "http_port": port if port in [80, 8080] else None
                }

            except (asyncio.TimeoutError, ConnectionError, OSError):
                continue
            except Exception as exc:
                logger.debug("Unexpected Raspberry Pi probe error for %s:%s: %s", ip, port, exc)
                continue

    except Exception as exc:
        logger.debug("Unexpected Raspberry Pi host scan error for %s: %s", ip, exc)

    return None

def detect_all_devices() -> Dict[str, Any]:
    """Detect all connected devices and generate device manifest."""
    import asyncio

    # Detect serial devices (ESP32, RPi USB)
    serial_devices = detect_serial_devices()

    # Detect Android devices
    android_devices = detect_android_devices()

    # Detect network Raspberry Pi devices
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        rpi_devices = loop.run_until_complete(detect_raspberry_pi_devices())
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    # Combine all devices
    all_devices = serial_devices + android_devices + rpi_devices

    manifest = {
        "devices": all_devices,
        "summary": build_summary(all_devices)
    }

    return manifest

def print_manifest(manifest: Dict[str, Any]):
    """Print device manifest in human-readable format."""
    print("\n" + "="*70)
    print("MIA Universal - Device Detection")
    print("="*70)

    devices = manifest.get("devices", [])
    summary = manifest.get("summary", {})

    print(f"\n📊 Summary:")
    print(f"   Total devices: {summary.get('total_devices', 0)}")
    print(f"   ESP32 devices: {summary.get('esp32_devices', 0)}")
    print(f"   Android devices: {summary.get('android_devices', 0)}")
    print(f"   Raspberry Pi devices: {summary.get('rpi_devices', 0)}")

    if devices:
        print(f"\n📱 Found {len(devices)} device(s):")

        for i, device in enumerate(devices, 1):
            print(f"\n  {i}. {device['type'].upper()}")
            print(f"     Platform: {device.get('platform', 'unknown').upper()}")

            if device.get("connection_type") == "serial":
                print(f"     Port: {device['port']}")
                if device.get("pio_env"):
                    print(f"     PIO Environment: {device['pio_env']}")
                if device.get("conan_profile"):
                    print(f"     Conan Profile: {device['conan_profile']}")
                if device.get("baud_rate"):
                    print(f"     Baud Rate: {device['baud_rate']}")

            elif device.get("connection_type") == "adb":
                print(f"     Device ID: {device['device_id']}")
                print(f"     Model: {device.get('model', 'Unknown')}")

            elif device.get("connection_type") == "network":
                print(f"     IP Address: {device['ip']}")
                if device.get("ssh_port"):
                    print(f"     SSH Port: {device['ssh_port']}")
                if device.get("http_port"):
                    print(f"     HTTP Port: {device['http_port']}")

            print(f"     Description: {device['description']}")
    else:
        print("\n❌ No devices detected")

    print("\n" + "="*70)

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect connected devices for MIA Universal deployment"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output only JSON (no human-readable format)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Write JSON output to file"
    )
    parser.add_argument(
        "--filter-platform",
        nargs="+",
        choices=["esp32", "android", "rpi"],
        help="Filter devices by platform (esp32 android rpi)"
    )

    args = parser.parse_args()

    # Detect devices
    manifest = detect_all_devices()

    # Apply platform filter if specified
    if args.filter_platform:
        manifest["devices"] = [
            d for d in manifest["devices"]
            if d.get("platform") in args.filter_platform
        ]
        manifest["summary"] = build_summary(manifest["devices"])

    # Print human-readable output (unless --json is specified)
    if not args.json:
        print_manifest(manifest)

    # Print or save JSON output
    json_output = json.dumps(manifest, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        if not args.json:
            print(f"\n✅ Device manifest saved to: {args.output}")
    else:
        if args.json:
            print(json_output)
        else:
            print("\nJSON Output:")
            print(json_output)

    # Exit with status
    if not manifest.get("devices"):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()