#!/usr/bin/env python3
"""Render the test phrases as speech fixtures: 16 kHz, 16-bit, mono WAV files plus a sha256 manifest.

    python tools/voice/render_fixtures.py [--out /var/tmp/mia-voice-fixtures] [--phrases tools/voice/phrases.yaml]
                                          [--engine auto|espeak-ng|piper] [--piper-model PATH.onnx]

The scenario harness (REQ-VOICE-028) plays these into the Pi's audio path. They are rendered on demand with
espeak-ng or piper and are never committed: the output directory must be outside the repository. The phrases are
English, because Czech speech recognition is blocked (REQ-VOICE-023).
"""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHRASES = Path(__file__).resolve().with_name("phrases.yaml")
DEFAULT_OUT = Path("/var/tmp/mia-voice-fixtures")
RATE = 16000
MANIFEST = "manifest.json"

# A synthesizer writes a WAV of any rate and channel count for the text; it is converted afterwards.
Synthesizer = Callable[[str, Path], None]


class RenderError(RuntimeError):
    """A problem the user can fix: no engine, a bad phrase list, an output directory in the repository."""


def load_phrases(path: Path) -> List[str]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    phrases = data.get("phrases") if isinstance(data, dict) else None
    if not isinstance(phrases, list) or not phrases:
        raise RenderError(f"{path}: expected a non-empty 'phrases' list")
    seen: Dict[str, str] = {}
    for phrase in phrases:
        if not isinstance(phrase, str) or not phrase.strip():
            raise RenderError(f"{path}: every phrase is a non-empty string, got {phrase!r}")
        name = slug(phrase)
        if not name:
            raise RenderError(f"{path}: phrase {phrase!r} has no letters or digits")
        if name in seen:
            raise RenderError(f"{path}: {phrase!r} and {seen[name]!r} would both be {name}.wav")
        seen[name] = phrase
    return [p.strip() for p in phrases]


def slug(phrase: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", phrase.lower()).strip("_")


def to_16k_mono(source: Path, target: Path) -> float:
    """Convert a 16-bit PCM WAV to 16 kHz mono (linear interpolation, enough for speech). Returns seconds."""
    with wave.open(str(source), "rb") as wav:
        if wav.getsampwidth() != 2:
            raise RenderError(f"{source}: expected 16-bit samples, got {8 * wav.getsampwidth()}-bit")
        channels, rate, frames = wav.getnchannels(), wav.getframerate(), wav.readframes(wav.getnframes())
    samples = array.array("h")
    samples.frombytes(frames)
    if sys.byteorder == "big":
        samples.byteswap()
    if channels > 1:
        samples = array.array(
            "h", (sum(samples[i : i + channels]) // channels for i in range(0, len(samples) - channels + 1, channels))
        )
    if rate != RATE and len(samples) > 1:
        count = max(1, round(len(samples) * RATE / rate))
        step = (len(samples) - 1) / max(1, count - 1)
        out = array.array("h")
        for i in range(count):
            pos = i * step
            lo = int(pos)
            hi = min(lo + 1, len(samples) - 1)
            out.append(round(samples[lo] + (samples[hi] - samples[lo]) * (pos - lo)))
        samples = out
    if sys.byteorder == "big":
        samples.byteswap()
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(samples.tobytes())
    return len(samples) / RATE


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(phrases: List[str], out: Path, synthesize: Synthesizer, engine: str = "custom") -> dict:
    """Render every phrase into ``out`` and write ``manifest.json``; return the manifest."""
    out = Path(out).resolve()
    if out == REPO_ROOT or REPO_ROOT in out.parents:
        raise RenderError(f"{out} is inside the repository; fixtures are never committed, use a directory outside it")
    out.mkdir(parents=True, exist_ok=True)
    files: Dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="mia-voice-") as scratch:
        for phrase in phrases:
            name = f"{slug(phrase)}.wav"
            raw = Path(scratch) / name
            synthesize(phrase, raw)
            if not raw.is_file() or raw.stat().st_size == 0:
                raise RenderError(f"the synthesizer wrote nothing for {phrase!r}")
            seconds = to_16k_mono(raw, out / name)
            files[name] = {
                "phrase": phrase,
                "sha256": sha256_of(out / name),
                "bytes": (out / name).stat().st_size,
                "seconds": round(seconds, 3),
            }
    manifest = {"format": "wav s16le 16000 Hz mono", "engine": engine, "language": "en", "files": files}
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify(out: Path) -> List[str]:
    """Problems with a rendered directory: a missing file or a hash that no longer matches the manifest."""
    out = Path(out)
    try:
        manifest = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{out / MANIFEST}: {exc}"]
    problems = []
    for name, entry in manifest.get("files", {}).items():
        if not (out / name).is_file():
            problems.append(f"{name}: missing")
        elif sha256_of(out / name) != entry.get("sha256"):
            problems.append(f"{name}: sha256 differs from the manifest")
    return problems


def espeak_synthesizer(binary: str) -> Synthesizer:
    def synthesize(text: str, target: Path) -> None:
        subprocess.run([binary, "-v", "en-us", "-s", "150", "-w", str(target), "--", text], check=True, timeout=60)

    return synthesize


def piper_synthesizer(binary: str, model: str) -> Synthesizer:
    def synthesize(text: str, target: Path) -> None:
        subprocess.run(
            [binary, "--model", model, "--output_file", str(target)], input=text.encode(), check=True, timeout=120
        )

    return synthesize


def pick_engine(choice: str, piper_model: Optional[str]) -> "tuple[str, Synthesizer]":
    espeak = shutil.which("espeak-ng")
    piper = shutil.which("piper")
    if choice in ("auto", "piper") and piper and piper_model:
        return "piper", piper_synthesizer(piper, piper_model)
    if choice == "piper":
        raise RenderError("piper needs the piper binary on PATH and --piper-model PATH.onnx")
    if choice in ("auto", "espeak-ng") and espeak:
        return "espeak-ng", espeak_synthesizer(espeak)
    raise RenderError(
        "no speech synthesizer found: install espeak-ng (apt install espeak-ng), or piper with --piper-model"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output directory (default {DEFAULT_OUT})")
    parser.add_argument("--phrases", type=Path, default=DEFAULT_PHRASES)
    parser.add_argument("--engine", choices=("auto", "espeak-ng", "piper"), default="auto")
    parser.add_argument("--piper-model", help="path of a piper .onnx voice")
    parser.add_argument("--verify", action="store_true", help="only check the directory against its manifest")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            problems = verify(args.out)
            print("\n".join(problems) or f"{args.out}: all files match the manifest")
            return 1 if problems else 0
        engine, synthesize = pick_engine(args.engine, args.piper_model)
        manifest = render(load_phrases(args.phrases), args.out, synthesize, engine)
    except RenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"rendered {len(manifest['files'])} phrases with {engine} into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
