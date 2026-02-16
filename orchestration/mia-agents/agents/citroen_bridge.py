import logging
import os
import sys
import time
from typing import Optional

import flatbuffers
import serial
import zmq

# Add project root to sys.path to allow importing 'Mia' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Attempt to import generated FlatBuffers classes
# In a real setup, these would be generated into a known python path
try:
    import Mia.Vehicle.CitroenTelemetry as CitroenTelemetry
    import Mia.Vehicle.DpfStatus as DpfStatus
except ImportError:
    # Fallback/Placeholder if not yet generated
    CitroenTelemetry = None
    DpfStatus = None

from agents import psa_decoder

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Configuration
    serial_port = os.environ.get('ELM_SERIAL_PORT', '/dev/ttyUSB0')
    baud_rate = int(os.environ.get('ELM_BAUD_RATE', 38400))
    zmq_pub_port = int(os.environ.get('ZMQ_PUB_PORT', 5557))

    # Setup ZMQ
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{zmq_pub_port}")
    logging.info(f"ZMQ Publisher bound to tcp://*:{zmq_pub_port}")

    # Setup Serial
    ser: Optional[serial.Serial] = None
    if os.environ.get('ELM_MOCK', '0') == '1':
        logging.info("Starting in MOCK mode")
    else:
        try:
            ser = serial.Serial(serial_port, baud_rate, timeout=1)
            logging.info(f"Connected to {serial_port} at {baud_rate} baud")
        except serial.SerialException as e:
            logging.error(f"Failed to connect to serial port {serial_port}: {e}")
            return

    # Initialize ELM327
    init_commands = [
        b"ATZ\r",      # Reset
        b"ATE0\r",     # Echo off
        b"ATL0\r",     # Linefeeds off
        b"ATSP0\r",    # Auto protocol search
        b"ATS0\r"      # Remove spaces from responses (optional, helps parsing)
    ]
    
    if ser:
        for cmd in init_commands:
            ser.write(cmd)
            time.sleep(0.2)
            resp = ser.read_all()
            logging.debug(f"Init cmd {cmd.strip()} resp: {resp}")

        logging.info("ELM327 initialized")

    while True:
        try:
            # -- Standard OBD PIDs --
            rpm_raw = ""
            speed_raw = ""
            coolant_raw = ""
            soot_raw = ""
            oil_raw = ""
            eolys_raw = ""
            
            if ser:
                # RPM (01 0C)
                ser.write(b"010C\r")
                rpm_raw = ser.read_until(b'>').strip().decode('utf-8', errors='ignore')

                # Speed (01 0D)
                ser.write(b"010D\r")
                speed_raw = ser.read_until(b'>').strip().decode('utf-8', errors='ignore')

                # Coolant (01 05)
                ser.write(b"0105\r")
                coolant_raw = ser.read_until(b'>').strip().decode('utf-8', errors='ignore')

                # -- PSA Specific PIDs (Example Placeholders) --
                # Adjust these PIDs/Modes based on actual PSA documentation

                # Soot Mass (Hypothetical Mode 21 PID 01)
                ser.write(b"2101\r")
                soot_raw = ser.read_until(b'>').strip().decode('utf-8', errors='ignore')

                # Oil Temp (Hypothetical Mode 21 PID 02)
                ser.write(b"2102\r")
                oil_raw = ser.read_until(b'>').strip().decode('utf-8', errors='ignore')

                # Eolys Level (Hypothetical)
                ser.write(b"2103\r")
                eolys_raw = ser.read_until(b'>').strip().decode('utf-8', errors='ignore')
            else:
                # Mock Data
                import random
                rpm_raw = f"41 0C {hex(int(random.randint(800, 3000) * 4))[2:]}"
                speed_raw = f"41 0D {hex(random.randint(0, 120))[2:]}"
                coolant_raw = f"41 05 {hex(random.randint(70, 90) + 40)[2:]}"
                # Soot: 46.60g -> 4660 -> 0x1234
                soot_raw = "1234"
                oil_raw = hex(random.randint(80, 110) + 40)[2:]  # degC
                eolys_raw = "64"  # 100%

            # -- Parsing --
            
            def parse_hex_val(resp, prefix='41'):
                # Basic parser for ELM327 response
                # Removes spaces, checks for prefix
                clean = resp.replace(" ", "").replace(">", "").strip()
                # If using ATS0, spaces are already gone
                # Response to 010C might be 410C0AFF
                if prefix and prefix in clean:
                    idx = clean.find(prefix)
                    # Return part after prefix + PID
                    # e.g. 410C -> data starts at idx + 4
                    return clean[idx+4:]
                return clean

            rpm = 0.0
            rpm_data = parse_hex_val(rpm_raw, '410C')
            if rpm_data:
                try:
                    rpm = int(rpm_data, 16) / 4.0
                except ValueError: pass

            speed = 0.0
            speed_data = parse_hex_val(speed_raw, '410D')
            if speed_data:
                try:
                    speed = float(int(speed_data, 16))
                except ValueError: pass

            coolant = 0.0
            coolant_data = parse_hex_val(coolant_raw, '4105')
            if coolant_data:
                try:
                    coolant = float(int(coolant_data, 16) - 40)
                except ValueError: pass

            # Use PSA Decoder
            # Note: The decoder expects raw hex of the data, or the full response?
            # Our decoder handles some cleanup.
            soot_mass = psa_decoder.decode_soot_mass(soot_raw)
            oil_temp = psa_decoder.decode_oil_temp(oil_raw)
            eolys_pct, eolys_l = psa_decoder.decode_eolys_level(eolys_raw)
            dpf_status_val = psa_decoder.decode_dpf_status(soot_raw) # Assuming status is in same response or similar

            # -- Serialization --
            if CitroenTelemetry:
                builder = flatbuffers.Builder(1024)
                
                CitroenTelemetry.CitroenTelemetryStart(builder)
                CitroenTelemetry.CitroenTelemetryAddRpm(builder, rpm)
                CitroenTelemetry.CitroenTelemetryAddSpeedKmh(builder, speed)
                CitroenTelemetry.CitroenTelemetryAddCoolantTempC(builder, coolant)
                
                CitroenTelemetry.CitroenTelemetryAddDpfSootMassG(builder, soot_mass)
                CitroenTelemetry.CitroenTelemetryAddOilTemperatureC(builder, oil_temp)
                CitroenTelemetry.CitroenTelemetryAddEolysAdditiveLevelPercent(builder, eolys_pct)
                CitroenTelemetry.CitroenTelemetryAddEolysAdditiveLevelL(builder, eolys_l)
                
                # Check enum validity
                if DpfStatus:
                     # Simple mapping, assuming decoder returned int 0, 1, 2
                    CitroenTelemetry.CitroenTelemetryAddDpfRegenerationStatus(builder, dpf_status_val)
                
                telemetry = CitroenTelemetry.CitroenTelemetryEnd(builder)
                builder.Finish(telemetry)
                
                buf = builder.Output()
                socket.send(buf)
            else:
                logging.warning("FlatBuffers not available, skipping publish")
                logging.info(f"Data: RPM={rpm}, Speed={speed}, Soot={soot_mass}")

            time.sleep(0.5)

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
