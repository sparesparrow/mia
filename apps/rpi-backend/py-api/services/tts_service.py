"""
MIA Local TTS Service — on-device text-to-speech via piper-tts.

Subscribes to ZMQ topic 'mia/voice/response' and speaks the text
through the USB audio output using piper-tts (fast, runs on aarch64).

Falls back to espeak if piper-tts is not installed.

Environment variables:
  PIPER_MODEL         — piper voice model (default: en_US-amy-medium)
  PIPER_DATA_DIR      — directory for piper models (default: /opt/mia/data/piper)
  ZMQ_RESPONSE_PORT   — SUB port for response text (default: 5561)
  AUDIO_OUTPUT_DEVICE — ALSA device for playback (default: auto)
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
import tempfile
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [tts] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
PIPER_MODEL = os.environ.get("PIPER_MODEL", "en_US-amy-medium")
PIPER_DATA_DIR = os.environ.get("PIPER_DATA_DIR", "/opt/mia/data/piper")
ZMQ_RESPONSE_PORT = int(os.environ.get("ZMQ_RESPONSE_PORT", "5561"))
AUDIO_OUTPUT = os.environ.get("AUDIO_OUTPUT_DEVICE", "")

# ── Dependencies ──────────────────────────────────────────────────────────
try:
    import zmq
except ImportError:
    logger.error("pyzmq required"); sys.exit(1)

# Check for piper-tts binary
PIPER_BIN = None
for path in ["/usr/bin/piper", "/usr/local/bin/piper", os.path.expanduser("~/.local/bin/piper")]:
    if os.path.isfile(path) and os.access(path, os.X_OK):
        PIPER_BIN = path
        break

# Check for espeak as fallback
ESPEAK_BIN = None
for name in ["espeak-ng", "espeak"]:
    try:
        subprocess.run([name, "--version"], capture_output=True, timeout=5)
        ESPEAK_BIN = name
        break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        continue

running = True


def speak_with_piper(text: str) -> bool:
    """Synthesize and play speech using piper-tts."""
    model_path = os.path.join(PIPER_DATA_DIR, f"{PIPER_MODEL}.onnx")
    config_path = os.path.join(PIPER_DATA_DIR, f"{PIPER_MODEL}.onnx.json")

    if not os.path.exists(model_path):
        logger.warning(f"Piper model not found at {model_path}")
        return False

    try:
        # piper outputs WAV to stdout, pipe to aplay
        aplay_cmd = ["aplay", "-q"]
        if AUDIO_OUTPUT:
            aplay_cmd.extend(["-D", AUDIO_OUTPUT])

        piper_proc = subprocess.Popen(
            [PIPER_BIN, "--model", model_path, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        aplay_proc = subprocess.Popen(
            aplay_cmd + ["-r", "22050", "-f", "S16_LE", "-t", "raw", "-c", "1"],
            stdin=piper_proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        piper_proc.stdin.write(text.encode('utf-8'))
        piper_proc.stdin.close()
        piper_proc.stdout.close()
        aplay_proc.wait(timeout=30)
        piper_proc.wait(timeout=5)
        return True
    except Exception as e:
        logger.error(f"Piper TTS error: {e}")
        return False


def speak_with_espeak(text: str) -> bool:
    """Fallback TTS using espeak/espeak-ng."""
    try:
        cmd = [ESPEAK_BIN, "-s", "160", "--stdout", text]
        espeak_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        aplay_cmd = ["aplay", "-q"]
        if AUDIO_OUTPUT:
            aplay_cmd.extend(["-D", AUDIO_OUTPUT])
        aplay_proc = subprocess.Popen(
            aplay_cmd,
            stdin=espeak_proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        espeak_proc.stdout.close()
        aplay_proc.wait(timeout=30)
        espeak_proc.wait(timeout=5)
        return True
    except Exception as e:
        logger.error(f"eSpeak TTS error: {e}")
        return False


def speak(text: str) -> bool:
    """Speak text using the best available TTS engine."""
    if PIPER_BIN:
        if speak_with_piper(text):
            return True
        logger.warning("Piper failed, falling back to espeak")

    if ESPEAK_BIN:
        return speak_with_espeak(text)

    logger.warning(f"No TTS engine available — would say: '{text}'")
    return False


def main():
    global running

    def handle_signal(signum, frame):
        global running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("MIA Local TTS Service starting")
    logger.info(f"  Piper: {'available' if PIPER_BIN else 'not found'}")
    logger.info(f"  eSpeak: {'available' if ESPEAK_BIN else 'not found'}")
    logger.info(f"  Model: {PIPER_MODEL}")

    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://localhost:{ZMQ_RESPONSE_PORT}")
    sub.subscribe(b"mia/voice/response")
    logger.info(f"Subscribed to mia/voice/response on port {ZMQ_RESPONSE_PORT}")

    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)

    try:
        while running:
            events = dict(poller.poll(200))
            if sub not in events:
                continue

            topic, msg_data = sub.recv_multipart()
            msg = json.loads(msg_data)
            text = msg.get("text", "")

            if not text:
                continue

            logger.info(f"Speaking: '{text[:60]}{'...' if len(text) > 60 else ''}'")
            start = time.time()
            success = speak(text)
            elapsed = int((time.time() - start) * 1000)

            if success:
                logger.info(f"Spoke in {elapsed}ms")
            else:
                logger.warning(f"TTS failed after {elapsed}ms")

    finally:
        sub.close()
        ctx.term()
        logger.info("TTS service stopped")


if __name__ == "__main__":
    main()
