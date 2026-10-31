"""The voice service of the router process: the console talks to the machine the router runs (ADR-0020).

``VoiceService`` owns a machine and ticks it. In the router the machine belongs to ``RouterBridge``, which
already ticks it, speaks, executes and publishes. ``BridgeVoiceService`` therefore does not touch the machine:

- a permitted console command goes through ``bridge.submit`` (applied once, with the bridge's side effects);
- every effect and transcript, whatever started it, reaches the bridge's observers; they are encoded into a
  pending list that ``tick()`` hands to the envelope router for broadcast, so every console sees all of them;
- ``tick()`` never advances the machine (the router loop calls ``bridge.poll()`` itself), so there is no second tick.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import List, Sequence

from ..bridge import Observed, RouterBridge
from ..types import Command, Speak
from .codec import encode_event
from .router import PEER_COMMANDS, VoiceService

logger = logging.getLogger(__name__)


class BridgeVoiceService(VoiceService):
    def __init__(self, bridge: RouterBridge, **kwargs) -> None:
        super().__init__(bridge.machine, **kwargs)
        self.bridge = bridge
        self._pending: List[bytes] = []
        bridge.observers.append(self._observe)

    def _observe(self, items: Sequence[Observed]) -> None:
        for item in items:
            if isinstance(item, Speak):
                # The words in the persona and language in use now, so a console shows the sentence.
                item = dataclasses.replace(item, text=self.bridge.render(item))
            payload = encode_event(item)
            if payload is not None:
                self._pending.append(payload)

    def drain(self) -> List[bytes]:
        pending, self._pending = self._pending, []
        return pending

    def submit(self, command: Command) -> List[bytes]:
        self.bridge.submit(command)
        return self.drain()

    def tick(self) -> List[bytes]:
        """Events that came from outside the console (speech, TTS, the clock) since the last call."""
        return self.drain()


__all__ = ["BridgeVoiceService", "PEER_COMMANDS"]
