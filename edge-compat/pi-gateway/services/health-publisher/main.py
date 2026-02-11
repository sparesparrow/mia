import os
import json
import time
import socket
import paho.mqtt.client as mqtt

broker = os.getenv("MQTT_URL", "tcp://localhost:1883")
host = broker.split("://", 1)[-1].split(":")[0]
port = int(broker.split(":")[-1])
node = os.getenv("NODE_ID", "pi-gateway-001")
topic = f"system/health/{node}"

client_id = f"ai-servis-health-{node}"
c = mqtt.Client(client_id=client_id, clean_session=True)
c.connect(host, port, 60)

while True:
    payload = {
        "node_id": node,
        "host": socket.gethostname(),
        "uptime": int(time.time()),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    c.publish(topic, json.dumps(payload), qos=1, retain=True)
    time.sleep(60)


