"""
MIA Power Monitor — graceful shutdown on ignition-off.

Monitors a GPIO pin connected to the car's ACC/ignition wire via an optocoupler.
When the ignition turns off (the pin moves to its "off" level), this service:
  1. Publishes a ZMQ shutdown message so all services can flush state
  2. Waits for services to drain (configurable delay)
  3. Triggers systemctl poweroff

GPIO wiring (optocoupler):
  ACC 12V ──[1kΩ]── optocoupler LED+ ── optocoupler LED- ── GND
  RPi GPIO{pin} ── optocoupler collector ── 3.3V (with 10kΩ pull-up)
  optocoupler emitter ── GND

  A conducting optocoupler (ignition ON) pulls the pin LOW through the collector; with the ignition
  OFF the 10 kΩ pull-up holds it HIGH. So, with this circuit:

  Ignition ON  → GPIO LOW
  Ignition OFF → GPIO HIGH (rising edge triggers shutdown)

  A stage that inverts this (ON → HIGH) is supported with IGNITION_ON_LEVEL=high.

Environment variables:
  IGNITION_GPIO_PIN  — BCM pin number (default: 17)
  IGNITION_ON_LEVEL  — pin level while the ignition is on: low (default, the circuit above) or high
  SHUTDOWN_DELAY     — seconds to wait for services to flush (default: 5)
  ZMQ_BROKER_URL     — broker address (default: tcp://localhost:5555)
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [power-monitor] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
IGNITION_PIN = int(os.environ.get("IGNITION_GPIO_PIN", "17"))
ON_LEVEL = os.environ.get("IGNITION_ON_LEVEL", "low").strip().lower()
if ON_LEVEL not in ("low", "high"):
    raise SystemExit(f"IGNITION_ON_LEVEL must be 'low' or 'high', got {ON_LEVEL!r}")
SHUTDOWN_DELAY = int(os.environ.get("SHUTDOWN_DELAY", "5"))
ZMQ_BROKER_URL = os.environ.get("ZMQ_BROKER_URL", "tcp://localhost:5555")
DEBOUNCE_SECONDS = 2  # ignore glitches shorter than this

# ── GPIO abstraction ──────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available — running in simulation mode")

# ── ZMQ notification ──────────────────────────────────────────────────────
try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    logger.warning("pyzmq not available — shutdown notifications disabled")


def publish_shutdown_notice():
    """Notify all ZMQ-connected services that shutdown is imminent."""
    if not ZMQ_AVAILABLE:
        return
    try:
        ctx = zmq.Context()
        sock = ctx.socket(zmq.DEALER)
        sock.setsockopt(zmq.LINGER, 1000)
        sock.connect(ZMQ_BROKER_URL)
        msg = {
            "type": "SYSTEM_SHUTDOWN",
            "reason": "ignition_off",
            "delay_seconds": SHUTDOWN_DELAY,
            "timestamp": datetime.now().isoformat()
        }
        sock.send_json(msg)
        logger.info("Shutdown notice sent via ZMQ")
        sock.close()
        ctx.term()
    except Exception as e:
        logger.error(f"Failed to send ZMQ shutdown notice: {e}")


def initiate_poweroff():
    """Order a clean system poweroff."""
    logger.info(f"Waiting {SHUTDOWN_DELAY}s for services to flush...")
    time.sleep(SHUTDOWN_DELAY)
    logger.info("Initiating system poweroff")
    subprocess.run(["systemctl", "poweroff"], check=False)


def monitor_gpio():
    """Main loop: watch the ignition GPIO pin for the edge to its "off" level."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(IGNITION_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    on_high = ON_LEVEL == "high"
    off_level = GPIO.LOW if on_high else GPIO.HIGH
    off_edge = GPIO.FALLING if on_high else GPIO.RISING

    logger.info(f"Monitoring GPIO {IGNITION_PIN} for ignition-off ({'falling' if on_high else 'rising'} edge)")
    logger.info(f"Ignition is ON when the pin is {ON_LEVEL.upper()}")
    logger.info(f"Current state: {'OFF' if GPIO.input(IGNITION_PIN) == off_level else 'ON'}")

    shutdown_requested = False

    def on_off_edge(channel):
        nonlocal shutdown_requested
        if shutdown_requested:
            return
        # Debounce: confirm the pin is still at the off level after a short delay
        time.sleep(DEBOUNCE_SECONDS)
        if GPIO.input(IGNITION_PIN) == off_level:
            logger.info("Ignition OFF confirmed (stable)")
            shutdown_requested = True
            publish_shutdown_notice()
            initiate_poweroff()
        else:
            logger.info("Ignition glitch detected — ignoring")

    GPIO.add_event_detect(
        IGNITION_PIN, off_edge,
        callback=on_off_edge,
        bouncetime=int(DEBOUNCE_SECONDS * 1000)
    )

    # Keep the process alive
    try:
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()


def monitor_simulation():
    """Simulation mode: just log and wait (for development/CI)."""
    logger.info(f"SIMULATION: Would monitor GPIO {IGNITION_PIN} for ignition-off")
    logger.info("SIMULATION: Send SIGTERM to simulate ignition-off")

    def on_sigterm(signum, frame):
        logger.info("SIGTERM received — simulating ignition-off")
        publish_shutdown_notice()
        logger.info(f"Would poweroff after {SHUTDOWN_DELAY}s (skipped in simulation)")
        sys.exit(0)

    signal.signal(signal.SIGTERM, on_sigterm)

    try:
        signal.pause()
    except KeyboardInterrupt:
        pass


def main():
    logger.info("MIA Power Monitor starting")
    logger.info(f"  Ignition GPIO pin: {IGNITION_PIN}")
    logger.info(f"  Shutdown delay: {SHUTDOWN_DELAY}s")
    logger.info(f"  ZMQ broker: {ZMQ_BROKER_URL}")

    if GPIO_AVAILABLE:
        monitor_gpio()
    else:
        monitor_simulation()


if __name__ == "__main__":
    main()
