"""Personas as data packages (ADR-0015, REQ-VOICE-019).

Each ``*.yaml`` file here is one persona: lines per language for the machine's phrase keys, a speech speed, and
one optional sentence to add after each safety warning. Loading checks a package before it is used:

- only known phrase keys (those in ``phrases.DEFAULT_PHRASES``) and known languages;
- every template formats with the sample parameters;
- no warning text under ``phrases``: a warning always starts with the shared fragment (``safety.py``);
- a framing line is one short sentence.

A package that fails is logged and left out, so MIA falls back to her own wording rather than going quiet.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

import yaml

from ..phrases import (
    DEFAULT_PHRASES,
    DEFAULT_TABLES,
    SAMPLE_PARAMS,
    localise,
    render_phrase,
)
from ..safety import WARNING_KEYS, render_fragment
from ..types import DEFAULT_PERSONA

logger = logging.getLogger(__name__)

PERSONA_DIR = Path(__file__).resolve().parent
LANGUAGES: Tuple[str, ...] = ("cs", "en")
_NAME = re.compile(r"^[a-z][a-z0-9_]{1,23}$")
# One sentence: no sentence end before the last character.
_ONE_SENTENCE = re.compile(r"^[^.!?]+[.!?]$")
MAX_FRAMING = 90


class PersonaError(ValueError):
    """A persona package that cannot be used."""


@dataclass(frozen=True)
class Persona:
    name: str
    display: str
    phrases: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    warning_framing: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    length_scale: float = 1.0


def _table(data: Any, what: str) -> Dict[str, Dict[str, str]]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise PersonaError(f"{what} must map languages to lines")
    out: Dict[str, Dict[str, str]] = {}
    for language, lines in data.items():
        if language not in LANGUAGES:
            raise PersonaError(f"{what}: unknown language {language!r}")
        if not isinstance(lines, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and v.strip()
            for k, v in lines.items()
        ):
            raise PersonaError(f"{what}.{language} must map keys to non-empty text")
        out[language] = {k: v.strip() for k, v in lines.items()}
    return out


def parse_persona(name: str, data: Any) -> Persona:
    if not _NAME.match(name) or name == DEFAULT_PERSONA:
        raise PersonaError(f"{name!r} is not a usable persona name")
    if not isinstance(data, dict):
        raise PersonaError("a persona package is a mapping")
    phrases = _table(data.get("phrases"), "phrases")
    for language, lines in phrases.items():
        for key, template in lines.items():
            if key in WARNING_KEYS or key.startswith("warning."):
                raise PersonaError(
                    f"{key} is a warning: its content is shared, add a framing line instead"
                )
            if key not in DEFAULT_PHRASES:
                raise PersonaError(f"phrases.{language}: unknown key {key!r}")
            try:
                template.format(**SAMPLE_PARAMS.get(key, {}))
            except (KeyError, ValueError, IndexError) as exc:
                raise PersonaError(
                    f"phrases.{language}.{key} does not format: {exc}"
                ) from None
    framing = _table(data.get("warning_framing"), "warning_framing")
    for language, lines in framing.items():
        for key, line in lines.items():
            if key not in WARNING_KEYS:
                raise PersonaError(
                    f"warning_framing.{language}: unknown warning {key!r}"
                )
            if not _ONE_SENTENCE.match(line) or len(line) > MAX_FRAMING:
                raise PersonaError(
                    f"warning_framing.{language}.{key} must be one short sentence"
                )
    tts = data.get("tts") or {}
    scale = tts.get("length_scale", 1.0) if isinstance(tts, dict) else None
    if (
        isinstance(scale, bool)
        or not isinstance(scale, (int, float))
        or not 0.5 <= scale <= 2.0
    ):
        raise PersonaError("tts.length_scale must be a number from 0.5 to 2.0")
    display = data.get("display", name.capitalize())
    if not isinstance(display, str) or not display.strip():
        raise PersonaError("display must be a name")
    return Persona(name, display.strip(), phrases, framing, float(scale))


def load_personas(directory: Path = PERSONA_DIR) -> Dict[str, Persona]:
    """Every usable package in ``directory``; a broken one is logged and skipped."""
    personas: Dict[str, Persona] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            personas[path.stem] = parse_persona(path.stem, data)
        except (OSError, yaml.YAMLError, PersonaError) as exc:
            logger.error("persona %s left out: %s", path.name, exc)
    return personas


class Phrasebook:
    """Turns a phrase key into words for a persona and a language."""

    def __init__(self, personas: Optional[Mapping[str, Persona]] = None) -> None:
        self._personas = dict(personas or {})

    @classmethod
    def load(cls, directory: Path = PERSONA_DIR) -> "Phrasebook":
        return cls(load_personas(directory))

    @property
    def names(self) -> Tuple[str, ...]:
        return (DEFAULT_PERSONA, *sorted(self._personas))

    @property
    def languages(self) -> Tuple[str, ...]:
        return LANGUAGES

    def display(self, persona: str) -> str:
        found = self._personas.get(persona)
        return found.display if found else "MIA"

    def length_scale(self, persona: str) -> float:
        found = self._personas.get(persona)
        return found.length_scale if found else 1.0

    def render(
        self, phrase: str, params: Mapping[str, Any], persona: str, language: str
    ) -> str:
        found = self._personas.get(persona)
        if phrase in WARNING_KEYS or phrase.startswith("warning."):
            # The shared fragment first, always; one framing sentence after it, never while moving.
            text = render_fragment(phrase, params, language)
            framing = (
                found.warning_framing.get(language, {}).get(phrase) if found else None
            )
            if framing and not params.get("moving"):
                text = f"{text} {framing}"
            return text
        values = localise(params, language)
        if "persona" in values and values["persona"] in self.names:
            values["persona"] = self.display(values["persona"])
        default = DEFAULT_TABLES.get(language, DEFAULT_PHRASES)
        table = dict(DEFAULT_PHRASES)
        table.update(default)
        if found:
            table.update(found.phrases.get(language, {}))
        return render_phrase(phrase, values, table)
