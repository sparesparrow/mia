"""Voice settings that outlive a restart (ADR-0019, REQ-VOICE-017).

One small JSON file in ``MIA_STATE_DIR`` (``/var/lib/mia`` on the Pi). Reading never fails: a missing, unreadable
or damaged file, or a value this version does not know, gives the defaults. Writing replaces the file in one step,
so a power cut leaves either the old settings or the new ones, and a write error is logged rather than raised, so
the voice loop never stops over a setting.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .types import DEFAULT_LANGUAGE, DEFAULT_PERSONA, Settings, Verbosity

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = "/var/lib/mia"
FILE_NAME = "voice_settings.json"
# A persona or language is a short lowercase name; anything else in the file is ignored. Whether this Pi has
# that persona or language is the machine's check, which falls back to its first one.
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,23}$")


def _name(value: Any, default: str, what: str) -> str:
    if isinstance(value, str) and _NAME.match(value):
        return value
    if value is not None:
        logger.warning("unusable %s %r, using %s", what, value, default)
    return default


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @classmethod
    def from_env(cls) -> "SettingsStore":
        return cls(Path(os.environ.get("MIA_STATE_DIR", DEFAULT_STATE_DIR)) / FILE_NAME)

    def load(self) -> Settings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError) as exc:
            logger.warning("voice settings unreadable, using defaults: %s", exc)
            return Settings()
        if not isinstance(data, dict):
            logger.warning("voice settings are not an object, using defaults")
            return Settings()
        try:
            verbosity = Verbosity(data.get("verbosity", Verbosity.NORMAL.value))
        except ValueError:
            logger.warning(
                "unknown verbosity %r, using %s",
                data.get("verbosity"),
                Verbosity.NORMAL.value,
            )
            verbosity = Verbosity.NORMAL
        return Settings(
            verbosity=verbosity,
            persona=_name(data.get("persona"), DEFAULT_PERSONA, "persona"),
            language=_name(data.get("language"), DEFAULT_LANGUAGE, "language"),
        )

    def save(self, settings: Settings) -> bool:
        """Store ``settings``; False (and a log line) if the file cannot be written."""
        stored = {
            "verbosity": settings.verbosity.value,
            "persona": settings.persona,
            "language": settings.language,
        }
        body = json.dumps(stored, indent=2) + "\n"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, partial = tempfile.mkstemp(
                dir=self.path.parent, prefix=f".{self.path.name}."
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(body)
                os.replace(partial, self.path)
            except BaseException:
                os.unlink(partial)
                raise
        except OSError as exc:
            logger.warning("voice settings not saved: %s", exc)
            return False
        return True
