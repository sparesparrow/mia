import zmq
import serial
import json
import time
import logging

<<<<<<< HEAD
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
=======
class SerialBridge:
    def __init__(self, serial_port="/dev/ttyUSB0", baud_rate=115200, zmq_endpoint="tcp://*:5556"):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.zmq_endpoint = zmq_endpoint
        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        
    def run(self):
        """Main loop"""
        self.pub_socket.bind(self.zmq_endpoint)
        logging.info(f"[HW] Bound to {self.zmq_endpoint}")
        
        ser = None
        while True:
            try:
                if not ser:
                    if self.serial_port:
                        ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
                        logging.info("[HW] Serial Connected")
                    else:
                        # Mock mode or wait
                        time.sleep(1)
                        continue
                
                line = ser.readline().decode().strip()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        self._publish_telemetry(data)
                    except json.JSONDecodeError:
                        pass
                    
            except Exception as e:
                logging.error(f"[HW] Serial error: {e}")
                ser = None
                time.sleep(1)

    def _publish_telemetry(self, data):
        """Publish telemetry data to ZMQ"""
        # Re-publish raw JSON onto ZMQ "mcu/telemetry" topic
        # The test expects topic and message separate, or specific format.
        # Original code: pub.send_multipart([b"mcu/telemetry", line.encode()])
        # But 'data' is dict here.
        payload = json.dumps(data)
        self.pub_socket.send_multipart([b"mcu/telemetry", payload.encode('utf-8')])

def run_bridge():
    bridge = SerialBridge()
    bridge.run()
>>>>>>> 5376269 (rebase)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bridge()
<<<<<<< HEAD
=======

>>>>>>> 5376269 (rebase)
