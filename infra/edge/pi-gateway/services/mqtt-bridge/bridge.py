import os
import threading
import paho.mqtt.client as mqtt

local_url = os.getenv("LOCAL_URL", "tcp://localhost:1883")
remote_url = os.getenv("REMOTE_URL", "")
forward_topics = [t.strip() for t in os.getenv("FORWARD_TOPICS", "vehicle/#,device/#,system/#,security/#,privacy/#").split(",")]

if not remote_url:
    # No remote configured; act as a no-op placeholder
    import time
    while True:
        time.sleep(3600)

def parse(url: str):
    host = url.split("://", 1)[-1].split(":")[0]
    port = int(url.split(":")[-1])
    return host, port

l_host, l_port = parse(local_url)
r_host, r_port = parse(remote_url)

lc = mqtt.Client(client_id="ai-servis-bridge-local")
rc = mqtt.Client(client_id="ai-servis-bridge-remote")

def on_l_message(_client, _userdata, msg):
    # forward from local -> remote
    rc.publish(msg.topic, payload=msg.payload, qos=msg.qos, retain=msg.retain)

def on_r_message(_client, _userdata, msg):
    # forward from remote -> local
    lc.publish(msg.topic, payload=msg.payload, qos=msg.qos, retain=msg.retain)

lc.on_message = on_l_message
rc.on_message = on_r_message

lc.connect(l_host, l_port, 60)
rc.connect(r_host, r_port, 60)

for t in forward_topics:
    lc.subscribe(t, qos=1)
    rc.subscribe(t, qos=1)

t1 = threading.Thread(target=lc.loop_forever, daemon=True)
t2 = threading.Thread(target=rc.loop_forever, daemon=True)
t1.start()
t2.start()

try:
    t1.join()
    t2.join()
except KeyboardInterrupt:
    pass


