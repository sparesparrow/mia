"""
target_llm.py — dynamická recepce chatky: Groq LLM + espeak hlas
Groq free tier (llama-3.1-8b-instant) + espeak → nulové TTS náklady.
"""

import asyncio
import os

import openai

from target_espeak import synth as espeak_synth

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

_client = openai.OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

SYSTEM = """Jsi recepční malého penzionu v České republice.
Odpovídáš na telefonní dotazy ohledně rezervací. Buď přirozený, stručný, přátelský.
Mluv vždy česky. Odpovědi max 2 věty.

Fakta o penzionu:
- Název: Penzion Lesní zátiší
- Cena: 800 Kč/noc, min 2 noci
- Kapacita chatky: 6 osob
- Potvrzení: e-mail + záloha 30 % do 7 dní
- Storno: zdarma do 7 dní před příjezdem
- Kontakt: recepce@lesnizatisi.cz
- Dostupnost 30. dubna 2026: volno
"""


class LLMTarget:
    def __init__(self, sample_rate: int = 48000):
        self._history = []
        self._sr = sample_rate

    async def respond(self, caller_text: str) -> tuple[str, "np.ndarray"]:
        import numpy as np
        self._history.append({"role": "user", "content": caller_text})

        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, self._call_groq)

        self._history.append({"role": "assistant", "content": reply})
        print(f"\033[92m[RECEPCE]\033[0m {reply}")

        pcm = await loop.run_in_executor(None, lambda: espeak_synth(reply, self._sr))
        return reply, pcm

    def _call_groq(self) -> str:
        r = _client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=100,
            messages=[{"role": "system", "content": SYSTEM}] + self._history,
        )
        return r.choices[0].message.content.strip()
