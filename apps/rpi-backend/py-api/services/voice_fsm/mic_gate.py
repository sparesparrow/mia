"""Mute the microphone while MIA speaks (REQ-VOICE-016).

Closed frames become silence of the same length rather than being dropped, so downstream timing,
voice activity detection and the wake word keep working and simply hear nothing. A short tail after
the speech ends covers the room echo.
"""

from __future__ import annotations

import threading
from typing import Callable

from .events import FINISHED, STARTED


class MicGate:
    def __init__(self, clock: Callable[[], float], tail_sec: float = 0.3) -> None:
        self._clock = clock
        self._tail_sec = tail_sec
        self._lock = threading.Lock()
        self._speaking = False
        self._open_at = 0.0

    def on_event(self, event: str) -> None:
        with self._lock:
            if event == STARTED:
                self._speaking = True
            elif event == FINISHED:
                self._speaking = False
                self._open_at = self._clock() + self._tail_sec

    @property
    def is_open(self) -> bool:
        with self._lock:
            return not self._speaking and self._clock() >= self._open_at

    def apply(self, pcm: bytes) -> bytes:
        return pcm if self.is_open else b"\x00" * len(pcm)
