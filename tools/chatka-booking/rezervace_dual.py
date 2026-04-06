#!/usr/bin/env python3
"""
rezervace_dual.py — dual-endpoint simulace telefonního hovoru
──────────────────────────────────────────────────────────────
Oba aktéři hovorů hrají přes stejné M-Audio audio zařízení:
  - Caller (náš booking agent)
  - Target (recepce chatky)

Módy:
  --mode espeak   oba actori = espeak, nulové náklady (test audio routing)
  --mode hybrid   caller = ElevenLabs, target = espeak       [default]
  --mode full     oba actori = ElevenLabs                    [drahé]

Ovládání: Ctrl+C ukončí simulaci.
"""

import argparse
import asyncio
import base64
import io
import json
import os
import signal
import sys
import wave

import numpy as np
import requests
import sounddevice as sd
import websockets

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    BOOKING_DATE, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    GUEST_COUNT, SYSTEM_PROMPT, FIRST_MESSAGE,
)
from target_espeak import EspeakTarget, synth as espeak_synth
from target_llm import LLMTarget

# ── Audio ──────────────────────────────────────────────────────────────────────
# ElevenLabs native rate — skip resample entirely, play/capture at 16kHz
SAMPLE_RATE   = 16000
EL_RATE       = 16000
CHUNK_MS      = 250                                    # bigger chunks → fewer WS sends
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)

EL_BASE = "https://api.elevenlabs.io/v1"

# Caller espeak voice (mode=espeak): jiný hlas/rychlost aby se lišil od target
CALLER_ESPEAK_TEXT_PREFIX = []  # plněno za běhu


# ── Helpers ────────────────────────────────────────────────────────────────────

def el_headers():
    return {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}


def resample(pcm: np.ndarray, from_r: int, to_r: int) -> np.ndarray:
    if from_r == to_r:
        return pcm
    n = int(len(pcm) * to_r / from_r)
    return np.interp(np.linspace(0, len(pcm)-1, n), np.arange(len(pcm)),
                     pcm.astype(np.float64)).astype(np.int16)


def float32_to_pcm16(data: np.ndarray) -> np.ndarray:
    mono = data[:, 0] if data.ndim > 1 else data.flatten()
    return (mono * 32767).clip(-32768, 32767).astype(np.int16)


def b64_to_pcm16(b64: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(b64), dtype=np.int16)


# ── Shared audio state ─────────────────────────────────────────────────────────

class AudioBus:
    """Serializovaný výstup zvuku + sdílený příznak kdo mluví."""
    def __init__(self):
        self._out_q: asyncio.Queue = asyncio.Queue()
        self.speaking: str | None = None   # "caller" | "target" | None
        self._lock = asyncio.Lock()

    async def play(self, pcm48: np.ndarray, who: str):
        """Zablokuje ostatní, přehraje audio, uvolní."""
        async with self._lock:
            self.speaking = who
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: sd.play(pcm48, samplerate=SAMPLE_RATE, blocking=True)
            )
            self.speaking = None

    @property
    def busy(self):
        return self.speaking is not None


# ── ElevenLabs agent ───────────────────────────────────────────────────────────

def el_create_agent() -> str:
    r = requests.post(f"{EL_BASE}/convai/agents/create", headers=el_headers(), json={
        "name": f"DualSim-Caller",
        "conversation_config": {
            "agent": {
                "prompt": {"prompt": SYSTEM_PROMPT, "llm": "gpt-4o-mini",
                           "temperature": 0.8, "max_tokens": 80},
                "first_message": FIRST_MESSAGE,
                "language": "cs",
            },
            "tts": {
                "voice_id": ELEVENLABS_VOICE_ID,
                "model_id": "eleven_flash_v2_5",
                "optimize_streaming_latency": 4,       # max latency reduction
                "output_format": "pcm_16000",          # native → no transcode
            },
            "asr": {"quality": "high", "provider": "elevenlabs",
                    "user_input_audio_format": "pcm_16000"},
            "turn": {"turn_timeout": 5, "silence_end_call_timeout": 20},
        },
    }, timeout=20)
    r.raise_for_status()
    aid = r.json()["agent_id"]
    _agents_to_cleanup.append(aid)
    print(f"[EL agent] {aid}")
    return aid


def el_signed_url(agent_id: str) -> str:
    r = requests.get(f"{EL_BASE}/convai/conversation/get-signed-url",
                     headers={"xi-api-key": ELEVENLABS_API_KEY},
                     params={"agent_id": agent_id}, timeout=10)
    r.raise_for_status()
    return r.json()["signed_url"]


_agents_to_cleanup: list[str] = []   # track all created agents for SIGTERM cleanup


def el_delete_agent(agent_id: str):
    try:
        requests.delete(f"{EL_BASE}/convai/agents/{agent_id}", headers=el_headers(), timeout=10)
        print(f"[EL agent smazán: {agent_id}]")
        if agent_id in _agents_to_cleanup:
            _agents_to_cleanup.remove(agent_id)
    except Exception as e:
        print(f"[WARN] Nelze smazat agenta {agent_id}: {e}")


def _cleanup_all_agents(signum=None, frame=None):
    """SIGINT/SIGTERM handler — smaže všechny EL agenty před ukončením."""
    for aid in list(_agents_to_cleanup):
        el_delete_agent(aid)
    sys.exit(0)


# ── Mode: espeak (oba lokální) ─────────────────────────────────────────────────

CALLER_SCRIPT = [
    f"Dobrý den, volám ohledně rezervace chatky na {BOOKING_DATE}. Jsem AI asistent. Máte volno?",
    f"Kolik stojí jedna noc a jaká je minimální délka pobytu?",
    f"Jsme čtyři dospělí, vejdeme se?",
    f"Jak probíhá potvrzení rezervace a jaká je záloha?",
    f"Jaké jsou storno podmínky?",
    f"Děkuji, zákazník vám pošle e-mail pro potvrzení. Na shledanou.",
]


async def run_espeak_mode(bus: AudioBus):
    """Oba actori = espeak, střídají se. Ověří audio routing bez nákladů."""
    target = EspeakTarget(SAMPLE_RATE)

    for caller_line in CALLER_SCRIPT:
        # Caller promluví
        print(f"\033[96m[CALLER]\033[0m {caller_line}")
        pcm = espeak_synth(caller_line, SAMPLE_RATE)
        if len(pcm):
            await bus.play(pcm, "caller")
        await asyncio.sleep(0.3)

        # Target odpoví
        if target.has_next():
            pcm_t = target.next_turn()
            if len(pcm_t):
                await bus.play(pcm_t, "target")
            await asyncio.sleep(0.3)

    print("\n[Simulace dokončena]")


# ── Mode: hybrid (caller=EL, target=espeak) ────────────────────────────────────

async def run_hybrid_mode(bus: AudioBus):
    target   = LLMTarget(EL_RATE)   # Groq + espeak @ 16kHz — dynamické odpovědi
    agent_id = el_create_agent()
    ws_url   = el_signed_url(agent_id)

    mic_q: asyncio.Queue = asyncio.Queue(maxsize=50)
    stop   = asyncio.Event()

    def mic_cb(indata, frames, t, status):
        pcm = float32_to_pcm16(indata)
        pcm_el = resample(pcm, SAMPLE_RATE, EL_RATE)
        if not bus.busy:          # posílej mic jen když nikdo nemluví
            try:
                mic_q.put_nowait(pcm_el)
            except asyncio.QueueFull:
                pass

    try:
        async with websockets.connect(ws_url) as ws:
            print("[EL připojeno]\n")

            async def send_mic():
                while not stop.is_set():
                    try:
                        chunk = await asyncio.wait_for(mic_q.get(), timeout=0.15)
                        if not bus.busy:
                            await ws.send(json.dumps({
                                "user_audio_chunk": base64.b64encode(chunk.tobytes()).decode()
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
                            pcm = b64_to_pcm16(b64)
                            pcm48 = resample(pcm, EL_RATE, SAMPLE_RATE)
                            await bus.play(pcm48, "caller")

                    elif t == "agent_response":
                        text = msg.get("agent_response_event", {}).get("agent_response", "")
                        if text:
                            print(f"\033[96m[CALLER]\033[0m {text}")
                            await asyncio.sleep(0.3)

                            # Dynamická odpověď recepce (Groq + espeak)
                            _, pcm_t48 = await target.respond(text)
                            if not len(pcm_t48):
                                continue

                            # 1) Přehraj do sluchátek (pro monitoring)
                            asyncio.create_task(bus.play(pcm_t48, "target"))

                            # 2) Digitální routing přímo do EL WS (16kHz == EL_RATE, no resample)
                            chunk_size = EL_RATE  # 1s bloky
                            for i in range(0, len(pcm_t48), chunk_size):
                                chunk = pcm_t48[i:i + chunk_size]
                                await ws.send(json.dumps({
                                    "user_audio_chunk": base64.b64encode(chunk.tobytes()).decode()
                                }))
                                await asyncio.sleep(len(chunk) / EL_RATE * 0.9)  # real-time pace

                    elif t == "user_transcript":
                        text = msg.get("user_transcription_event", {}).get("user_transcript", "")
                        if text:
                            print(f"\033[92m[RECEPCE←]\033[0m {text}")

                    elif t == "ping":
                        await ws.send(json.dumps({
                            "type": "pong",
                            "event_id": msg.get("ping_event", {}).get("event_id"),
                        }))

                    elif t == "conversation_initiation_metadata":
                        cid = msg.get("conversation_initiation_metadata_event", {}).get("conversation_id", "")
                        print(f"[session: {cid}]\n")

            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                blocksize=CHUNK_SAMPLES, callback=mic_cb):
                try:
                    await asyncio.gather(send_mic(), recv())
                except websockets.exceptions.ConnectionClosed:
                    print("\n[Hovor ukončen agentem]")
                finally:
                    stop.set()

    finally:
        el_delete_agent(agent_id)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Dual-endpoint phone call simulation")
    parser.add_argument("--mode", choices=["espeak", "hybrid", "full"], default="espeak",
                        help="espeak=nulové náklady | hybrid=1×EL | full=2×EL")
    args = parser.parse_args()

    print("━" * 58)
    print(f"  DUAL SIMULACE — M-Audio MobilePre   [{args.mode.upper()}]")
    print("━" * 58)
    print(f"  Datum: {BOOKING_DATE}  |  Hosté: {GUEST_COUNT}")
    print(f"  Ukončení: Ctrl+C\n")

    signal.signal(signal.SIGINT,  _cleanup_all_agents)
    signal.signal(signal.SIGTERM, _cleanup_all_agents)

    bus = AudioBus()

    try:
        if args.mode == "espeak":
            asyncio.run(run_espeak_mode(bus))
        elif args.mode == "hybrid":
            asyncio.run(run_hybrid_mode(bus))
        else:
            print("Mód 'full' (2× ElevenLabs) není implementován — použij hybrid pro test.")
            sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        _cleanup_all_agents()
    except Exception as e:
        print(f"\nChyba: {e}")
        _cleanup_all_agents()


if __name__ == "__main__":
    main()
