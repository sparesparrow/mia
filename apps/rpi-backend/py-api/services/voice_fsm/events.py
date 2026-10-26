"""Wire format of the "speaking" events that TTS publishes (REQ-VOICE-016).

TTS tells the rest of the pipeline when MIA starts and stops talking. The state machine needs it to
start the confirmation window only after the announcement, and audio capture needs it to mute the
microphone so MIA does not hear itself. Each event carries the ``utterance_id`` the router sent with the
text, so a "finished" from an utterance that was stopped can be told from one that really finished.
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
    event: str,
    ok: bool = True,
    now: Optional[Callable[[], float]] = None,
    utterance_id: Optional[int] = None,
) -> Tuple[bytes, bytes]:
    if event not in (STARTED, FINISHED):
        raise ValueError(f"unknown speaking event: {event}")
    body = {"event": event, "ok": ok, "timestamp": (now or time.time)()}
    if utterance_id is not None:
        body["utterance_id"] = utterance_id
    return SPEAKING_TOPIC, json.dumps(body).encode()


def decode_speaking_event(payload: bytes) -> Optional[Tuple[str, Optional[int]]]:
    """Return ``(event, utterance_id)``, or None if the payload is not a speaking event."""
    try:
        body = json.loads(payload)
        event = body.get("event")
        utterance_id = body.get("utterance_id")
    except (ValueError, AttributeError):
        return None
    if event not in (STARTED, FINISHED):
        return None
    return event, utterance_id if isinstance(utterance_id, int) else None


def decode_speaking(payload: bytes) -> Optional[str]:
    """Return ``started`` or ``finished``, or None if the payload is not a speaking event."""
    decoded = decode_speaking_event(payload)
    return decoded[0] if decoded else None


def encode_feedback(state: str, led: str, tone: str) -> Tuple[bytes, bytes]:
    return (
        FEEDBACK_TOPIC,
        json.dumps({"state": state, "led": led, "tone": tone}).encode(),
    )


def feedback_frames(feedback) -> Tuple[bytes, bytes]:
    """A machine ``Feedback`` effect as topic and payload. Its ``state`` is already the plain name."""
    return encode_feedback(feedback.state, feedback.led, feedback.tone)
