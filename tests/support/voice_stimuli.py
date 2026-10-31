"""Stimuli for the voice scenarios: what the test does, as opposed to what it watches (REQ-VOICE-028).

Only the stimulus and the tap (``voice_trace``) differ between layers. A target for ``press`` is anything with a
``send_command(command)`` method (see ``voice_rig``). The audio stimuli are for the Pi: ``play_wav`` needs ``aplay``
and an ALSA device, and ``stream_wav_ws`` waits for the /ws/audio endpoint (REQ-VOICE-027).
"""

from __future__ import annotations

import json
import shutil
import subprocess
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
    """Stream a WAV as 30 ms frames to the phone-microphone endpoint (ADR-0021). Not available yet."""
    raise NotImplementedError("/ws/audio does not exist yet; this stimulus arrives with REQ-VOICE-027")
