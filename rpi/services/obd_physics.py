import zmq
import serial
import struct
import time
import logging

# CONFIG
ECU_LINK = "/dev/ttyUSB1"  # The connection to the ESP32's "Serial2"
ZMQ_INPUT = "tcp://localhost:5556"

def run_physics_engine():
    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(ZMQ_INPUT)
    sub.subscribe(b"hardware/input")

    # High-speed binary link to the C++ ECU
    link = serial.Serial(ECU_LINK, 115200)

    rpm = 800
    speed = 0

    while True:
        try:
            # 1. Read Inputs (Non-blocking)
            try:
                topic, msg = sub.recv_multipart(flags=zmq.NOBLOCK)
                # ... update physics state based on msg ...
            except zmq.Again:
                pass

            # 2. Run Physics (e.g., acceleration curve)
            # ... complex math here ...

            # 3. Sync to C++ ECU (Binary Struct is faster than JSON)
            # Struct: [Header 'U', RPM (2b), Speed (1b), Checksum]
            packet = struct.pack('<CHBB', b'U', rpm, speed, 0)
            link.write(packet)
            
            time.sleep(0.05)  # 20Hz Update Rate is plenty for dashboard

        except Exception as e:
            logging.error(f"Error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_physics_engine()
