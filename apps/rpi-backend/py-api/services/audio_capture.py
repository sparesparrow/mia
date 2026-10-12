"""
MIA Audio Capture Service — microphone input to ZMQ pipeline.

Captures audio from a USB microphone and publishes raw PCM chunks
to ZMQ PUB topic 'mia/audio/raw' for downstream consumers
(wake word detector, VAD, STT).

Audio format: 16kHz, 16-bit mono PCM (optimal for speech recognition).

Environment variables:
  AUDIO_DEVICE_INDEX  — ALSA device index (default: auto-detect USB mic)
  ZMQ_PUB_PORT        — PUB socket port (default: 5558)
  ZMQ_SPEAKING_PORT   — TTS "speaking" events; the microphone is muted while MIA talks (default: 5563)
  CHUNK_DURATION_MS   — audio chunk size in ms (default: 30)
  SAMPLE_RATE         — sample rate in Hz (default: 16000)
"""

import os
import sys
import json
import time
import signal
import logging
import struct
import threading
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [audio-capture] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
SAMPLE_RATE = int(os.environ.get("SAMPLE_RATE", "16000"))
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
CHUNK_DURATION_MS = int(os.environ.get("CHUNK_DURATION_MS", "30"))
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)
ZMQ_PUB_PORT = int(os.environ.get("ZMQ_PUB_PORT", "5558"))
ZMQ_SPEAKING_PORT = int(os.environ.get("ZMQ_SPEAKING_PORT", "5563"))
DEVICE_INDEX = os.environ.get("AUDIO_DEVICE_INDEX", None)
if DEVICE_INDEX is not None:
    DEVICE_INDEX = int(DEVICE_INDEX)

# ── Dependencies ──────────────────────────────────────────────────────────
try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    logger.error("pyzmq not available — cannot publish audio")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice not available — trying pyaudio fallback")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from services.voice_fsm.events import SPEAKING_TOPIC, decode_speaking
    from services.voice_fsm.mic_gate import MicGate
except ImportError:  # run without the services package on the path: no muting
    MicGate = None

running = True

# Closed while MIA speaks (REQ-VOICE-016). None when the gate could not be imported.
mic_gate = MicGate(time.monotonic) if MicGate is not None else None


def gated(pcm: bytes) -> bytes:
    """Silence the frame while MIA is speaking so it does not hear itself."""
    return mic_gate.apply(pcm) if mic_gate is not None else pcm


def listen_for_speaking(ctx):
    """Follow TTS speaking events and drive the gate (runs in a daemon thread)."""
    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://localhost:{ZMQ_SPEAKING_PORT}")
    sub.subscribe(SPEAKING_TOPIC)
    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)
    try:
        while running:
            if sub in dict(poller.poll(200)):
                _, payload = sub.recv_multipart()
                event = decode_speaking(payload)
                if event:
                    mic_gate.on_event(event)
    finally:
        sub.close()


def find_usb_microphone():
    """Auto-detect USB audio input device."""
    if SOUNDDEVICE_AVAILABLE:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and 'usb' in dev['name'].lower():
                logger.info(f"Found USB mic: [{i}] {dev['name']}")
                return i
        # Fallback to default input
        default = sd.default.device[0]
        if default is not None and default >= 0:
            logger.info(f"Using default input device: [{default}]")
            return default
    elif PYAUDIO_AVAILABLE:
        pa = pyaudio.PyAudio()
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0 and 'usb' in info['name'].lower():
                logger.info(f"Found USB mic: [{i}] {info['name']}")
                pa.terminate()
                return i
        pa.terminate()
    return None


def capture_with_sounddevice(pub_socket):
    """Capture audio using sounddevice (preferred)."""
    global running
    device_idx = DEVICE_INDEX if DEVICE_INDEX is not None else find_usb_microphone()

    logger.info(f"Starting sounddevice capture: device={device_idx}, "
                f"rate={SAMPLE_RATE}, chunk={CHUNK_FRAMES} frames ({CHUNK_DURATION_MS}ms)")

    def audio_callback(indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        if not running:
            raise sd.CallbackAbort()
        # indata is numpy float32 array, convert to int16 bytes
        import numpy as np
        pcm_data = gated((indata[:, 0] * 32767).astype(np.int16).tobytes())
        try:
            pub_socket.send_multipart([
                b"mia/audio/raw",
                pcm_data,
            ], zmq.NOBLOCK)
        except zmq.Again:
            pass  # Drop frame if queue is full

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='float32',
        blocksize=CHUNK_FRAMES,
        device=device_idx,
        callback=audio_callback
    ):
        logger.info("Audio capture started")
        while running:
            time.sleep(0.1)


def capture_with_pyaudio(pub_socket):
    """Fallback capture using pyaudio."""
    global running
    device_idx = DEVICE_INDEX if DEVICE_INDEX is not None else find_usb_microphone()

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_idx,
        frames_per_buffer=CHUNK_FRAMES,
    )

    logger.info(f"PyAudio capture started: device={device_idx}, rate={SAMPLE_RATE}")

    try:
        while running:
            pcm_data = gated(stream.read(CHUNK_FRAMES, exception_on_overflow=False))
            try:
                pub_socket.send_multipart([
                    b"mia/audio/raw",
                    pcm_data,
                ], zmq.NOBLOCK)
            except zmq.Again:
                pass
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def capture_simulation(pub_socket):
    """Simulation mode: generate silence frames for development/CI."""
    global running
    silence = b'\x00' * (CHUNK_FRAMES * SAMPLE_WIDTH)
    interval = CHUNK_DURATION_MS / 1000.0

    logger.info(f"SIMULATION: Publishing silence on mia/audio/raw ({CHUNK_DURATION_MS}ms chunks)")
    while running:
        try:
            pub_socket.send_multipart([b"mia/audio/raw", silence], zmq.NOBLOCK)
        except zmq.Again:
            pass
        time.sleep(interval)


def main():
    global running

    def handle_signal(signum, frame):
        global running
        logger.info(f"Signal {signum} received — stopping")
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("MIA Audio Capture starting")
    logger.info(f"  Sample rate: {SAMPLE_RATE} Hz")
    logger.info(f"  Chunk size: {CHUNK_FRAMES} frames ({CHUNK_DURATION_MS}ms)")
    logger.info(f"  ZMQ PUB port: {ZMQ_PUB_PORT}")

    if not ZMQ_AVAILABLE:
        logger.error("Cannot start without pyzmq")
        sys.exit(1)

    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://*:{ZMQ_PUB_PORT}")
    logger.info(f"ZMQ PUB bound on tcp://*:{ZMQ_PUB_PORT}")

    if mic_gate is not None:
        threading.Thread(target=listen_for_speaking, args=(ctx,), daemon=True).start()
        logger.info(f"Microphone muted while MIA speaks (events on port {ZMQ_SPEAKING_PORT})")

    try:
        if SOUNDDEVICE_AVAILABLE:
            try:
                capture_with_sounddevice(pub)
            except Exception as e:
                logger.warning(f"sounddevice capture failed ({e}) — falling back")
                if PYAUDIO_AVAILABLE:
                    capture_with_pyaudio(pub)
                else:
                    logger.warning("No working audio device — running in simulation mode")
                    capture_simulation(pub)
        elif PYAUDIO_AVAILABLE:
            try:
                capture_with_pyaudio(pub)
            except Exception as e:
                logger.warning(f"pyaudio capture failed ({e}) — running in simulation mode")
                capture_simulation(pub)
        else:
            logger.warning("No audio library available — running in simulation mode")
            capture_simulation(pub)
    finally:
        pub.close()
        ctx.term()
        logger.info("Audio capture stopped")


if __name__ == "__main__":
    main()
