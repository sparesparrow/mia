"""Which microphone the pipeline hears: the local device or the phone (ADR-0021, REQ-VOICE-027).

Pure logic with an injected clock, so it needs no ZeroMQ, sound card or sleeping to test. ``audio_capture`` feeds
phone frames in with :meth:`MicSource.push_phone` and asks for the next frame to publish with
:meth:`MicSource.next_frame` once per 30 ms tick (the tick comes from the sound device or, with none, from the
simulation loop, so there is a single pacer). Sources are never mixed.

``AUDIO_SOURCE`` is ``usb`` (local only), ``phone`` (phone only; silence while no frame is there) or ``auto``
(the phone while its last frame is younger than ``FRESH_SEC``, else the local device, else silence).
"""

from __future__ import annotations

import os
import threading
from collections import deque
from typing import Callable, Deque, Optional, Protocol

MODES = ("auto", "usb", "phone")
BUFFER_FRAMES = 10  # about 300 ms; the oldest frame is dropped when it is full
JITTER_FRAMES = 3  # after an underrun, wait for this many frames before playing out again
FRESH_SEC = 0.5
DEFAULT_TAIL_SEC = 0.8


class Gate(Protocol):
    def apply(self, pcm: bytes) -> bytes: ...

    @property
    def is_open(self) -> bool: ...


def source_mode(value: Optional[str] = None) -> str:
    """``AUDIO_SOURCE`` normalised; an unknown value means ``auto``."""
    text = (os.environ.get("AUDIO_SOURCE", "auto") if value is None else value).strip().lower()
    return text if text in MODES else "auto"


def tail_seconds(value: Optional[str] = None) -> float:
    """``MIC_TAIL_SEC``: how long the phone path stays muted after MIA stops speaking."""
    raw = os.environ.get("MIC_TAIL_SEC") if value is None else value
    try:
        tail = float(raw) if raw is not None else DEFAULT_TAIL_SEC
    except ValueError:
        return DEFAULT_TAIL_SEC
    return tail if 0.0 <= tail <= 5.0 else DEFAULT_TAIL_SEC


class MicSource:
    def __init__(
        self,
        mode: str,
        clock: Callable[[], float],
        local_gate: Optional[Gate],
        phone_gate: Optional[Gate],
        frame_bytes: int = 960,
    ) -> None:
        self.mode = mode if mode in MODES else "auto"
        self._clock = clock
        self._local_gate = local_gate
        self._phone_gate = phone_gate
        self._silence = b"\x00" * frame_bytes
        self._lock = threading.Lock()  # the ingest thread pushes, the capture tick pops
        self._frames: Deque[bytes] = deque(maxlen=BUFFER_FRAMES)
        self._last_arrival: Optional[float] = None
        self._primed = False
        self.dropped_overflow = 0
        self.flushed = 0
        self.underruns = 0

    @property
    def wants_phone(self) -> bool:
        return self.mode != "usb"

    def push_phone(self, frame: bytes) -> None:
        with self._lock:
            self._push(frame)

    def _push(self, frame: bytes) -> None:
        if len(self._frames) == BUFFER_FRAMES:
            self.dropped_overflow += 1  # deque drops the oldest
        self._frames.append(frame)
        self._last_arrival = self._clock()

    def phone_fresh(self) -> bool:
        return self._last_arrival is not None and self._clock() - self._last_arrival < FRESH_SEC

    def next_frame(self, local: Optional[bytes]) -> bytes:
        """The frame to publish now, already muted if MIA is speaking. ``local`` is None without a device."""
        with self._lock:
            return self._next(local)

    def _next(self, local: Optional[bytes]) -> bytes:
        if self.mode == "usb" or (self.mode == "auto" and not self.phone_fresh()):
            self._drop_all()
            return self._gated(self._local_gate, local if local is not None else self._silence)
        return self._phone_frame()

    def _phone_frame(self) -> bytes:
        if self._phone_gate is not None and not self._phone_gate.is_open:
            # MIA is speaking (or just did): what the phone sent meanwhile is stale, so it is thrown away.
            self._drop_all()
            return self._silence
        if not self._primed:
            if len(self._frames) < JITTER_FRAMES:
                return self._silence
            self._primed = True
        if not self._frames:
            self.underruns += 1
            self._primed = False
            return self._silence
        return self._frames.popleft()

    def _drop_all(self) -> None:
        if self._frames:
            self.flushed += len(self._frames)
            self._frames.clear()
        self._primed = False

    @staticmethod
    def _gated(gate: Optional[Gate], pcm: bytes) -> bytes:
        return gate.apply(pcm) if gate is not None else pcm
