#!/usr/bin/env python3
"""
rezervace_local.py — lokální simulace hovoru přes M-Audio MobilePre
────────────────────────────────────────────────────────────────────
ElevenLabs Conversational AI WebSocket + mikrofon + headphones.
Bez telefonního hovoru — agent mluví do sluchátek, ty odpovídáš jako recepce chatky.

Spuštění:
    python rezervace_local.py

Ovládání:
    Ctrl+C  — ukončení
"""

import asyncio
import base64
import json
import os
import sys

import numpy as np
import requests
import sounddevice as sd
import websockets

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    BOOKING_DATE, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    GUEST_COUNT, SYSTEM_PROMPT, FIRST_MESSAGE,
)

# ── Audio ──────────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 48000    # M-Audio MobilePre native
EL_RATE        = 16000    # ElevenLabs ASR input rate
CHUNK_MS       = 100
CHUNK_SAMPLES  = int(SAMPLE_RATE * CHUNK_MS / 1000)
EL_CHUNK       = int(EL_RATE    * CHUNK_MS / 1000)

EL_BASE = "https://api.elevenlabs.io/v1"


# ── Helpers ────────────────────────────────────────────────────────────────────

def el_headers():
    return {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}


def resample(audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    if from_rate == to_rate:
        return audio
    new_len = int(len(audio) * to_rate / from_rate)
    return np.interp(
        np.linspace(0, len(audio) - 1, new_len),
        np.arange(len(audio)),
        audio.astype(np.float64),
    ).astype(np.int16)


def float32_to_pcm16(data: np.ndarray) -> np.ndarray:
    mono = data[:, 0] if data.ndim > 1 else data.flatten()
    return (mono * 32767).clip(-32768, 32767).astype(np.int16)


def b64_to_pcm16(b64: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(b64), dtype=np.int16)


# ── ElevenLabs agent setup ─────────────────────────────────────────────────────

def create_agent() -> str:
    r = requests.post(f"{EL_BASE}/convai/agents/create", headers=el_headers(), json={
        "name": f"SimulaceChatka-{BOOKING_DATE}",
        "conversation_config": {
            "agent": {
                "prompt": {"prompt": SYSTEM_PROMPT, "llm": "gpt-4o", "temperature": 0.4},
                "first_message": FIRST_MESSAGE,
                "language": "cs",
            },
            "tts": {"voice_id": ELEVENLABS_VOICE_ID, "model_id": "eleven_turbo_v2_5"},
            "asr": {"quality": "high", "provider": "elevenlabs", "user_input_audio_format": "pcm_16000"},
            "turn": {"turn_timeout": 10, "silence_end_call_timeout": 60},
        },
    }, timeout=20)
    r.raise_for_status()
    aid = r.json()["agent_id"]
    print(f"[Agent] {aid}")
    return aid


def get_signed_url(agent_id: str) -> str:
    r = requests.get(
        f"{EL_BASE}/convai/conversation/get-signed-url",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        params={"agent_id": agent_id},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["signed_url"]


def delete_agent(agent_id: str):
    requests.delete(f"{EL_BASE}/convai/agents/{agent_id}", headers=el_headers(), timeout=10)
    print(f"[Agent smazán]")


# ── Playback ───────────────────────────────────────────────────────────────────

class AudioPlayer:
    def __init__(self):
        self._q: asyncio.Queue = asyncio.Queue()
        self.speaking = False

    def enqueue(self, pcm_el: np.ndarray):
        pcm48 = resample(pcm_el, EL_RATE, SAMPLE_RATE)
        self._q.put_nowait(pcm48)

    async def drain(self):
        loop = asyncio.get_event_loop()
        while True:
            chunk = await self._q.get()
            self.speaking = True
            await loop.run_in_executor(None, lambda c=chunk: sd.play(c, samplerate=SAMPLE_RATE, blocking=True))
            if self._q.empty():
                self.speaking = False

    @property
    def busy(self):
        return self.speaking or not self._q.empty()


# ── Main ───────────────────────────────────────────────────────────────────────

async def run():
    player = AudioPlayer()
    mic_q: asyncio.Queue = asyncio.Queue(maxsize=40)
    stop = asyncio.Event()

    def mic_cb(indata, frames, t, status):
        pcm16 = float32_to_pcm16(indata)
        pcm_el = resample(pcm16, SAMPLE_RATE, EL_RATE)
        try:
            mic_q.put_nowait(pcm_el)
        except asyncio.QueueFull:
            pass

    print("━" * 58)
    print("  SIMULACE HOVORU — M-Audio MobilePre")
    print("━" * 58)
    print(f"  Hlas:   Hana [CZ]")
    print(f"  Datum:  {BOOKING_DATE}  |  Hosté: {GUEST_COUNT}")
    print(f"\n  Agent mluví do sluchátek.")
    print(f"  Ty odpovídáš jako recepce chatky.")
    print(f"  Ukončení: Ctrl+C\n")

    agent_id = create_agent()
    ws_url   = get_signed_url(agent_id)

    try:
        async with websockets.connect(ws_url) as ws:
            print("[Připojeno]\n")
            asyncio.create_task(player.drain())

            async def send_mic():
                while not stop.is_set():
                    try:
                        chunk = await asyncio.wait_for(mic_q.get(), timeout=0.15)
                        if not player.busy:
                            await ws.send(json.dumps({
                                "user_audio_chunk": base64.b64encode(chunk.tobytes()).decode(),
                            }))
                    except asyncio.TimeoutError:
                        continue
                    except Exception:
                        break

            async def recv():
                async for raw in ws:
                    msg = json.loads(raw)
                    t = msg.get("type", "")

                    if t == "audio":
                        b64 = msg.get("audio_event", {}).get("audio_base_64", "")
                        if b64:
                            player.enqueue(b64_to_pcm16(b64))

                    elif t == "agent_response":
                        text = msg.get("agent_response_event", {}).get("agent_response", "")
                        if text:
                            print(f"\033[96m[AGENT]\033[0m {text}")

                    elif t == "user_transcript":
                        text = msg.get("user_transcription_event", {}).get("user_transcript", "")
                        if text:
                            print(f"\033[93m[TY]   \033[0m {text}")

                    elif t == "interruption":
                        print("\033[90m[přerušeno]\033[0m")

                    elif t == "conversation_initiation_metadata":
                        cid = msg.get("conversation_initiation_metadata_event", {}).get("conversation_id", "")
                        print(f"[session: {cid}]\n")

                    elif t == "ping":
                        await ws.send(json.dumps({
                            "type": "pong",
                            "event_id": msg.get("ping_event", {}).get("event_id"),
                        }))

            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                blocksize=CHUNK_SAMPLES, callback=mic_cb):
                try:
                    await asyncio.gather(send_mic(), recv())
                except websockets.exceptions.ConnectionClosed:
                    print("\n[Hovor ukončen]")
                finally:
                    stop.set()

    finally:
        delete_agent(agent_id)


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nSimulace ukončena.")


if __name__ == "__main__":
    main()
