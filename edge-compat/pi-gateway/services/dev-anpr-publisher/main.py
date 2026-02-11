import os, json, time, random, hashlib, paho.mqtt.client as mqtt

broker = os.getenv("MQTT_URL", "tcp://localhost:1883")
host = broker.split("://", 1)[-1].split(":")[0]
port = int(broker.split(":")[-1])
vin = os.getenv("VIN", "TESTVIN")
interval_ms = int(os.getenv("INTERVAL_MS", "2000"))
topic = f"vehicle/events/{vin}/anpr"

plates = ["1AB2345", "2BC3456", "BRN1234", "CZ123AB", "7XJ9000"]

def plate_hash(plate: str) -> str:
    # Dev-only hash
    return hashlib.sha256(plate.encode("utf-8")).hexdigest()

def connect_with_retry(client: mqtt.Client, host: str, port: int):
    backoff = [0, 1, 2, 5, 5, 5]
    attempt = 0
    while True:
        try:
            client.connect(host, port, 60)
            return
        except Exception as e:
            delay = backoff[min(attempt, len(backoff) - 1)]
            attempt += 1
            time.sleep(delay)

c = mqtt.Client(client_id="dev-anpr")
connect_with_retry(c, host, port)

while True:
    plate = random.choice(plates)
    payload = {
        "plate_hash": plate_hash(plate),
        "confidence": round(random.uniform(0.7, 0.98), 2),
        "snapshot_id": f"dev-{int(time.time()*1000)}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        c.publish(topic, json.dumps(payload), qos=1, retain=False)
    except Exception:
        connect_with_retry(c, host, port)
    time.sleep(max(0.1, interval_ms / 1000.0))


