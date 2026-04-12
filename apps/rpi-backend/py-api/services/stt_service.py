"""
MIA Local STT Service — on-device speech-to-text via faster-whisper.

Subscribes to ZMQ 'mia/voice/wake' events, then captures audio from
'mia/audio/raw' until silence is detected (VAD), and transcribes using
faster-whisper's 'tiny' model (runs on RPi4 in ~2s, no cloud needed).

Publishes transcripts to 'mia/voice/transcript'.

Environment variables:
  WHISPER_MODEL       — model size (default: tiny, options: tiny, base, small)
  WHISPER_LANGUAGE    — language code (default: en)
  MAX_RECORDING_SEC   — max recording duration (default: 10)
  SILENCE_TIMEOUT_MS  — silence duration to end recording (default: 1500)
  ZMQ_WAKE_PORT       — SUB port for wake events (default: 5559)
  ZMQ_AUDIO_PORT      — SUB port for raw audio (default: 5558)
  ZMQ_PUB_PORT        — PUB port for transcripts (default: 5560)
"""

import os
import sys
import io
import json
import time
import signal
import struct
import logging
import tempfile
import wave
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [stt] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "tiny")
WHISPER_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "en")
MAX_RECORDING_SEC = int(os.environ.get("MAX_RECORDING_SEC", "10"))
SILENCE_TIMEOUT_MS = int(os.environ.get("SILENCE_TIMEOUT_MS", "1500"))
ZMQ_WAKE_PORT = int(os.environ.get("ZMQ_WAKE_PORT", "5559"))
ZMQ_AUDIO_PORT = int(os.environ.get("ZMQ_AUDIO_PORT", "5558"))
ZMQ_PUB_PORT = int(os.environ.get("ZMQ_PUB_PORT", "5560"))

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit

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
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed — using mock STT")

running = True


class LocalWhisperSTT:
    """On-device STT using faster-whisper (CTranslate2 backend)."""

    def __init__(self, model_size: str, language: str):
        logger.info(f"Loading faster-whisper model '{model_size}'...")
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",  # ARM-friendly quantization
        )
        self.language = language
        logger.info(f"Whisper model loaded: {model_size} (int8, CPU)")

    def transcribe(self, audio_bytes: bytes) -> dict:
        """Transcribe PCM audio bytes to text."""
        start = time.time()

        # Write PCM to WAV in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_bytes)
        wav_buffer.seek(0)

        # Transcribe
        segments, info = self.model.transcribe(
            wav_buffer,
            language=self.language,
            beam_size=1,
            vad_filter=True,
        )

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        text = " ".join(text_parts)
        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "text": text,
            "language": info.language,
            "confidence": round(1.0 - info.language_probability, 3) if info.language_probability else None,
            "duration_ms": len(audio_bytes) // (SAMPLE_RATE * SAMPLE_WIDTH) * 1000,
            "processing_ms": elapsed_ms,
        }


class MockSTT:
    """Mock STT for development/CI when faster-whisper is not installed."""

    def transcribe(self, audio_bytes: bytes) -> dict:
        duration_ms = len(audio_bytes) // (SAMPLE_RATE * SAMPLE_WIDTH) * 1000
        return {
            "text": "[mock transcript - install faster-whisper for real STT]",
            "language": "en",
            "confidence": 0.0,
            "duration_ms": duration_ms,
            "processing_ms": 0,
        }


def compute_rms(pcm_bytes: bytes) -> float:
    """Compute RMS energy of PCM audio."""
    if NUMPY_AVAILABLE:
        samples = np.frombuffer(pcm_bytes, dtype=np.int16)
        return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    else:
        n = len(pcm_bytes) // 2
        total = sum(abs(struct.unpack_from('<h', pcm_bytes, i * 2)[0]) for i in range(n))
        return total / max(n, 1)


def record_until_silence(audio_sub, poller, max_seconds, silence_timeout_ms):
    """Record audio from ZMQ until silence detected or max time reached."""
    frames = []
    silence_threshold = 500  # RMS below this = silence
    silence_frames = 0
    silence_max = int(silence_timeout_ms / 30)  # ~30ms per chunk
    max_frames = int(max_seconds * SAMPLE_RATE / 480)  # ~480 samples per 30ms chunk
    frame_count = 0

    logger.info(f"Recording (max {max_seconds}s, silence timeout {silence_timeout_ms}ms)...")

    while running and frame_count < max_frames:
        events = dict(poller.poll(100))
        if audio_sub not in events:
            continue

        topic, pcm_data = audio_sub.recv_multipart()
        if topic != b"mia/audio/raw":
            continue

        frames.append(pcm_data)
        frame_count += 1

        rms = compute_rms(pcm_data)
        if rms < silence_threshold:
            silence_frames += 1
            if silence_frames >= silence_max:
                logger.info(f"Silence detected after {frame_count} frames")
                break
        else:
            silence_frames = 0

    audio_bytes = b"".join(frames)
    logger.info(f"Recorded {len(audio_bytes)} bytes ({len(audio_bytes) / (SAMPLE_RATE * SAMPLE_WIDTH):.1f}s)")
    return audio_bytes


def main():
    global running

    def handle_signal(signum, frame):
        global running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("MIA Local STT Service starting")
    logger.info(f"  Model: {WHISPER_MODEL}")
    logger.info(f"  Language: {WHISPER_LANGUAGE}")

    # Initialize STT engine
    if WHISPER_AVAILABLE:
        stt = LocalWhisperSTT(WHISPER_MODEL, WHISPER_LANGUAGE)
    else:
        stt = MockSTT()

    # ZMQ sockets
    ctx = zmq.Context()

    wake_sub = ctx.socket(zmq.SUB)
    wake_sub.connect(f"tcp://localhost:{ZMQ_WAKE_PORT}")
    wake_sub.subscribe(b"mia/voice/wake")
    logger.info(f"Subscribed to mia/voice/wake on port {ZMQ_WAKE_PORT}")

    audio_sub = ctx.socket(zmq.SUB)
    audio_sub.connect(f"tcp://localhost:{ZMQ_AUDIO_PORT}")
    audio_sub.subscribe(b"mia/audio/raw")

    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://*:{ZMQ_PUB_PORT}")
    logger.info(f"Publishing transcripts on port {ZMQ_PUB_PORT}")

    wake_poller = zmq.Poller()
    wake_poller.register(wake_sub, zmq.POLLIN)

    audio_poller = zmq.Poller()
    audio_poller.register(audio_sub, zmq.POLLIN)

    try:
        while running:
            # Wait for wake word event
            events = dict(wake_poller.poll(200))
            if wake_sub not in events:
                continue

            topic, wake_data = wake_sub.recv_multipart()
            wake_event = json.loads(wake_data)
            logger.info(f"Wake event received: {wake_event.get('wake_word')}")

            # Record audio until silence
            audio_bytes = record_until_silence(
                audio_sub, audio_poller,
                MAX_RECORDING_SEC, SILENCE_TIMEOUT_MS
            )

            if len(audio_bytes) < SAMPLE_RATE * SAMPLE_WIDTH * 0.3:  # < 0.3s = too short
                logger.info("Recording too short, skipping")
                continue

            # Transcribe
            result = stt.transcribe(audio_bytes)
            text = result.get("text", "").strip()

            if not text or text.startswith("["):
                logger.info(f"Empty/mock transcript, skipping: '{text}'")
                continue

            # Publish transcript
            transcript_event = {
                "event": "transcript",
                "text": text,
                "language": result.get("language", WHISPER_LANGUAGE),
                "confidence": result.get("confidence"),
                "audio_duration_ms": result.get("duration_ms"),
                "processing_ms": result.get("processing_ms"),
                "wake_word": wake_event.get("wake_word"),
                "timestamp": datetime.now().isoformat(),
            }
            pub.send_multipart([
                b"mia/voice/transcript",
                json.dumps(transcript_event).encode()
            ])
            logger.info(f"Transcript: '{text}' ({result.get('processing_ms')}ms)")

    finally:
        wake_sub.close()
        audio_sub.close()
        pub.close()
        ctx.term()
        logger.info("STT service stopped")


if __name__ == "__main__":
    main()
