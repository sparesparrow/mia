import zmq
import serial
import json
import time
import logging

# PUB to the same bus the OBD service SUBs from
ZMQ_PUB_ENDPOINT = "tcp://*:5556"

def run_bridge():
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(ZMQ_PUB_ENDPOINT)
    logging.info(f"[HW] Bound to {ZMQ_PUB_ENDPOINT}")
    
    # Auto-reconnect logic for Serial
    ser = None
    while True:
        try:
            if not ser:
                # Scan logic or hardcoded for now
                ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
                logging.info("[HW] Serial Connected")
            
            line = ser.readline().decode().strip()
            if line.startswith("{"):
                # Re-publish raw JSON onto ZMQ "mcu/telemetry" topic
                pub.send_multipart([b"mcu/telemetry", line.encode()])
                
        except Exception as e:
            logging.error(f"[HW] Serial error: {e}")
            ser = None
            time.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bridge()
