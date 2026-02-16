#!/usr/bin/env python3
"""
Simple OBD-II ELM327 Simulator for Testing

This simulator responds to standard ELM327 AT commands and OBD-II PIDs.
Run this on your development machine and connect your Android app via TCP.

Usage:
    python3 obd-simulator.py [--port PORT]
    
Default port: 35000
Connect from Android app using: tcp://localhost:35000
"""

import socket
import threading
import argparse
import random
import time
from typing import Dict, Callable

# Simulated vehicle data
class VehicleState:
    def __init__(self):
        self.rpm = 800  # Engine RPM
        self.speed = 0  # km/h
        self.coolant_temp = 90  # °C
        self.fuel_level = 75  # %
        self.throttle = 0  # %
        self.engine_load = 20  # %
        self.intake_temp = 25  # °C
        self.maf = 5.0  # g/s
        self.o2_voltage = 0.45  # V
        self.running = True
    
    def update(self):
        """Simulate realistic vehicle behavior"""
        if self.running:
            # Simulate idle fluctuation
            self.rpm = 800 + random.randint(-50, 50)
            if self.throttle > 0:
                self.rpm = min(6000, self.rpm + self.throttle * 50)
                self.speed = min(200, self.speed + random.randint(0, 5))
            else:
                self.speed = max(0, self.speed - random.randint(0, 3))
            
            # Temperature simulation
            if self.coolant_temp < 90:
                self.coolant_temp += random.uniform(0, 0.5)
            else:
                self.coolant_temp = 90 + random.randint(-2, 2)
            
            # Fuel consumption
            if self.fuel_level > 0:
                self.fuel_level -= random.uniform(0, 0.01)
            
            # Engine load based on throttle
            self.engine_load = 20 + self.throttle * 0.5
            
            # MAF based on RPM and load
            self.maf = 5.0 + (self.rpm / 1000) * 2


class ELM327Simulator:
    """ELM327 OBD-II Adapter Simulator"""
    
    def __init__(self, port: int = 35000):
        self.port = port
        self.vehicle = VehicleState()
        self.echo = True
        self.linefeeds = True
        self.spaces = True
        self.protocol = "AUTO"
        self.running = True
        
        # AT command handlers
        self.at_commands: Dict[str, Callable] = {
            "ATZ": self._cmd_reset,
            "ATE0": self._cmd_echo_off,
            "ATE1": self._cmd_echo_on,
            "ATL0": self._cmd_linefeeds_off,
            "ATL1": self._cmd_linefeeds_on,
            "ATS0": self._cmd_spaces_off,
            "ATS1": self._cmd_spaces_on,
            "ATSP0": self._cmd_protocol_auto,
            "ATI": self._cmd_identify,
            "ATRV": self._cmd_voltage,
            "ATDP": self._cmd_describe_protocol,
            "ATDPN": self._cmd_describe_protocol_num,
            "ATH0": lambda: "OK",
            "ATH1": lambda: "OK",
            "ATST": lambda: "OK",
            "ATAT1": lambda: "OK",
            "ATAT2": lambda: "OK",
        }
        
        # OBD-II PID handlers (Mode 01)
        self.obd_pids: Dict[str, Callable] = {
            "0100": self._pid_supported_01_20,
            "0105": self._pid_coolant_temp,
            "010C": self._pid_rpm,
            "010D": self._pid_speed,
            "0110": self._pid_maf,
            "0111": self._pid_throttle,
            "012F": self._pid_fuel_level,
            "0104": self._pid_engine_load,
            "010F": self._pid_intake_temp,
            "0114": self._pid_o2_sensor,
        }
    
    def _cmd_reset(self) -> str:
        self.echo = True
        self.linefeeds = True
        self.spaces = True
        return "ELM327 v1.5\r\n>"
    
    def _cmd_echo_off(self) -> str:
        self.echo = False
        return "OK"
    
    def _cmd_echo_on(self) -> str:
        self.echo = True
        return "OK"
    
    def _cmd_linefeeds_off(self) -> str:
        self.linefeeds = False
        return "OK"
    
    def _cmd_linefeeds_on(self) -> str:
        self.linefeeds = True
        return "OK"
    
    def _cmd_spaces_off(self) -> str:
        self.spaces = False
        return "OK"
    
    def _cmd_spaces_on(self) -> str:
        self.spaces = True
        return "OK"
    
    def _cmd_protocol_auto(self) -> str:
        self.protocol = "AUTO"
        return "OK"
    
    def _cmd_identify(self) -> str:
        return "ELM327 v1.5"
    
    def _cmd_voltage(self) -> str:
        voltage = 12.4 + random.uniform(-0.2, 0.2)
        return f"{voltage:.1f}V"
    
    def _cmd_describe_protocol(self) -> str:
        return "AUTO, ISO 15765-4 (CAN 11/500)"
    
    def _cmd_describe_protocol_num(self) -> str:
        return "6"
    
    def _pid_supported_01_20(self) -> str:
        # Bits indicate which PIDs 01-20 are supported
        # Supporting: 04, 05, 0C, 0D, 0F, 10, 11, 14, 1F, 2F
        return "41 00 BE 3F A8 13"
    
    def _pid_coolant_temp(self) -> str:
        # Formula: A - 40 = temp in °C
        temp_byte = int(self.vehicle.coolant_temp + 40)
        return f"41 05 {temp_byte:02X}"
    
    def _pid_rpm(self) -> str:
        # Formula: ((A*256)+B)/4 = RPM
        rpm_val = int(self.vehicle.rpm * 4)
        a = (rpm_val >> 8) & 0xFF
        b = rpm_val & 0xFF
        return f"41 0C {a:02X} {b:02X}"
    
    def _pid_speed(self) -> str:
        # Formula: A = speed in km/h
        speed = int(self.vehicle.speed)
        return f"41 0D {speed:02X}"
    
    def _pid_maf(self) -> str:
        # Formula: ((A*256)+B)/100 = g/s
        maf_val = int(self.vehicle.maf * 100)
        a = (maf_val >> 8) & 0xFF
        b = maf_val & 0xFF
        return f"41 10 {a:02X} {b:02X}"
    
    def _pid_throttle(self) -> str:
        # Formula: A*100/255 = %
        throttle = int(self.vehicle.throttle * 255 / 100)
        return f"41 11 {throttle:02X}"
    
    def _pid_fuel_level(self) -> str:
        # Formula: A*100/255 = %
        fuel = int(self.vehicle.fuel_level * 255 / 100)
        return f"41 2F {fuel:02X}"
    
    def _pid_engine_load(self) -> str:
        # Formula: A*100/255 = %
        load = int(self.vehicle.engine_load * 255 / 100)
        return f"41 04 {load:02X}"
    
    def _pid_intake_temp(self) -> str:
        # Formula: A - 40 = temp in °C
        temp_byte = int(self.vehicle.intake_temp + 40)
        return f"41 0F {temp_byte:02X}"
    
    def _pid_o2_sensor(self) -> str:
        # Simplified O2 sensor response
        voltage = int(self.vehicle.o2_voltage * 200)
        return f"41 14 {voltage:02X} 80"
    
    def process_command(self, cmd: str) -> str:
        """Process an OBD-II command and return response"""
        cmd = cmd.strip().upper().replace(" ", "")
        
        if not cmd:
            return ""
        
        # Handle AT commands
        for at_cmd, handler in self.at_commands.items():
            if cmd.startswith(at_cmd):
                return handler()
        
        # Handle OBD-II PIDs
        for pid, handler in self.obd_pids.items():
            if cmd == pid:
                return handler()
        
        # Unknown command
        if cmd.startswith("AT"):
            return "OK"
        elif cmd.startswith("01"):
            return "NO DATA"
        else:
            return "?"
    
    def format_response(self, response: str) -> str:
        """Format response according to current settings"""
        if not self.spaces:
            response = response.replace(" ", "")
        
        if self.linefeeds:
            response = response + "\r\n"
        else:
            response = response + "\r"
        
        return response + ">"
    
    def handle_client(self, conn: socket.socket, addr: tuple):
        """Handle a single client connection"""
        print(f"[OBD-SIM] Client connected: {addr}")
        buffer = ""
        
        try:
            while self.running:
                data = conn.recv(1024)
                if not data:
                    break
                
                buffer += data.decode('utf-8', errors='ignore')
                
                # Process complete commands (ending with \r)
                while '\r' in buffer:
                    cmd, buffer = buffer.split('\r', 1)
                    cmd = cmd.strip()
                    
                    if cmd:
                        print(f"[OBD-SIM] Received: {cmd}")
                        
                        # Update vehicle state
                        self.vehicle.update()
                        
                        # Process command
                        response = self.process_command(cmd)
                        formatted = self.format_response(response)
                        
                        # Echo command if enabled
                        if self.echo and not cmd.startswith("AT"):
                            conn.send((cmd + "\r").encode())
                        
                        print(f"[OBD-SIM] Sending: {response}")
                        conn.send(formatted.encode())
        
        except Exception as e:
            print(f"[OBD-SIM] Error: {e}")
        finally:
            print(f"[OBD-SIM] Client disconnected: {addr}")
            conn.close()
    
    def start(self):
        """Start the OBD-II simulator server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(5)
        
        print("=" * 60)
        print(" ELM327 OBD-II Simulator")
        print("=" * 60)
        print(f" Listening on port {self.port}")
        print(f" Connect your OBD diagnostic software to:")
        print(f"   TCP: localhost:{self.port}")
        print("")
        print(" Simulating: Toyota Auris Hybrid (default vehicle)")
        print(" Supported PIDs: RPM, Speed, Coolant Temp, Fuel Level, etc.")
        print("")
        print(" Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            while self.running:
                conn, addr = server.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\n[OBD-SIM] Shutting down...")
        finally:
            self.running = False
            server.close()


def main():
    parser = argparse.ArgumentParser(description="ELM327 OBD-II Simulator")
    parser.add_argument("--port", "-p", type=int, default=35000,
                        help="TCP port (default: 35000)")
    args = parser.parse_args()
    
    simulator = ELM327Simulator(port=args.port)
    simulator.start()


if __name__ == "__main__":
    main()

