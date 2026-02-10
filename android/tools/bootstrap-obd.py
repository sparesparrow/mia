#!/usr/bin/env python3
"""
MIA OBD-II Simulator Bootstrap Script

This script orchestrates the download, extraction, and execution of the 
ELM327-emulator without system-wide dependencies.

Usage:
    python3 bootstrap-obd.py [--port PORT] [--scenario SCENARIO]

Options:
    --port PORT         TCP port for the emulator (default: 35000)
    --scenario SCENARIO Simulation scenario: car, truck, motorcycle (default: car)
"""

import sys
import os
import urllib.request
import tarfile
import subprocess
import platform
import shutil
import argparse

# CONFIGURATION
CPY_VER = "3.12.7"
PLATFORM_MAP = {
    "Linux": "linux-x86_64",
    "Darwin": "macos-arm64",  # Assumes Apple Silicon, adjust for intel
    "Windows": "windows-x86_64"
}
SYS_PLATFORM = platform.system()
ARCH = PLATFORM_MAP.get(SYS_PLATFORM, "linux-x86_64")
URL = f"https://dl.cloudsmith.io/public/sparesparrow/cpy/raw/files/cpython-tool-{CPY_VER}-{ARCH}.tar.gz"
INSTALL_DIR = os.path.abspath(".mia/python")
BIN_DIR = os.path.join(INSTALL_DIR, "Scripts" if SYS_PLATFORM == "Windows" else "bin")
PIP_EXE = os.path.join(BIN_DIR, "pip.exe" if SYS_PLATFORM == "Windows" else "pip3")
PYTHON_EXE = os.path.join(BIN_DIR, "python.exe" if SYS_PLATFORM == "Windows" else "python3")


def parse_args():
    parser = argparse.ArgumentParser(description="MIA OBD-II Simulator Bootstrap")
    parser.add_argument("--port", "-p", type=int, default=35000, 
                        help="TCP port for the emulator (default: 35000)")
    parser.add_argument("--scenario", "-s", type=str, default="car",
                        choices=["car", "truck", "motorcycle"],
                        help="Simulation scenario (default: car)")
    parser.add_argument("--clean", action="store_true",
                        help="Clean existing installation and re-bootstrap")
    parser.add_argument("--serial", action="store_true",
                        help="Use virtual serial port instead of TCP")
    return parser.parse_args()


def bootstrap(args):
    """Bootstrap the CPython environment and ELM327 emulator."""
    
    # Clean if requested
    if args.clean and os.path.exists(INSTALL_DIR):
        print("[MIA] Cleaning existing installation...")
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
    
    if not os.path.exists(INSTALL_DIR):
        print(f"[MIA] Fetching CPython {CPY_VER} from Cloudsmith...")
        try:
            os.makedirs(os.path.dirname(INSTALL_DIR), exist_ok=True)
            file_tmp, _ = urllib.request.urlretrieve(URL)
            print("[MIA] Extracting runtime...")
            with tarfile.open(file_tmp, "r:gz") as tar:
                tar.extractall(INSTALL_DIR)
            os.unlink(file_tmp)
        except urllib.error.HTTPError as e:
            print(f"[FAIL] HTTP Error: {e.code} - {e.reason}")
            print(f"[HINT] Verify CPython version {CPY_VER} exists at Cloudsmith")
            sys.exit(1)
        except Exception as e:
            print(f"[FAIL] Bootstrap failed: {e}")
            sys.exit(1)
    else:
        print(f"[MIA] Using existing CPython installation at {INSTALL_DIR}")

    # Validate extracted files
    if not os.path.exists(PYTHON_EXE):
        print(f"[FAIL] Python executable not found at {PYTHON_EXE}")
        print("[HINT] Try running with --clean to re-bootstrap")
        sys.exit(1)

    # Setup environment
    env = os.environ.copy()
    env["PYTHONHOME"] = INSTALL_DIR
    if SYS_PLATFORM != "Windows":
        env["PATH"] = f"{BIN_DIR}:{env.get('PATH', '')}"
    else:
        env["PATH"] = f"{BIN_DIR};{env.get('PATH', '')}"

    print("[MIA] Installing OBD Simulator dependencies...")
    try:
        subprocess.run(
            [PIP_EXE, "install", "--quiet", "ELM327-emulator", "obd", "pyserial"],
            env=env, 
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Dependency installation failed: {e.stderr.decode()}")
        sys.exit(1)

    print(f"[MIA] Launching ELM327 Simulator...")
    print(f"      Scenario: {args.scenario}")
    print(f"      Port: {args.port}")
    print("")
    print("=" * 60)
    print(" ELM327 OBD-II Emulator")
    print(" Connect your OBD diagnostic software to:")
    if args.serial:
        print("   Virtual Serial Port: (see output below)")
    else:
        print(f"   TCP: localhost:{args.port}")
    print("=" * 60)
    print("")

    # Build command arguments
    cmd = [PYTHON_EXE, "-m", "elm", "-s", args.scenario]
    if not args.serial:
        cmd.extend(["-p", str(args.port)])

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\n[MIA] Simulator stopped.")


def check_system_python():
    """Check if we can use system Python as fallback."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import sys; print(sys.version_info[:2])"],
            capture_output=True, text=True
        )
        version = eval(result.stdout.strip())
        if version >= (3, 8):
            return True
    except:
        pass
    return False


def fallback_install(args):
    """Use system Python if CPython bootstrap fails."""
    print("[MIA] Using system Python as fallback...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "ELM327-emulator", "obd", "pyserial"],
            check=True
        )
        
        cmd = [sys.executable, "-m", "elm", "-s", args.scenario]
        if not args.serial:
            cmd.extend(["-p", str(args.port)])
        
        subprocess.run(cmd)
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Fallback installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    
    try:
        bootstrap(args)
    except Exception as e:
        print(f"[WARN] Bootstrap failed: {e}")
        if check_system_python():
            print("[MIA] Attempting fallback to system Python...")
            fallback_install(args)
        else:
            print("[FAIL] No suitable Python environment found")
            sys.exit(1)

