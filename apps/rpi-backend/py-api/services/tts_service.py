"""
MIA Local TTS Service — on-device text-to-speech via piper-tts.

Subscribes to ZMQ topic 'mia/voice/response' and speaks the text
through the USB audio output using piper-tts (fast, runs on aarch64).

Falls back to espeak if piper-tts is not installed.

Environment variables:
  PIPER_MODEL         — piper voice model (default: en_US-amy-medium)
  PIPER_VOICES        — model per language, "en=en_US-amy-medium,cs=cs_CZ-jirka-medium" (default: English is
                        PIPER_MODEL, Czech is cs_CZ-jirka-medium). A message names a language, never a model, so
                        only the models listed here are ever loaded. A missing model falls back to espeak.
  PIPER_DATA_DIR      — directory for piper models (default: /opt/mia/data/piper)
  ZMQ_RESPONSE_PORT   — SUB port for response text (default: 5561)
  ZMQ_SPEAKING_PORT   — PUB port for "speaking started/finished" events (default: 5563)
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
PIPER_VOICES_SPEC = os.environ.get("PIPER_VOICES", f"en={PIPER_MODEL},cs=cs_CZ-jirka-medium")
PIPER_DATA_DIR = os.environ.get("PIPER_DATA_DIR", "/opt/mia/data/piper")
ZMQ_RESPONSE_PORT = int(os.environ.get("ZMQ_RESPONSE_PORT", "5561"))
ZMQ_SPEAKING_PORT = int(os.environ.get("ZMQ_SPEAKING_PORT", "5563"))
AUDIO_OUTPUT = os.environ.get("AUDIO_OUTPUT_DEVICE", "")

# ── Dependencies ──────────────────────────────────────────────────────────
try:
    import zmq
except ImportError:
    logger.error("pyzmq required"); sys.exit(1)

try:
    from services.voice_fsm.events import FINISHED, STARTED, encode_speaking
except ImportError:  # run without the services package on the path: no events, speech still works
    STARTED, FINISHED, encode_speaking = "started", "finished", None

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

# Speech speed a persona may ask for (piper's length_scale: above 1 is slower).
MIN_LENGTH_SCALE = 0.5
MAX_LENGTH_SCALE = 2.0


def parse_voices(spec: str) -> dict:
    """``"en=model_a,cs=model_b"`` as ``{"en": "model_a", "cs": "model_b"}``; malformed entries are skipped."""
    voices = {}
    for entry in spec.split(","):
        language, _, model = entry.strip().partition("=")
        if language.strip() and model.strip() and "/" not in model and ".." not in model:
            voices[language.strip()] = model.strip()
    return voices


PIPER_VOICES = parse_voices(PIPER_VOICES_SPEC)


def choose_voice(message: dict, voices: dict = None, default_model: str = None):
    """The language, piper model and speed for one response message (ADR-0015).

    The message names a language and a length scale; the model comes only from the allowlist, so a message
    can never make TTS load an arbitrary file. Anything unusable falls back to English at normal speed.
    """
    voices = PIPER_VOICES if voices is None else voices
    default_model = default_model or PIPER_MODEL
    language = message.get("language")
    if not isinstance(language, str) or language not in voices:
        language = "en"
    model = voices.get(language, default_model)
    scale = message.get("length_scale", 1.0)
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        scale = 1.0
    scale = min(MAX_LENGTH_SCALE, max(MIN_LENGTH_SCALE, float(scale)))
    return language, model, scale


def speak_with_piper(text: str, model: str = None, length_scale: float = 1.0) -> bool:
    """Synthesize and play speech using piper-tts."""
    model = model or PIPER_MODEL
    model_path = os.path.join(PIPER_DATA_DIR, f"{model}.onnx")

    if not os.path.exists(model_path):
        logger.warning(f"Piper model not found at {model_path}")
        return False

    try:
        # piper outputs WAV to stdout, pipe to aplay
        aplay_cmd = ["aplay", "-q"]
        if AUDIO_OUTPUT:
            aplay_cmd.extend(["-D", AUDIO_OUTPUT])

        piper_proc = subprocess.Popen(
            [PIPER_BIN, "--model", model_path, "--length_scale", str(length_scale), "--output-raw"],
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


def speak_with_espeak(text: str, language: str = "en", length_scale: float = 1.0) -> bool:
    """Fallback TTS using espeak/espeak-ng."""
    try:
        speed = str(int(160 / length_scale))
        cmd = [ESPEAK_BIN, "-v", language, "-s", speed, "--stdout", text]
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


def speak(text: str, message: dict = None) -> bool:
    """Speak text using the best available TTS engine, in the message's language and speed."""
    language, model, length_scale = choose_voice(message or {})
    if PIPER_BIN:
        if speak_with_piper(text, model, length_scale):
            return True
        logger.warning("Piper failed, falling back to espeak")

    if ESPEAK_BIN:
        return speak_with_espeak(text, language, length_scale)

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

    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://*:{ZMQ_SPEAKING_PORT}")
    logger.info(f"Publishing mia/voice/speaking on port {ZMQ_SPEAKING_PORT}")

    def announce(event: str, ok: bool = True, utterance_id=None) -> None:
        if encode_speaking is not None:
            pub.send_multipart(list(encode_speaking(event, ok, utterance_id=utterance_id)))

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
            utterance_id = msg.get("utterance_id")
            announce(STARTED, utterance_id=utterance_id)
            success = False
            try:
                success = speak(text, msg)
            finally:
                # Always announce the end, or the state machine would wait for it forever.
                announce(FINISHED, success, utterance_id)
            elapsed = int((time.time() - start) * 1000)

            if success:
                logger.info(f"Spoke in {elapsed}ms")
            else:
                logger.warning(f"TTS failed after {elapsed}ms")

    finally:
        sub.close()
        pub.close()
        ctx.term()
        logger.info("TTS service stopped")


if __name__ == "__main__":
    main()
