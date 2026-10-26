"""MIA's own wording: the default persona, in code so a broken persona package can never leave her silent (ADR-0015).

The machine only knows phrase keys. ``render_phrase`` fills a template with the parameters; ``Phrasebook``
(``personas``) chooses the template for a persona and a language. A persona package may override any key here
but may not add new ones, so every key it uses is one the machine really says.

The Czech lines ask for "yes" and "no": speech recognition is English until Czech recognition exists (#179).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

DEFAULT_PHRASES: Dict[str, str] = {
    "chain.announce": "I will {parts} in {seconds:.0f} seconds. Say stop or press cancel.",
    "chain.refused": "I can't do that: {part}.",
    "chain.dictation_alone": "A note has to be on its own. Say it again without the rest.",
    "message.confirm": "Send it? Say yes or no.",
    "confirm.timeout": "No answer, so I did not send it.",
    "intent.unknown": "Sorry, I didn't understand.",
    "note.empty": "The note was empty.",
    "message.arrived": "New message from {sender}.",
    "message.read": "Message from {sender}: {text}",
    "verbosity.set": "Okay, {level}.",
    "persona.set": "{persona} here.",
    "persona.unknown": "I don't know a persona called {persona}.",
    "language.set": "Okay, speaking English.",
    "language.unknown": "I can't speak {language}.",
}

DEFAULT_PHRASES_CS: Dict[str, str] = {
    "chain.announce": "Za {seconds:.0f} sekund provedu: {parts}. Řekněte stop nebo stiskněte zrušit.",
    "chain.refused": "Tohle udělat nemůžu: {part}.",
    "chain.dictation_alone": "Poznámku řekněte samostatně, bez dalších příkazů.",
    "message.confirm": "Odeslat? Řekněte yes, nebo no.",
    "confirm.timeout": "Bez odpovědi, takže se nic neodeslalo.",
    "intent.unknown": "Promiňte, tomu nerozumím.",
    "note.empty": "Poznámka byla prázdná.",
    "message.arrived": "Nová zpráva od {sender}.",
    "message.read": "Zpráva od {sender}: {text}",
    "verbosity.set": "Dobře, režim {level}.",
    "persona.set": "Tady {persona}.",
    "persona.unknown": "Osobnost {persona} neznám.",
    "language.set": "Dobře, mluvím česky.",
    "language.unknown": "Jazyk {language} neumím.",
}

DEFAULT_TABLES: Dict[str, Dict[str, str]] = {
    "en": DEFAULT_PHRASES,
    "cs": DEFAULT_PHRASES_CS,
}

# Parameters a test formats every template with, so a package cannot ship a template that breaks at runtime.
SAMPLE_PARAMS: Dict[str, Dict[str, Any]] = {
    "chain.announce": {"parts": ["lights.on", "read.voltage"], "seconds": 5.0},
    "chain.refused": {"part": "ecu.write"},
    "message.arrived": {"sender": "Jana"},
    "message.read": {"sender": "Jana", "text": "Running late."},
    "verbosity.set": {"level": "quiet"},
    "persona.set": {"persona": "Holly"},
    "persona.unknown": {"persona": "Kryten"},
    "language.unknown": {"language": "de"},
}

# Values the machine passes as codes, said as words in each language.
_WORDS: Dict[str, Dict[str, Dict[str, str]]] = {
    "level": {
        "en": {"quiet": "quiet", "normal": "normal", "chatty": "chatty"},
        "cs": {"quiet": "tichý", "normal": "běžný", "chatty": "upovídaný"},
    },
    "language": {
        "en": {"cs": "Czech", "en": "English"},
        "cs": {"cs": "čeština", "en": "angličtina"},
    },
}


def localise(params: Mapping[str, Any], language: str) -> Dict[str, Any]:
    """Codes such as ``quiet`` or ``cs`` become words of ``language``; anything else is kept as it is."""
    values = dict(params)
    for key, words in _WORDS.items():
        if isinstance(values.get(key), str):
            values[key] = words.get(language, {}).get(values[key], values[key])
    return values


def render_phrase(
    phrase: str, params: Dict[str, Any], table: Optional[Dict[str, str]] = None
) -> str:
    """Turn a phrase key and parameters into text. ``raw`` carries ready text from an executor."""
    if phrase == "raw":
        return str(params.get("text", ""))
    template = (table or DEFAULT_PHRASES).get(phrase)
    if template is None:
        return phrase
    values = dict(params)
    if isinstance(values.get("parts"), (list, tuple)):
        values["parts"] = ", ".join(str(p) for p in values["parts"])
    try:
        return template.format(**values)
    except (KeyError, ValueError, IndexError):
        return template
