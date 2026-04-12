import logging
import os
import sys
import time
from typing import Callable, Optional

import serial
import zmq

# Add project root to sys.path to allow importing 'Mia' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Attempt to import generated FlatBuffers classes
# In a real setup, these would be generated into a known python path
try:
    from Mia.vehicle_codec import build_citroen_telemetry
except ImportError:
    build_citroen_telemetry = None

from agents import psa_decoder

logger = logging.getLogger(__name__)


def parse_hex_val(resp: str, prefix: str = '41') -> str:
    """Extract the payload bytes from an ELM327-style hexadecimal response."""
    clean = resp.replace(" ", "").replace(">", "").strip()
    if prefix and prefix in clean:
        idx = clean.find(prefix)
        return clean[idx + 4:]
    return clean


def decode_hex_measurement(
    raw_response: str,
    prefix: str,
    field_name: str,
    transform: Callable[[int], float],
) -> float:
    """Decode a numeric OBD field and fall back to 0.0 when the payload is malformed."""
    payload = parse_hex_val(raw_response, prefix)
    if not payload:
        return 0.0

    try:
        return transform(int(payload, 16))
    except ValueError:
        logger.warning(
            "Failed to parse %s from response %r (payload=%r)",
            field_name,
            raw_response,
            payload,
        )
        return 0.0

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
            rpm = decode_hex_measurement(rpm_raw, '410C', 'rpm', lambda value: value / 4.0)
            speed = decode_hex_measurement(speed_raw, '410D', 'speed', float)
            coolant = decode_hex_measurement(coolant_raw, '4105', 'coolant', lambda value: float(value - 40))

            # Use PSA Decoder
            # Note: The decoder expects raw hex of the data, or the full response?
            # Our decoder handles some cleanup.
            soot_mass = psa_decoder.decode_soot_mass(soot_raw)
            oil_temp = psa_decoder.decode_oil_temp(oil_raw)
            eolys_pct, eolys_l = psa_decoder.decode_eolys_level(eolys_raw)
            dpf_status_val = psa_decoder.decode_dpf_status(soot_raw) # Assuming status is in same response or similar

            # -- Serialization --
            if build_citroen_telemetry:
                buf = build_citroen_telemetry(
                    {
                        "rpm": rpm,
                        "speed_kmh": speed,
                        "coolant_temp_c": coolant,
                        "dpf_soot_mass_g": soot_mass,
                        "oil_temperature_c": oil_temp,
                        "eolys_additive_level_percent": eolys_pct,
                        "eolys_additive_level_l": eolys_l,
                        "dpf_regeneration_status": dpf_status_val,
                        "timestamp": int(time.time() * 1000),
                    }
                )
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
