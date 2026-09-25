import os, json, time, math, random, paho.mqtt.client as mqtt

broker = os.getenv("MQTT_URL", "tcp://localhost:1883")
host = broker.split("://", 1)[-1].split(":")[0]
port = int(broker.split(":")[-1])
vin = os.getenv("VIN", "TESTVIN")
rate_hz = float(os.getenv("RATE_HZ", "5"))
topic = f"vehicle/telemetry/{vin}/obd"

def connect_with_retry(client: mqtt.Client, host: str, port: int):
    backoff = [0, 1, 2, 5, 5, 5]
    attempt = 0
    while True:
        try:
            client.connect(host, port, 60)
            return
        except Exception:
            delay = backoff[min(attempt, len(backoff) - 1)]
            attempt += 1
            time.sleep(delay)

c = mqtt.Client(client_id="obd-sim")
connect_with_retry(c, host, port)

t0 = time.time()

def frame(t):
    rpm = 800 + int(700 * (1 + math.sin(t * 0.8)))
    speed = max(0, int(50 + 20 * math.sin(t * 0.3)))
    coolant = 85 + int(10 * (0.5 + 0.5 * math.sin(t * 0.05)))
    fuel = max(5, 60 - int((t / 60) % 60))
    engine_load = int(30 + 20 * random.random())
    dtc = [] if random.random() > 0.98 else ["P0420"]
    return {
        "engine_rpm": rpm,
        "vehicle_speed": speed,
        "coolant_temp": coolant,
        "fuel_level": fuel,
        "engine_load": engine_load,
        "dtc_codes": dtc,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

period = 1.0 / max(0.1, rate_hz)
while True:
    t = time.time() - t0
    payload = frame(t)
    try:
        c.publish(topic, json.dumps(payload), qos=1, retain=False)
    except Exception:
        connect_with_retry(c, host, port)
    time.sleep(period)


