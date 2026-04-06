"""
target_espeak.py — skriptovaná recepce chatky přes espeak (nulové náklady)
Používá se jako levná náhrada za ElevenLabs na straně "volaného".
"""

import asyncio
import io
import subprocess
import wave
import numpy as np

ESPEAK_VOICE   = "cs"
ESPEAK_SPEED   = 145   # slov/min (přirozené tempo)
ESPEAK_PITCH   = 55

# Skriptované odpovědi — postupné, přecházejí při každém caller-turnu
SCRIPT = [
    "Dobrý den, penzion Lesní zátiší, jak vám mohu pomoci?",
    "Ano, na třicátého dubna máme jednu chatku volnou.",
    "Cena je osm set korun za noc, minimálně dvě noci.",
    "Chatka má kapacitu šest osob.",
    "Rezervaci potvrzujeme e-mailem, záloha je třicet procent do týdne.",
    "Storno do sedmi dní před příjezdem je bez poplatku.",
    "Dobře, zablokuji vám termín. Pošlete nám prosím e-mail na recepce zavináč penzion lesni zatisi tečka cz.",
    "Není zač, těšíme se na vás. Na shledanou.",
]


def synth(text: str, sample_rate_out: int = 48000) -> np.ndarray:
    """Syntetizuje text přes espeak → PCM int16 na požadované sample rate."""
    proc = subprocess.run(
        ["espeak", "-v", ESPEAK_VOICE, "-s", str(ESPEAK_SPEED),
         "-p", str(ESPEAK_PITCH), "--stdout", text],
        capture_output=True,
    )
    raw = proc.stdout
    if len(raw) < 44:
        return np.zeros(0, dtype=np.int16)

    with wave.open(io.BytesIO(raw)) as w:
        native_rate = w.getframerate()
        frames = w.readframes(w.getnframes())

    pcm = np.frombuffer(frames, dtype=np.int16)

    # Resample na cílový sample rate
    if native_rate != sample_rate_out:
        new_len = int(len(pcm) * sample_rate_out / native_rate)
        pcm = np.interp(
            np.linspace(0, len(pcm) - 1, new_len),
            np.arange(len(pcm)),
            pcm.astype(np.float64),
        ).astype(np.int16)

    return pcm


class EspeakTarget:
    """State machine: při každém volání `next_turn()` vrátí PCM pro další repliku."""

    def __init__(self, sample_rate: int = 48000):
        self._idx = 0
        self._sr  = sample_rate

    def has_next(self) -> bool:
        return self._idx < len(SCRIPT)

    def next_turn(self) -> np.ndarray:
        if not self.has_next():
            return np.zeros(0, dtype=np.int16)
        text = SCRIPT[self._idx]
        self._idx += 1
        print(f"\033[92m[RECEPCE]\033[0m {text}")
        return synth(text, self._sr)
