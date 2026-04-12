#!/usr/bin/env python3
"""
mia_voice_bridge.py — Asterisk AGI script
──────────────────────────────────────────
Bridges an active SIP call (via Asterisk) to the MIA WebSocket voice pipeline.
Called by extensions.conf when ElevenLabs delivers an inbound SIP call.

Audio flow:
  Caller ↔ Asterisk (RTP/ulaw) ↔ this AGI ↔ MIA WS (/ws) ↔ AI agent
"""

import asyncio
import os
import sys
import threading
from pathlib import Path

# AGI talks to Asterisk over stdin/stdout
def agi_send(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def agi_recv() -> str:
    return sys.stdin.readline().strip()


def agi_exec(cmd: str) -> str:
    agi_send(cmd)
    return agi_recv()


def agi_get_var(name: str) -> str:
    resp = agi_exec(f"GET VARIABLE {name}")
    # Response: 200 result=1 (value)
    if "result=1" in resp:
        return resp.split("(", 1)[-1].rstrip(")")
    return ""


def agi_say(text: str) -> None:
    # Use SPEECH RECOGNIZE for full duplex — here just log for now
    agi_exec(f"VERBOSE \"{text}\" 1")


class AgiVoiceBridge:
    """
    Reads AGI environment, opens MIA WebSocket, and streams audio bidirectionally.

    TODO (user contribution): Implement the audio streaming loop.
    The bridge receives μ-law 8 kHz PCM from Asterisk via /tmp/ast-audio-{channel}.raw
    and should forward to MIA WS, then play responses back.
    See MIA WS protocol: {"type":"audio","data":"<base64-ulaw>"}
    """

    def __init__(self, called: str, caller: str) -> None:
        self.called = called
        self.caller = caller
        self.mia_ws_url = os.getenv("MIA_WS_URL", "ws://192.168.200.23:8000/ws")

    def run(self) -> None:
        # Read AGI environment headers
        env: dict[str, str] = {}
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break
            if ":" in line:
                k, v = line.split(":", 1)
                env[k.strip()] = v.strip()

        channel = env.get("agi_channel", "unknown")
        agi_exec("ANSWER")
        agi_exec(f'VERBOSE "MIA bridge: {self.caller} → {self.called}" 1')

        # Hand off to async event loop for WS connection
        asyncio.run(self._stream(channel))

    async def _stream(self, channel: str) -> None:
        try:
            import websockets
        except ImportError:
            agi_exec('VERBOSE "websockets not installed — pip install websockets" 1')
            return

        try:
            async with websockets.connect(self.mia_ws_url) as ws:
                await ws.send(__import__("json").dumps({
                    "type": "sip_call",
                    "caller": self.caller,
                    "called": self.called,
                    "channel": channel,
                }))
                # TODO: bidirectional audio streaming loop
                # await asyncio.gather(self._read_rtp(ws), self._write_rtp(ws))
                resp = await asyncio.wait_for(ws.recv(), timeout=300)
                agi_exec(f'VERBOSE "MIA response: {resp[:80]}" 1')
        except Exception as exc:
            agi_exec(f'VERBOSE "MIA WS error: {exc}" 1')


if __name__ == "__main__":
    args = sys.argv[1:]
    called = args[0] if args else ""
    caller = args[1] if len(args) > 1 else ""
    AgiVoiceBridge(called, caller).run()
