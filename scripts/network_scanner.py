#!/usr/bin/env python3
"""
Network Scanner for MIA Universal
Scans local network to find ESP32, Android, and Raspberry Pi devices
"""

import asyncio
import json
import logging
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import aiohttp
except ImportError:
    aiohttp = None


logger = logging.getLogger(__name__)


@dataclass
class MIAScanResult:
    esp32_devices: List[Dict[str, Any]] = field(default_factory=list)
    android_devices: List[Dict[str, Any]] = field(default_factory=list)
    rpi_devices: List[Dict[str, Any]] = field(default_factory=list)
    scan_duration: float = 0.0
    devices_scanned: int = 0

    def total_devices(self) -> int:
        return len(self.esp32_devices) + len(self.android_devices) + len(self.rpi_devices)

    def is_success(self) -> bool:
        return self.total_devices() > 0


class MIANetworkScanner:
    """Scan local network for MIA Universal devices"""

    # MIA-specific API endpoints
    MIA_ENDPOINTS = [
        "/api/v1/system/health",
        "/api/v1/system/info",
        "/api/v1/bpm/current",
        "/",  # Basic web interface
    ]

    # Common ports for MIA devices
    ESP32_PORTS = [80, 8080, 5000]  # HTTP servers
    RPI_PORTS = [22, 80, 8080, 5555, 5556]  # SSH, HTTP, ZeroMQ
    ANDROID_PORTS = [5555]  # ADB

    def __init__(self, timeout: float = 0.5):
        self.timeout = timeout

    @staticmethod
    def _parse_json_payload(payload: str, source: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON payload and log malformed responses at debug level."""
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.debug("Invalid JSON from %s: %s", source, exc)
            return None

        if isinstance(parsed, dict):
            return parsed

        logger.debug("Ignoring non-object JSON payload from %s", source)
        return None

    def get_local_subnet(self) -> Optional[str]:
        """Get local subnet from network interfaces"""
        try:
            # Get default gateway IP using ip route
            result = subprocess.run(
                ["ip", "route", "get", "8.8.8.8"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Parse: "8.8.8.8 via 192.168.1.1 dev wlan0 src 192.168.1.100"
                import re
                match = re.search(r'src\s+(\d+\.\d+\.\d+)\.\d+', result.stdout)
                if match:
                    return match.group(1)
        except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
            logger.debug("Falling back to default subnet detection: %s", exc)

        # Fallback: common subnets
        return "192.168.1"

    async def scan_for_mia_devices(self, subnet: str = None) -> MIAScanResult:
        """Scan subnet for MIA devices"""
        result = MIAScanResult()
        start_time = asyncio.get_event_loop().time()

        if subnet is None:
            subnet = self.get_local_subnet()

        if subnet is None:
            return result

        if aiohttp is None:
            # Fallback to sync scanning
            return self._scan_sync(subnet)

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            # Scan IPs in parallel batches
            tasks = []
            for i in range(1, 255):
                ip = f"{subnet}.{i}"
                tasks.append(self._test_ip_for_mia_devices(session, ip))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for ip_result in results:
                if isinstance(ip_result, dict):
                    device_type = ip_result.get("type")
                    if device_type == "esp32":
                        result.esp32_devices.append(ip_result)
                    elif device_type == "rpi":
                        result.rpi_devices.append(ip_result)
                    elif device_type == "android":
                        result.android_devices.append(ip_result)
                result.devices_scanned += 1

        result.scan_duration = asyncio.get_event_loop().time() - start_time
        return result

    async def _test_ip_for_mia_devices(self, session, ip: str) -> Optional[Dict]:
        """Test if an IP responds to MIA device endpoints"""
        # Test ESP32 HTTP endpoints
        for port in self.ESP32_PORTS:
            try:
                # Test health endpoint
                async with session.get(
                    f"http://{ip}:{port}/api/v1/system/health"
                ) as resp:
                    if resp.status == 200:
                        payload = await resp.text()
                        data = self._parse_json_payload(payload, f"http://{ip}:{port}/api/v1/system/health")
                        # Verify it's an ESP32 by checking response structure
                        if data and any(key in data for key in ["status", "uptime", "heap", "free_heap"]):
                            return {
                                "type": "esp32",
                                "ip": ip,
                                "port": port,
                                "endpoints": [f"http://{ip}:{port}/api/v1/system/health"],
                                "device_info": data
                            }

                # Test basic web interface
                async with session.get(f"http://{ip}:{port}/") as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if "MIA" in text.upper() or "ESP32" in text.upper():
                            return {
                                "type": "esp32",
                                "ip": ip,
                                "port": port,
                                "endpoints": [f"http://{ip}:{port}/"],
                                "web_interface": True
                            }

            except (asyncio.TimeoutError, OSError) as exc:
                logger.debug("ESP32 probe failed for %s:%s: %s", ip, port, exc)
                continue
            except Exception as exc:
                logger.debug("Unexpected ESP32 probe error for %s:%s: %s", ip, port, exc)
                continue

        # Test Raspberry Pi SSH and HTTP
        for port in self.RPI_PORTS:
            if port in [22]:  # SSH
                # Test SSH connection
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=self.timeout
                    )
                    # Send SSH version string check
                    writer.write(b"SSH-2.0-MIA-Scanner\r\n")
                    await writer.drain()

                    response = await asyncio.wait_for(
                        reader.read(100), timeout=self.timeout
                    )

                    writer.close()
                    await writer.wait_closed()

                    if response.startswith(b"SSH-"):
                        return {
                            "type": "rpi",
                            "ip": ip,
                            "port": port,
                            "service": "ssh",
                            "connection_type": "ssh"
                        }
                except (asyncio.TimeoutError, OSError) as exc:
                    logger.debug("SSH probe failed for %s:%s: %s", ip, port, exc)
                except Exception as exc:
                    logger.debug("Unexpected SSH probe error for %s:%s: %s", ip, port, exc)

            elif port in [80, 8080]:  # HTTP
                try:
                    async with session.get(f"http://{ip}:{port}/") as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            if any(keyword in text.upper() for keyword in ["RASPBERRY", "RPI", "MIA", "ZEROMQ"]):
                                return {
                                    "type": "rpi",
                                    "ip": ip,
                                    "port": port,
                                    "service": "http",
                                    "connection_type": "http",
                                    "web_interface": True
                                }
                except (asyncio.TimeoutError, OSError) as exc:
                    logger.debug("RPi HTTP probe failed for %s:%s: %s", ip, port, exc)
                except Exception as exc:
                    logger.debug("Unexpected RPi HTTP probe error for %s:%s: %s", ip, port, exc)

        return None

    def _scan_sync(self, subnet: str) -> MIAScanResult:
        """Synchronous fallback scanning"""
        import urllib.request
        import urllib.error

        result = MIAScanResult()

        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            result.devices_scanned += 1

            # Test ESP32 devices
            for port in self.ESP32_PORTS:
                try:
                    url = f"http://{ip}:{port}/api/v1/system/health"
                    req = urllib.request.Request(url, method='GET')
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        if resp.status == 200:
                            payload = resp.read().decode()
                            data = self._parse_json_payload(payload, url)
                            if data and any(key in data for key in ["status", "uptime", "heap"]):
                                result.esp32_devices.append({
                                    "type": "esp32",
                                    "ip": ip,
                                    "port": port,
                                    "endpoints": [url],
                                    "device_info": data
                                })
                                break
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    logger.debug("Sync probe failed for %s:%s: %s", ip, port, exc)
                    continue
                except Exception as exc:
                    logger.debug("Unexpected sync probe error for %s:%s: %s", ip, port, exc)
                    continue

        return result

    def scan_known_ip(self, ip: str) -> MIAScanResult:
        """Test a known IP address directly"""
        result = MIAScanResult()
        result.devices_scanned = 1

        # Test ESP32 endpoints
        for port in self.ESP32_PORTS:
            try:
                import urllib.request
                url = f"http://{ip}:{port}/api/v1/system/health"
                req = urllib.request.Request(url, method='GET')
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        payload = resp.read().decode()
                        data = self._parse_json_payload(payload, url)
                        if data is None:
                            continue

                        result.esp32_devices.append({
                            "type": "esp32",
                            "ip": ip,
                            "port": port,
                            "endpoints": [url],
                            "device_info": data
                        })
                        break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                logger.debug("Known IP probe failed for %s:%s: %s", ip, port, exc)
                continue
            except Exception as exc:
                logger.debug("Unexpected known IP probe error for %s:%s: %s", ip, port, exc)
                continue

        return result


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="MIA Universal Network Scanner")
    parser.add_argument("-s", "--subnet", help="Subnet to scan (e.g., 192.168.1)")
    parser.add_argument("-i", "--ip", help="Test specific IP address")
    parser.add_argument("-t", "--timeout", type=float, default=0.5, help="Timeout per host")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    scanner = MIANetworkScanner(timeout=args.timeout)

    if args.ip:
        print(f"Testing specific IP: {args.ip}")
        result = scanner.scan_known_ip(args.ip)
    else:
        subnet = args.subnet or scanner.get_local_subnet()
        print(f"Scanning subnet: {subnet}.0/24...")
        result = await scanner.scan_for_mia_devices(subnet)

    print()
    print("=" * 70)
    print("MIA Universal Network Scan Results")
    print("=" * 70)
    print(f"ESP32 Devices:     {len(result.esp32_devices)}")
    print(f"Android Devices:   {len(result.android_devices)}")
    print(f"RPi Devices:       {len(result.rpi_devices)}")
    print(f"Total Devices:     {result.total_devices()}")
    print(f"IPs Scanned:       {result.devices_scanned}")
    print(f"Duration:          {result.scan_duration:.1f}s")
    print()

    if result.esp32_devices:
        print("ESP32 Devices Found:")
        for i, device in enumerate(result.esp32_devices, 1):
            print(f"  {i}. {device['ip']}:{device['port']}")
            if 'device_info' in device:
                info = device['device_info']
                print(f"     Status: {info.get('status', 'Unknown')}")
                print(f"     Uptime: {info.get('uptime', 'Unknown')}")
                print(f"     Free Heap: {info.get('free_heap', 'Unknown')}")
        print()

    if result.rpi_devices:
        print("Raspberry Pi Devices Found:")
        for i, device in enumerate(result.rpi_devices, 1):
            print(f"  {i}. {device['ip']}:{device['port']} ({device.get('service', 'unknown')})")
        print()

    if result.android_devices:
        print("Android Devices Found:")
        for i, device in enumerate(result.android_devices, 1):
            print(f"  {i}. {device['ip']}:{device['port']}")
        print()

    if result.is_success():
        print(f"SUCCESS: Found {result.total_devices()} MIA device(s)")
        return 0
    else:
        print("No MIA devices found on the network")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))