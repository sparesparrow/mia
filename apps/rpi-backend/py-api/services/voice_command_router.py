"""
MIA Voice Command Router — maps spoken commands to API actions.

Subscribes to ZMQ 'mia/voice/transcript', interprets the user's intent,
calls the appropriate FastAPI endpoint, and publishes the spoken response
to 'mia/voice/response' for the TTS service.

This is the "brain" of the voice pipeline — it decides what the driver
meant and what to do about it.

Environment variables:
  API_BASE_URL        — FastAPI base URL (default: http://localhost:8000)
  ZMQ_TRANSCRIPT_PORT — SUB port for transcripts (default: 5560)
  ZMQ_PUB_PORT        — PUB port for voice responses (default: 5561)
"""

import os
import sys
import json
import time
import signal
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [voice-router] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
ZMQ_TRANSCRIPT_PORT = int(os.environ.get("ZMQ_TRANSCRIPT_PORT", "5560"))
ZMQ_PUB_PORT = int(os.environ.get("ZMQ_PUB_PORT", "5561"))

# ── Dependencies ──────────────────────────────────────────────────────────
try:
    import zmq
except ImportError:
    logger.error("pyzmq required"); sys.exit(1)

try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    logger.warning("httpx not available — using urllib fallback")

running = True


# ── Confidence-Based Routing with Confirmation ───────────────────────────
#
# Each route has a human-readable label and keyword groups.
# Matching produces a confidence score (0.0–1.0):
#   HIGH (≥0.6)  → execute immediately, no confirmation needed
#   LOW  (0.2–0.6) → ask "Did you mean: {label}?" and wait for yes/no
#   NONE (<0.2)  → "I didn't understand"
#
# Thresholds are tuned for driving safety: better to ask once than
# to execute the wrong command while the driver is in traffic.

CONFIRM_THRESHOLD = 0.6   # above this → auto-execute
MINIMUM_THRESHOLD = 0.2   # below this → "didn't understand"
CONFIRMATION_TIMEOUT_SEC = 8  # driver has 8s to say yes/no

# Words that count as "yes" or "no" in confirmation context
YES_WORDS = {"yes", "yeah", "yep", "correct", "do it", "go ahead", "confirm", "sure", "ok", "okay", "affirmative"}
NO_WORDS = {"no", "nope", "cancel", "never mind", "nevermind", "stop", "don't", "negative"}

# ── Route Definitions ────────────────────────────────────────────────────
# Each route: (label, keyword_groups, action_dict)
# keyword_groups is a list of sets — each set is a "concept". The score
# is the fraction of concepts matched. More concept matches = higher score.

ROUTES: List[Tuple[str, List[set], Dict[str, Any]]] = [
    # ── Status & Health ────────────────────────────────────────────────
    ("system status", [
        {"status", "health", "system"},
        {"how are you", "how's it going", "are you okay"},
    ], {
        "endpoint": "/status",
        "method": "GET",
        "params": {},
        "response_template": "_format_status",
    }),

    ("processor temperature", [
        {"temperature", "thermal", "temp"},
        {"hot", "heat", "overheating", "warm"},
    ], {
        "endpoint": "/health/thermal",
        "method": "GET",
        "params": {},
        "response_template": "_format_thermal",
    }),

    # ── Vehicle / OBD ──────────────────────────────────────────────────
    ("engine telemetry", [
        {"engine", "motor"},
        {"rpm", "speed", "telemetry", "vehicle", "car"},
        {"coolant", "temperature"},
    ], {
        "endpoint": "/telemetry",
        "method": "GET",
        "params": {},
        "response_template": "_format_telemetry",
    }),

    # ── Devices ────────────────────────────────────────────────────────
    ("connected devices", [
        {"devices", "connected", "peripherals"},
        {"list", "show", "what"},
    ], {
        "endpoint": "/devices",
        "method": "GET",
        "params": {},
        "response_template": "_format_devices",
    }),

    # ── Features ───────────────────────────────────────────────────────
    ("feature list", [
        {"features", "capabilities"},
        {"what can you do", "help", "list"},
    ], {
        "endpoint": "/features",
        "method": "GET",
        "params": {},
        "response_template": "_format_features",
    }),

    # ── LED Control ────────────────────────────────────────────────────
    ("turn lights off", [
        {"light", "lights", "led", "leds"},
        {"off", "turn off", "disable", "dark"},
    ], {
        "endpoint": "/led/state",
        "method": "PUT",
        "params": {"mode": "off"},
        "response_template": "_format_led_off",
    }),

    ("turn lights on", [
        {"light", "lights", "led", "leds"},
        {"on", "turn on", "enable", "bright"},
    ], {
        "endpoint": "/led/state",
        "method": "PUT",
        "params": {"mode": "on", "brightness": 128},
        "response_template": "_format_led_on",
    }),
]


def _score_route(text: str, keyword_groups: List[set]) -> float:
    """Score how well a transcript matches a route's keyword groups.

    Each keyword group represents a concept. The score is the fraction
    of concept groups that have at least one keyword present in the text.
    This means matching 2/3 concept groups gives 0.67 (above CONFIRM_THRESHOLD),
    while matching 1/3 gives 0.33 (triggers confirmation).
    """
    if not keyword_groups:
        return 0.0
    matched = 0
    for group in keyword_groups:
        if any(kw in text for kw in group):
            matched += 1
    return matched / len(keyword_groups)


def route_command(transcript: str) -> Optional[Tuple[str, Dict[str, Any], float]]:
    """
    Match a transcript against all routes and return the best match.

    Returns (label, action_dict, confidence) or None if nothing matches.
    """
    text = transcript.lower().strip()

    best_label = None
    best_action = None
    best_score = 0.0

    for label, keyword_groups, action in ROUTES:
        score = _score_route(text, keyword_groups)
        if score > best_score:
            best_score = score
            best_label = label
            best_action = action

    if best_score < MINIMUM_THRESHOLD:
        return None

    return (best_label, best_action, best_score)


# ── Response Formatters ───────────────────────────────────────────────────
# These turn JSON API responses into natural speech.

def _format_status(data: dict) -> str:
    status = data.get("status", "unknown")
    cpu = data.get("cpu", {}).get("percent", "?")
    mem = data.get("memory", {}).get("percent", "?")
    devices = data.get("devices_connected", 0)
    return f"System is {status}. CPU at {cpu} percent, memory at {mem} percent, {devices} devices connected."


def _format_thermal(data: dict) -> str:
    temp = data.get("temperature_c")
    status = data.get("status", "unknown")
    if temp is None:
        return "Temperature sensor is not available."
    return f"Processor temperature is {temp:.0f} degrees celsius. Status: {status}."


def _format_telemetry(data: dict) -> str:
    t = data.get("telemetry", {})
    vehicle = t.get("vehicle", {})
    if not vehicle:
        return "No vehicle telemetry data available."
    rpm = vehicle.get("rpm", "unknown")
    speed = vehicle.get("speed_kmh", "unknown")
    coolant = vehicle.get("coolant_temp_c", "unknown")
    return f"Engine at {rpm} RPM, speed {speed} kilometers per hour, coolant temperature {coolant} degrees."


def _format_devices(data: dict) -> str:
    count = data.get("count", 0)
    if count == 0:
        return "No devices connected."
    devices = data.get("devices", [])
    names = [d.get("name", d.get("device_id", "unknown")) for d in devices[:5]]
    return f"{count} devices connected: {', '.join(names)}."


def _format_features(data: dict) -> str:
    total = data.get("total", 0)
    summary = data.get("summary", {})
    parts = [f"{v} {k.lower()}" for k, v in summary.items()]
    return f"MIA has {total} features: {', '.join(parts)}."


def _format_led_off(data: dict) -> str:
    return "Lights turned off."


def _format_led_on(data: dict) -> str:
    brightness = data.get("brightness", "default")
    return f"Lights turned on at brightness {brightness}."


# ── Formatter Lookup ─────────────────────────────────────────────────────
FORMATTERS = {
    "_format_status": _format_status,
    "_format_thermal": _format_thermal,
    "_format_telemetry": _format_telemetry,
    "_format_devices": _format_devices,
    "_format_features": _format_features,
    "_format_led_off": _format_led_off,
    "_format_led_on": _format_led_on,
}


# ── API Client ────────────────────────────────────────────────────────────

def call_api(endpoint: str, method: str = "GET", params: dict = None) -> Optional[dict]:
    """Call the FastAPI endpoint and return the JSON response."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if HTTP_AVAILABLE:
            with httpx.Client(timeout=5.0) as client:
                if method == "GET":
                    r = client.get(url)
                elif method == "PUT":
                    r = client.put(url, json=params or {})
                elif method == "POST":
                    r = client.post(url, json=params or {})
                else:
                    return None
                r.raise_for_status()
                return r.json()
        else:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(url)
            if method in ("PUT", "POST") and params:
                req.data = json.dumps(params).encode()
                req.add_header("Content-Type", "application/json")
                req.method = method
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
    except Exception as e:
        logger.error(f"API call failed: {method} {url} — {e}")
        return None


# ── Main Loop ─────────────────────────────────────────────────────────────

def _execute_action(action: Dict[str, Any]) -> str:
    """Execute a matched action and return the spoken response."""
    api_result = call_api(
        action["endpoint"],
        action["method"],
        action.get("params")
    )
    if api_result is None:
        return "Sorry, I couldn't reach the system right now."

    template_name = action.get("response_template")
    formatter = FORMATTERS.get(template_name) if template_name else None
    if formatter:
        return formatter(api_result)
    return str(api_result)


def _publish_response(pub, text: str, transcript: str, route_endpoint: Optional[str]):
    """Publish a spoken response to the TTS service."""
    event = {
        "text": text,
        "source_transcript": transcript,
        "route": route_endpoint,
        "timestamp": datetime.now().isoformat(),
    }
    pub.send_multipart([
        b"mia/voice/response",
        json.dumps(event).encode()
    ])
    logger.info(f"Response: '{text[:80]}'")


def main():
    global running

    def handle_signal(signum, frame):
        global running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("MIA Voice Command Router starting")
    logger.info(f"  API: {API_BASE_URL}")
    logger.info(f"  Confirm threshold: {CONFIRM_THRESHOLD}, min: {MINIMUM_THRESHOLD}")

    ctx = zmq.Context()

    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://localhost:{ZMQ_TRANSCRIPT_PORT}")
    sub.subscribe(b"mia/voice/transcript")
    logger.info(f"Subscribed to mia/voice/transcript on port {ZMQ_TRANSCRIPT_PORT}")

    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://*:{ZMQ_PUB_PORT}")
    logger.info(f"Publishing responses on port {ZMQ_PUB_PORT}")

    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)

    # Confirmation state: None when idle, dict when awaiting yes/no
    pending_confirmation: Optional[Dict[str, Any]] = None

    try:
        while running:
            events = dict(poller.poll(200))

            # ── Check confirmation timeout ────────────────────────────
            if pending_confirmation:
                elapsed = time.time() - pending_confirmation["timestamp"]
                if elapsed > CONFIRMATION_TIMEOUT_SEC:
                    logger.info("Confirmation timed out")
                    _publish_response(pub, "No confirmation received, cancelling.", "", None)
                    pending_confirmation = None

            if sub not in events:
                continue

            topic, msg_data = sub.recv_multipart()
            msg = json.loads(msg_data)
            transcript = msg.get("text", "")

            if not transcript:
                continue

            text_lower = transcript.lower().strip()
            logger.info(f"Received: '{transcript}'")

            # ── State: AWAITING_CONFIRMATION ──────────────────────────
            route_this = True  # should we route this transcript?

            if pending_confirmation:
                label = pending_confirmation["label"]
                action = pending_confirmation["action"]
                pending_confirmation = None

                if any(w in text_lower for w in YES_WORDS):
                    logger.info(f"Confirmed: {label}")
                    response_text = _execute_action(action)
                    _publish_response(pub, response_text, transcript, action["endpoint"])
                    route_this = False
                elif any(w in text_lower for w in NO_WORDS):
                    logger.info(f"Denied: {label}")
                    _publish_response(pub, "Okay, cancelled.", transcript, None)
                    route_this = False
                else:
                    # Not a clear yes/no — cancel and route as new command
                    logger.info("Unclear confirmation, routing as new command")

            if not route_this:
                continue

            # ── State: IDLE — route new command ───────────────────────
            logger.info(f"Routing: '{transcript}'")
            match = route_command(transcript)

            if match is None:
                _publish_response(
                    pub,
                    f"Sorry, I didn't understand: {transcript}",
                    transcript,
                    None,
                )
                continue

            label, action, confidence = match
            logger.info(f"Matched '{label}' (confidence: {confidence:.2f})")

            if confidence >= CONFIRM_THRESHOLD:
                # High confidence → execute immediately
                response_text = _execute_action(action)
                _publish_response(pub, response_text, transcript, action["endpoint"])
            else:
                # Low confidence → ask for confirmation
                pending_confirmation = {
                    "label": label,
                    "action": action,
                    "timestamp": time.time(),
                }
                _publish_response(
                    pub,
                    f"Did you mean: {label}? Say yes or no.",
                    transcript,
                    None,
                )
                logger.info(f"Awaiting confirmation for '{label}'")

    finally:
        sub.close()
        pub.close()
        ctx.term()
        logger.info("Voice command router stopped")


if __name__ == "__main__":
    main()
