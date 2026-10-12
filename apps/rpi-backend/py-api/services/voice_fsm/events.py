"""Wire format of the "speaking" events that TTS publishes (REQ-VOICE-016).

TTS tells the rest of the pipeline when MIA starts and stops talking. The state machine needs it to
start the confirmation window only after the announcement, and audio capture needs it to mute the
microphone so MIA does not hear itself.
"""

from __future__ import annotations

import json
import time
from typing import Callable, Optional, Tuple

SPEAKING_TOPIC = b"mia/voice/speaking"
FEEDBACK_TOPIC = b"mia/voice/feedback"

STARTED = "started"
FINISHED = "finished"


def encode_speaking(
    event: str, ok: bool = True, now: Optional[Callable[[], float]] = None
) -> Tuple[bytes, bytes]:
    if event not in (STARTED, FINISHED):
        raise ValueError(f"unknown speaking event: {event}")
    stamp = (now or time.time)()
    return (
        SPEAKING_TOPIC,
        json.dumps({"event": event, "ok": ok, "timestamp": stamp}).encode(),
    )


def decode_speaking(payload: bytes) -> Optional[str]:
    """Return ``started`` or ``finished``, or None if the payload is not a speaking event."""
    try:
        event = json.loads(payload).get("event")
    except (ValueError, AttributeError):
        return None
    return event if event in (STARTED, FINISHED) else None


def encode_feedback(state: str, led: str, tone: str) -> Tuple[bytes, bytes]:
    return (
        FEEDBACK_TOPIC,
        json.dumps({"state": state, "led": led, "tone": tone}).encode(),
    )
