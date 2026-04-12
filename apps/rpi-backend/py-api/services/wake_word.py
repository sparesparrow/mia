"""
MIA Wake Word Detector — listens for "Hey Mia" on the audio stream.

Subscribes to ZMQ topic 'mia/audio/raw' (16kHz 16-bit mono PCM),
runs openWakeWord detection, and publishes wake events to
'mia/voice/wake' when the wake phrase is detected.

Uses openWakeWord (Apache-2.0, runs on aarch64, no cloud).
Falls back to simple energy-threshold detection if openWakeWord
is not installed.

Environment variables:
  WAKE_WORD           — wake phrase to detect (default: "hey_mia")
  SENSITIVITY         — detection threshold 0.0-1.0 (default: 0.5)
  ZMQ_AUDIO_PORT      — SUB port for audio stream (default: 5558)
  ZMQ_PUB_PORT        — PUB port for wake events (default: 5559)
"""

import os
import sys
import json
import time
import signal
import logging
import struct
import collections
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [wake-word] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
WAKE_WORD = os.environ.get("WAKE_WORD", "hey_mia")
SENSITIVITY = float(os.environ.get("SENSITIVITY", "0.5"))
ZMQ_AUDIO_PORT = int(os.environ.get("ZMQ_AUDIO_PORT", "5558"))
ZMQ_PUB_PORT = int(os.environ.get("ZMQ_PUB_PORT", "5559"))
SAMPLE_RATE = 16000
CHUNK_SAMPLES = 1280  # 80ms at 16kHz — openWakeWord expects this size

# ── Dependencies ──────────────────────────────────────────────────────────
try:
    import zmq
except ImportError:
    logger.error("pyzmq required"); sys.exit(1)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from openwakeword.model import Model as OWWModel
    OWW_AVAILABLE = True
except ImportError:
    OWW_AVAILABLE = False
    logger.warning("openWakeWord not installed — using energy-based fallback")

running = True


class OpenWakeWordEngine:
    """Real wake word detection using openWakeWord."""

    def __init__(self, wake_word: str, sensitivity: float):
        self.model = OWWModel(
            wakeword_models=[wake_word],
            inference_framework="onnx",
        )
        self.sensitivity = sensitivity
        self.wake_word = wake_word
        logger.info(f"openWakeWord loaded: model='{wake_word}', sensitivity={sensitivity}")

    def process_audio(self, pcm_bytes: bytes) -> float:
        """Process PCM audio, return detection score (0.0-1.0)."""
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        prediction = self.model.predict(audio)
        # openWakeWord returns dict of model_name → score
        scores = prediction.get(self.wake_word, {})
        if isinstance(scores, dict):
            return max(scores.values()) if scores else 0.0
        return float(scores) if scores else 0.0


class EnergyFallbackEngine:
    """Simple energy-threshold wake detection (fallback when openWakeWord unavailable).

    This is NOT real wake word detection — it just detects when someone starts
    speaking loudly. Useful for development and testing.
    """

    def __init__(self, sensitivity: float):
        self.threshold = int(3000 * (1.0 - sensitivity))  # higher sensitivity = lower threshold
        self.consecutive_frames = 0
        self.required_frames = 3  # need 3 loud frames in a row
        logger.info(f"Energy fallback engine: threshold={self.threshold}")

    def process_audio(self, pcm_bytes: bytes) -> float:
        """Return 1.0 if energy burst detected, else 0.0."""
        if not NUMPY_AVAILABLE:
            # Manual RMS calculation
            n_samples = len(pcm_bytes) // 2
            total = 0
            for i in range(n_samples):
                sample = struct.unpack_from('<h', pcm_bytes, i * 2)[0]
                total += abs(sample)
            rms = total / max(n_samples, 1)
        else:
            samples = np.frombuffer(pcm_bytes, dtype=np.int16)
            rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))

        if rms > self.threshold:
            self.consecutive_frames += 1
            if self.consecutive_frames >= self.required_frames:
                self.consecutive_frames = 0
                return 1.0
        else:
            self.consecutive_frames = 0
        return 0.0


def main():
    global running

    def handle_signal(signum, frame):
        global running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("MIA Wake Word Detector starting")
    logger.info(f"  Wake word: {WAKE_WORD}")
    logger.info(f"  Sensitivity: {SENSITIVITY}")

    # Initialize detection engine
    if OWW_AVAILABLE:
        engine = OpenWakeWordEngine(WAKE_WORD, SENSITIVITY)
    else:
        engine = EnergyFallbackEngine(SENSITIVITY)

    # ZMQ sockets
    ctx = zmq.Context()

    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://localhost:{ZMQ_AUDIO_PORT}")
    sub.subscribe(b"mia/audio/raw")
    logger.info(f"Subscribed to mia/audio/raw on port {ZMQ_AUDIO_PORT}")

    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://*:{ZMQ_PUB_PORT}")
    logger.info(f"Publishing wake events on port {ZMQ_PUB_PORT}")

    # Cooldown: don't fire another wake event within 3 seconds
    last_wake_time = 0
    COOLDOWN_SECONDS = 3

    # Audio buffer to accumulate chunks to CHUNK_SAMPLES size
    audio_buffer = bytearray()

    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)

    try:
        while running:
            events = dict(poller.poll(100))
            if sub not in events:
                continue

            topic, pcm_data = sub.recv_multipart()
            audio_buffer.extend(pcm_data)

            # Process when we have enough samples
            chunk_bytes = CHUNK_SAMPLES * 2  # 16-bit = 2 bytes per sample
            while len(audio_buffer) >= chunk_bytes:
                chunk = bytes(audio_buffer[:chunk_bytes])
                del audio_buffer[:chunk_bytes]

                score = engine.process_audio(chunk)

                if score >= SENSITIVITY:
                    now = time.time()
                    if now - last_wake_time >= COOLDOWN_SECONDS:
                        last_wake_time = now
                        wake_event = {
                            "event": "wake_word_detected",
                            "wake_word": WAKE_WORD,
                            "score": round(score, 3),
                            "timestamp": datetime.now().isoformat(),
                        }
                        pub.send_multipart([
                            b"mia/voice/wake",
                            json.dumps(wake_event).encode()
                        ])
                        logger.info(f"Wake word detected! score={score:.3f}")
    finally:
        sub.close()
        pub.close()
        ctx.term()
        logger.info("Wake word detector stopped")


if __name__ == "__main__":
    main()
