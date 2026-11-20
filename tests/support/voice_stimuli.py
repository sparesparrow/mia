"""Stimuli for the voice scenarios: what the test does, as opposed to what it watches (REQ-VOICE-028).

Only the stimulus and the tap (``voice_trace``) differ between layers. A target for ``press`` is anything with a
``send_command(command)`` method (see ``voice_rig``). The audio stimuli are for the Pi: ``play_wav`` needs ``aplay``
and an ALSA device, and ``stream_wav_ws`` sends microphone-format frames to a live Pi (REQ-VOICE-027).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import wave
from pathlib import Path
from typing import Any, Dict, Optional

BUTTONS = ("Wake", "GoNow", "Cancel", "Confirm", "Deny", "EndDictation")
TRANSCRIPT_TOPIC = b"mia/voice/transcript"


def button_command(button: str) -> Any:
    """The machine command for a button name; the channel stamps the source, so the default one is fine."""
    from services.voice_fsm import Cancel, Confirm, Deny, EndDictation, GoNow, Wake

    commands = {
        "Wake": Wake,
        "GoNow": GoNow,
        "Cancel": Cancel,
        "Confirm": Confirm,
        "Deny": Deny,
        "EndDictation": EndDictation,
    }
    if button not in commands:
        raise ValueError(f"unknown button {button!r}; one of {BUTTONS}")
    return commands[button]()


def press(target: Any, button: str) -> None:
    """Press a button: Wake, GoNow, Cancel, Confirm, Deny or EndDictation."""
    target.send_command(button_command(button))


def inject_transcript(socket: Any, text: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Publish a recognised utterance as stt_service would: ``mia/voice/transcript`` {"text": ...}.

    ``socket`` is a ZeroMQ PUB socket bound by the test (the router connects to it in the layer that runs
    the router). No audio, no speech recognition involved.
    """
    body: Dict[str, Any] = {"event": "transcript", "text": text}
    body.update(extra or {})
    socket.send_multipart([TRANSCRIPT_TOPIC, json.dumps(body).encode()])


def play_wav(path: str, device: str) -> subprocess.CompletedProcess:
    """Play a WAV into an ALSA device with ``aplay`` (Pi only; e.g. ``plughw:Loopback,0,0`` of snd-aloop).

    Blocks until the file has been played. Raises RuntimeError where ``aplay`` is missing, FileNotFoundError for
    a missing file and CalledProcessError when ``aplay`` fails.
    """
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    aplay = shutil.which("aplay")
    if aplay is None:
        raise RuntimeError("aplay is not installed (alsa-utils); play_wav runs on the Pi only")
    return subprocess.run([aplay, "-q", "-D", device, str(path)], check=True, timeout=60)


def stream_wav_ws(path: str, url: str) -> None:
    """Stream a 16 kHz mono PCM16 WAV to ``/ws/audio`` in real-time 30 ms frames (ADR-0021)."""
    if not Path(path).is_file():
        raise FileNotFoundError(path)

    with wave.open(path, "rb") as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth(), audio.getcomptype()) != (
            16000,
            1,
            2,
            "NONE",
        ):
            raise ValueError("phone microphone WAV must be uncompressed 16 kHz mono PCM16")

        try:
            from websockets.sync.client import connect
        except ImportError as exc:
            raise RuntimeError("websockets 12.0 is required for phone microphone stimuli") from exc

        key = os.environ.get("MIA_API_KEY", "").strip()
        headers = {"X-API-Key": key} if key else {}
        with connect(url, extra_headers=headers, open_timeout=5, close_timeout=2) as socket:
            socket.send(json.dumps({"v": 1, "fmt": "s16le", "rate": 16000, "ch": 1, "frame_ms": 30}))
            try:
                acknowledgement = json.loads(socket.recv(timeout=5))
            except (TimeoutError, json.JSONDecodeError) as exc:
                raise RuntimeError("Pi did not acknowledge the phone microphone format") from exc
            if acknowledgement.get("ok") is not True:
                raise RuntimeError("Pi refused the phone microphone format")

            frame_bytes = 960
            interval = 0.03
            next_frame_at = time.monotonic()
            while True:
                frame = audio.readframes(frame_bytes // 2)
                if not frame:
                    break
                if len(frame) < frame_bytes:
                    frame += b"\x00" * (frame_bytes - len(frame))
                socket.send(frame)
                next_frame_at += interval
                time.sleep(max(0.0, next_frame_at - time.monotonic()))
