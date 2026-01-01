#!/usr/bin/env python3
"""
Multi-Platform Deployment Script for MIA Universal

This script:
1. Detects all connected devices (ESP32, Android, Raspberry Pi)
2. Builds firmware/services for each platform using appropriate tools
3. Deploys to all devices sequentially or in parallel
4. Monitors deployment status and provides detailed logs
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from typing import Dict, List

# Import device detection
sys.path.insert(0, str(Path(__file__).parent))
from detect_devices import detect_all_devices

def build_for_platform(platform: str, project_dir: Path) -> bool:
    """Build software for specified platform."""
    print(f"\n{'='*60}")
    print(f"Building for platform: {platform}")
    print(f"{'='*60}")

    if platform == "esp32":
        return build_esp32_firmware(project_dir)
    elif platform == "android":
        return build_android_app(project_dir)
    elif platform == "rpi":
        return build_rpi_services(project_dir)
    else:
        print(f"❌ Unknown platform: {platform}")
        return False

def build_esp32_firmware(project_dir: Path) -> bool:
    """Build ESP32 firmware using ESP-IDF or PlatformIO."""
    esp32_dir = project_dir / "esp32"

    if not esp32_dir.exists():
        print("⚠️  ESP32 directory not found, skipping ESP32 build")
        return True

    # Check if firmware binaries already exist
    firmware_dir = esp32_dir / ".pio" / "build" / "esp32s3"
    if firmware_dir.exists() and (firmware_dir / "firmware.bin").exists():
        print("✅ ESP32 firmware binaries already exist, skipping build")
        return True

    # Try PlatformIO first
    if (esp32_dir / "platformio.ini").exists():
        print("Building ESP32 firmware with PlatformIO...")
        result = subprocess.run(
            ["pio", "run", "--environment", "esp32dev"],
            cwd=esp32_dir
        )
        return result.returncode == 0

    # Try ESP-IDF
    elif (esp32_dir / "CMakeLists.txt").exists():
        print("Building ESP32 firmware with ESP-IDF...")
        result = subprocess.run(
            ["idf.py", "build"],
            cwd=esp32_dir
        )
        return result.returncode == 0

    else:
        print("❌ No ESP32 build system found (PlatformIO or ESP-IDF)")
        return False

def build_android_app(project_dir: Path) -> bool:
    """Build Android app using Gradle."""
    android_dir = project_dir / "android"

    if not android_dir.exists():
        print("⚠️  Android directory not found, skipping Android build")
        return True

    print("Building Android app with Gradle...")
    result = subprocess.run(
        ["./gradlew", "assembleDebug"],
        cwd=android_dir
    )
    return result.returncode == 0

def build_rpi_services(project_dir: Path) -> bool:
    """Build Raspberry Pi services."""
    rpi_dir = project_dir / "rpi"

    if not rpi_dir.exists():
        print("⚠️  RPi directory not found, skipping RPi build")
        return True

    print("Building RPi services...")

    # Install Python dependencies if requirements.txt exists
    req_file = rpi_dir / "requirements.txt"
    if req_file.exists():
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            cwd=rpi_dir
        )
        if result.returncode != 0:
            return False

    # Build any C++ components if CMakeLists.txt exists
    cmake_file = rpi_dir / "CMakeLists.txt"
    if cmake_file.exists():
        build_dir = rpi_dir / "build"
        build_dir.mkdir(exist_ok=True)

        # Configure and build
        result = subprocess.run(
            ["cmake", "-S", str(rpi_dir), "-B", str(build_dir)],
            cwd=rpi_dir
        )
        if result.returncode != 0:
            return False

        result = subprocess.run(
            ["cmake", "--build", str(build_dir), "--config", "Release"],
            cwd=build_dir
        )
        if result.returncode != 0:
            return False

    return True

def upload_to_device(device_info: Dict, project_dir: Path) -> bool:
    """Upload software to a specific device."""
    print(f"\n{'='*60}")
    print(f"Uploading to {device_info['type']} ({device_info.get('platform', 'unknown')})")
    print(f"{'='*60}")

    platform = device_info.get("platform")

    if platform == "esp32":
        return upload_esp32_firmware(device_info, project_dir)
    elif platform == "android":
        return upload_android_app(device_info, project_dir)
    elif platform == "rpi":
        return upload_rpi_services(device_info, project_dir)
    else:
        print(f"❌ Unknown platform: {platform}")
        return False

def upload_esp32_firmware(device_info: Dict, project_dir: Path) -> bool:
    """Upload ESP32 firmware."""
    esp32_dir = project_dir / "esp32"
    port = device_info["port"]
    device_type = device_info.get("type", "")

    # Check for pre-built firmware
    firmware_dir = esp32_dir / ".pio" / "build" / "esp32s3"
    firmware_bin = firmware_dir / "firmware.bin"

    if firmware_bin.exists():
        print(f"Uploading pre-built ESP32 firmware to {port}...")
        # Use esptool.py directly for upload
        bootloader = firmware_dir / "bootloader.bin"
        partitions = firmware_dir / "partitions.bin"

        if bootloader.exists() and partitions.exists():
            result = subprocess.run([
                "esptool.py",
                "--chip", "esp32s3" if "s3" in device_type else "esp32",
                "--port", port,
                "--baud", "921600",
                "--before", "default_reset",
                "--after", "hard_reset",
                "write_flash",
                "-z",
                "--flash_mode", "dio",
                "--flash_freq", "80m",
                "--flash_size", "detect",
                "0x0000", str(bootloader),
                "0x8000", str(partitions),
                "0x10000", str(firmware_bin)
            ])
            return result.returncode == 0
        else:
            print("❌ Required firmware files not found")
            return False

    # Try PlatformIO
    if (esp32_dir / "platformio.ini").exists():
        env_name = "esp32dev"  # Use the environment from platformio.ini
        print(f"Uploading ESP32 firmware to {port} with PlatformIO ({env_name})...")
        result = subprocess.run(
            ["pio", "run", "--environment", env_name, "--target", "upload", "--upload-port", port],
            cwd=esp32_dir
        )
        return result.returncode == 0

    # Try ESP-IDF
    elif (esp32_dir / "CMakeLists.txt").exists():
        print(f"Uploading ESP32 firmware to {port} with ESP-IDF...")
        result = subprocess.run(
            ["idf.py", "-p", port, "flash"],
            cwd=esp32_dir
        )
        return result.returncode == 0

    else:
        print("❌ No ESP32 upload method available")
        return False

def upload_android_app(device_info: Dict, project_dir: Path) -> bool:
    """Upload Android app via ADB."""
    android_dir = project_dir / "android"
    device_id = device_info["device_id"]

    apk_path = android_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"

    if not apk_path.exists():
        print(f"❌ APK not found at {apk_path}")
        return False

    print(f"Installing Android app to {device_id}...")
    result = subprocess.run([
        "adb", "-s", device_id, "install", "-r", str(apk_path)
    ])

    return result.returncode == 0

def upload_rpi_services(device_info: Dict, project_dir: Path) -> bool:
    """Upload Raspberry Pi services via SSH."""
    ip = device_info["ip"]
    rpi_dir = project_dir / "rpi"

    print(f"Uploading RPi services to {ip}...")

    try:
        # Create deployment script
        deploy_script = f"""
#!/bin/bash
set -e

echo "Deploying MIA services to Raspberry Pi..."

# Create MIA directory
sudo mkdir -p /opt/mia
sudo chown -R $USER:$USER /opt/mia

# Copy services
cp -r /tmp/mia_services/* /opt/mia/

# Install systemd services
sudo cp /opt/mia/services/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start services
for service in /opt/mia/services/*.service; do
    service_name=$(basename "$service")
    sudo systemctl enable "$service_name"
    sudo systemctl restart "$service_name"
done

echo "MIA services deployed successfully"
"""

        # Write deploy script to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(deploy_script)
            deploy_script_path = f.name

        # Copy files to RPi
        result = subprocess.run([
            "scp", "-r", str(rpi_dir), f"mia@{ip}:/tmp/mia_services"
        ])

        if result.returncode != 0:
            return False

        # Execute deployment script
        result = subprocess.run([
            "ssh", f"mia@{ip}", "bash", "-s"
        ], input=deploy_script, text=True)

        # Cleanup
        os.unlink(deploy_script_path)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ RPi deployment failed: {e}")
        return False

def monitor_device(device_info: Dict, duration: int = 10):
    """Monitor device output after deployment."""
    print(f"\n{'='*60}")
    print(f"Monitoring {device_info['type']} for {duration}s")
    print(f"{'='*60}")

    platform = device_info.get("platform")

    if platform == "esp32":
        monitor_esp32_device(device_info, duration)
    elif platform == "android":
        monitor_android_device(device_info, duration)
    elif platform == "rpi":
        monitor_rpi_device(device_info, duration)

def monitor_esp32_device(device_info: Dict, duration: int):
    """Monitor ESP32 serial output."""
    port = device_info["port"]

    try:
        result = subprocess.run([
            "pio", "device", "monitor",
            "--port", port,
            "--baud", "115200",
            "--filter", "default"
        ], timeout=duration)
    except subprocess.TimeoutExpired:
        pass  # Expected

def monitor_android_device(device_info: Dict, duration: int):
    """Monitor Android device logs."""
    device_id = device_info["device_id"]

    try:
        result = subprocess.run([
            "adb", "-s", device_id, "logcat", "-v", "time", "-d"
        ], timeout=duration)
    except subprocess.TimeoutExpired:
        pass

def monitor_rpi_device(device_info: Dict, duration: int):
    """Monitor Raspberry Pi service logs."""
    ip = device_info["ip"]

    try:
        result = subprocess.run([
            "ssh", f"mia@{ip}", "journalctl", "-f", "-n", "50"
        ], timeout=duration)
    except subprocess.TimeoutExpired:
        pass

def deploy_sequential(devices: List[Dict], project_dir: Path, args) -> List[bool]:
    """Deploy to all devices sequentially."""
    print(f"\n🚀 Starting SEQUENTIAL deployment to {len(devices)} device(s)")

    # Build for each unique platform
    unique_platforms = list(set(d["platform"] for d in devices if "platform" in d))
    build_results = {}

    for platform in unique_platforms:
        build_results[platform] = build_for_platform(platform, project_dir)

    # Upload to each device
    upload_results = []
    for device in devices:
        platform = device.get("platform")
        if not platform or not build_results.get(platform, False):
            print(f"⏭️  Skipping {device.get('port', device.get('device_id', 'unknown'))} - build failed")
            upload_results.append(False)
            continue

        success = upload_to_device(device, project_dir)
        upload_results.append(success)

        if success and args.monitor:
            monitor_device(device, duration=args.monitor_duration)

    return upload_results

def deploy_parallel(devices: List[Dict], project_dir: Path, args) -> List[bool]:
    """Deploy to all devices in parallel."""
    print(f"\n🚀 Starting PARALLEL deployment to {len(devices)} device(s)")

    # Build for each unique platform (still sequential - shared resources)
    unique_platforms = list(set(d["platform"] for d in devices if "platform" in d))
    build_results = {}

    for platform in unique_platforms:
        build_results[platform] = build_for_platform(platform, project_dir)

    # Upload to devices in parallel
    upload_results = []
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = []
        for device in devices:
            platform = device.get("platform")
            if not platform or not build_results.get(platform, False):
                print(f"⏭️  Skipping {device.get('port', device.get('device_id', 'unknown'))} - build failed")
                upload_results.append(False)
                continue

            future = executor.submit(upload_to_device, device, project_dir)
            futures.append((future, device))

        for future, device in futures:
            success = future.result()
            upload_results.append(success)

    return upload_results

def main():
    """Main deployment orchestration."""
    parser = argparse.ArgumentParser(
        description="Deploy MIA Universal to multiple devices"
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "parallel"],
        default="sequential",
        help="Deployment mode (default: sequential)"
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor device output after upload"
    )
    parser.add_argument(
        "--monitor-duration",
        type=int,
        default=10,
        help="Duration to monitor each device in seconds (default: 10)"
    )
    parser.add_argument(
        "--filter-platform",
        nargs="+",
        choices=["esp32", "android", "rpi"],
        help="Filter devices by platform (esp32 android rpi)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without actually deploying"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Automatically confirm deployment without prompting"
    )

    args = parser.parse_args()

    # Get project directory
    project_dir = Path(__file__).parent.parent

    print("MIA Universal - Multi-Platform Deployment")
    print("=" * 60)

    # Detect all devices
    print("\n🔍 Detecting connected devices...")
    device_manifest = detect_all_devices()

    if not device_manifest or not device_manifest.get("devices"):
        print("❌ No devices detected. Please connect devices and try again.")
        sys.exit(1)

    devices = device_manifest["devices"]

    # Apply platform filter if specified
    if args.filter_platform:
        devices = [d for d in devices if d.get("platform") in args.filter_platform]
        print(f"\n🔍 Filtered to {len(devices)} device(s): {args.filter_platform}")

    # Display detected devices
    print(f"\n📱 Found {len(devices)} device(s):")
    for i, device in enumerate(devices, 1):
        platform = device.get("platform", "unknown")
        connection = device.get("connection_type", "unknown")

        if connection == "serial":
            print(f"  {i}. {device['type']} ({platform}) on {device['port']}")
        elif connection == "adb":
            print(f"  {i}. {device['type']} ({platform}) {device['device_id']}")
        elif connection == "network":
            print(f"  {i}. {device['type']} ({platform}) at {device['ip']}")

    if args.dry_run:
        print("\n🔍 DRY RUN - No actual deployment will occur")
        sys.exit(0)

    # Confirm deployment
    if not args.yes:
        response = input("\n⚠️  Proceed with deployment? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Deployment cancelled.")
            sys.exit(0)
    else:
        print("\n⚠️  Auto-confirming deployment (--yes flag used)")

    # Deploy based on mode
    if args.mode == "parallel":
        results = deploy_parallel(devices, project_dir, args)
    else:
        results = deploy_sequential(devices, project_dir, args)

    # Summary
    print(f"\n{'='*60}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'='*60}")

    success_count = sum(1 for r in results if r)
    total_count = len(results)

    for i, (device, result) in enumerate(zip(devices, results), 1):
        status = "✅ SUCCESS" if result else "❌ FAILED"

        if device.get("connection_type") == "serial":
            identifier = device["port"]
        elif device.get("connection_type") == "adb":
            identifier = device["device_id"]
        elif device.get("connection_type") == "network":
            identifier = device["ip"]
        else:
            identifier = "unknown"

        print(f"{i}. {device['type']} ({identifier}): {status}")

    print(f"\n{success_count}/{total_count} devices deployed successfully")

    if success_count == total_count:
        print("✅ All devices deployed successfully!")
        sys.exit(0)
    else:
        print("⚠️  Some devices failed to deploy")
        sys.exit(1)

if __name__ == "__main__":
    main()