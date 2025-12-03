#!/usr/bin/env python3
"""
OBD Simulator Bootstrap

Sets up and runs the OBD-II simulator with bundled CPython.
Useful for development and testing of BLE OBD integration.

Usage:
    python3 bootstrap-obd.py [--port PORT] [--device DEVICE] [--mock]
    
Options:
    --port PORT      Serial port (default: /dev/ttyUSB0)
    --device DEVICE  BLE device name (default: OBD-II Simulator)
    --mock           Run in mock mode without hardware
"""

import argparse
import sys
from pathlib import Path

# Add lib to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.cpython_bootstrap import CPythonBootstrap, get_bundled_python


OBD_SIMULATOR_SCRIPT = """
#!/usr/bin/env python3
\"\"\"
OBD-II Simulator

Simulates OBD-II responses for testing Android BLE integration.
\"\"\"

import asyncio
import json
import random
import sys
from datetime import datetime
from typing import Dict, Optional

# OBD-II PIDs and their simulated responses
OBD_PIDS = {
    "0100": {  # Supported PIDs 01-20
        "name": "Supported PIDs",
        "value": "BE1FA813"
    },
    "0105": {  # Engine coolant temperature
        "name": "Engine Coolant Temp",
        "generator": lambda: random.randint(70, 105),
        "unit": "°C"
    },
    "010C": {  # Engine RPM
        "name": "Engine RPM",
        "generator": lambda: random.randint(750, 3500),
        "unit": "rpm"
    },
    "010D": {  # Vehicle speed
        "name": "Vehicle Speed",
        "generator": lambda: random.randint(0, 120),
        "unit": "km/h"
    },
    "010F": {  # Intake air temperature
        "name": "Intake Air Temp",
        "generator": lambda: random.randint(20, 45),
        "unit": "°C"
    },
    "0111": {  # Throttle position
        "name": "Throttle Position",
        "generator": lambda: random.randint(0, 100),
        "unit": "%"
    },
    "012F": {  # Fuel tank level
        "name": "Fuel Level",
        "generator": lambda: random.randint(20, 100),
        "unit": "%"
    },
    "0142": {  # Control module voltage
        "name": "Battery Voltage",
        "generator": lambda: round(random.uniform(12.0, 14.8), 1),
        "unit": "V"
    }
}


class OBDSimulator:
    \"\"\"Simulates OBD-II device responses.\"\"\"
    
    def __init__(self, device_name: str = "OBD-II Simulator", mock: bool = False):
        self.device_name = device_name
        self.mock = mock
        self.running = False
        self._telemetry_cache: Dict[str, Dict] = {}
    
    def process_command(self, command: str) -> str:
        \"\"\"Process OBD-II command and return response.\"\"\"
        command = command.strip().upper()
        
        # Handle ATZ (reset)
        if command == "ATZ":
            return f"ELM327 v1.5 ({self.device_name})"
        
        # Handle AT commands
        if command.startswith("AT"):
            return self._handle_at_command(command)
        
        # Handle OBD PID requests
        if command in OBD_PIDS:
            return self._handle_pid_request(command)
        
        return "?"
    
    def _handle_at_command(self, command: str) -> str:
        \"\"\"Handle AT commands.\"\"\"
        at_responses = {
            "ATE0": "OK",      # Echo off
            "ATE1": "OK",      # Echo on
            "ATH0": "OK",      # Headers off
            "ATH1": "OK",      # Headers on
            "ATL0": "OK",      # Linefeeds off
            "ATL1": "OK",      # Linefeeds on
            "ATSP0": "OK",     # Auto protocol
            "ATDP": "AUTO",    # Describe protocol
            "ATRV": f"{round(random.uniform(12.0, 14.8), 1)}V",  # Read voltage
        }
        return at_responses.get(command, "OK")
    
    def _handle_pid_request(self, pid: str) -> str:
        \"\"\"Handle OBD PID request.\"\"\"
        pid_info = OBD_PIDS.get(pid)
        if not pid_info:
            return "NO DATA"
        
        if "value" in pid_info:
            return f"41 {pid[2:]} {pid_info['value']}"
        
        if "generator" in pid_info:
            value = pid_info["generator"]()
            # Convert to hex format
            if isinstance(value, float):
                hex_value = format(int(value * 10), "04X")
            else:
                hex_value = format(value, "04X")
            
            # Cache telemetry
            self._telemetry_cache[pid] = {
                "name": pid_info["name"],
                "value": value,
                "unit": pid_info.get("unit", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            return f"41 {pid[2:]} {hex_value}"
        
        return "NO DATA"
    
    def get_telemetry(self) -> Dict:
        \"\"\"Get cached telemetry readings.\"\"\"
        return self._telemetry_cache.copy()
    
    async def run_interactive(self):
        \"\"\"Run interactive OBD simulator.\"\"\"
        print(f"OBD-II Simulator ({self.device_name})")
        print("=" * 40)
        print("Enter OBD commands (ATZ to reset, Ctrl+C to exit)")
        print()
        
        self.running = True
        while self.running:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("> ")
                )
                response = self.process_command(command)
                print(response)
            except KeyboardInterrupt:
                print("\\nShutting down...")
                self.running = False
            except EOFError:
                self.running = False
    
    async def run_demo(self, duration: int = 60):
        \"\"\"Run demo mode with continuous telemetry output.\"\"\"
        print(f"OBD-II Simulator Demo Mode ({self.device_name})")
        print("=" * 40)
        print(f"Running for {duration} seconds...")
        print()
        
        self.running = True
        end_time = asyncio.get_event_loop().time() + duration
        
        pids_to_query = ["010C", "010D", "0105", "0111", "012F"]
        
        while self.running and asyncio.get_event_loop().time() < end_time:
            for pid in pids_to_query:
                if not self.running:
                    break
                response = self.process_command(pid)
                telemetry = self._telemetry_cache.get(pid, {})
                if telemetry:
                    print(f"[{telemetry.get('name', pid)}] "
                          f"{telemetry.get('value', 'N/A')} {telemetry.get('unit', '')}")
            
            print("-" * 40)
            await asyncio.sleep(2)
        
        print("\\nDemo complete")


async def main():
    parser = argparse.ArgumentParser(description="OBD-II Simulator")
    parser.add_argument("--device", default="OBD-II Simulator",
                       help="Device name")
    parser.add_argument("--mock", action="store_true",
                       help="Run in mock mode")
    parser.add_argument("--demo", type=int, metavar="SECONDS",
                       help="Run demo for specified seconds")
    parser.add_argument("--json", action="store_true",
                       help="Output in JSON format")
    
    args = parser.parse_args()
    
    simulator = OBDSimulator(device_name=args.device, mock=args.mock)
    
    if args.demo:
        await simulator.run_demo(duration=args.demo)
    else:
        await simulator.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
"""


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap OBD-II Simulator with bundled CPython"
    )
    parser.add_argument(
        "--port", 
        default="/dev/ttyUSB0",
        help="Serial port (default: /dev/ttyUSB0)"
    )
    parser.add_argument(
        "--device",
        default="OBD-II Simulator",
        help="BLE device name (default: OBD-II Simulator)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode without hardware"
    )
    parser.add_argument(
        "--demo",
        type=int,
        metavar="SECONDS",
        help="Run demo for specified seconds"
    )
    parser.add_argument(
        "--use-system-python",
        action="store_true",
        help="Use system Python instead of bundled"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("OBD-II Simulator Bootstrap")
    print("=" * 50)
    
    if args.use_system_python:
        python_path = sys.executable
        print(f"Using system Python: {python_path}")
    else:
        print("Setting up bundled CPython...")
        bootstrap = CPythonBootstrap()
        python_path = str(bootstrap.ensure_python())
        print(f"Using bundled Python: {python_path}")
    
    print()
    
    # Create temporary script file
    import tempfile
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="obd_simulator_")
    try:
        with open(script_path, "w") as f:
            f.write(OBD_SIMULATOR_SCRIPT)
        
        # Build command
        cmd = [python_path, script_path]
        cmd.extend(["--device", args.device])
        if args.mock:
            cmd.append("--mock")
        if args.demo:
            cmd.extend(["--demo", str(args.demo)])
        
        print(f"Running: {' '.join(cmd)}")
        print()
        
        import subprocess
        result = subprocess.run(cmd)
        return result.returncode
        
    finally:
        Path(script_path).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
