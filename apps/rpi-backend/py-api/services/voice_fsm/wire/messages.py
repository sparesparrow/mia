"""Plain-Python side of the voice envelope (schemas/voice.fbs, ADR-0013).

The numbers match the schema enums; ``tests/unit/rpi_backend/test_voice_wire_codec.py`` compares
them with the generated bindings, so a renumbered enum fails a test rather than a car.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

WIRE_VERSION = 1
FILE_IDENTIFIER = b"MIAV"


class Service(IntEnum):
    UNKNOWN = 0
    VOICE = 1


class Op(IntEnum):
    DATA = 0
    OPEN = 1
    CLOSE = 2


class Status(IntEnum):
    OK = 0
    UNKNOWN_SERVICE = 1
    UNSUPPORTED_VERSION = 2
    MALFORMED = 3
    NOT_PERMITTED = 4
    UNKNOWN_SESSION = 5


@dataclass(frozen=True)
class Envelope:
    """Routing header around a service payload. The envelope never looks inside ``payload``."""

    service: int = Service.VOICE
    session_id: str = ""
    op: int = Op.DATA
    status: int = Status.OK
    seq: int = 0
    payload: bytes = b""
    version: int = WIRE_VERSION


@dataclass(frozen=True)
class Transcript:
    """What the user said, as recognised. An event for peers; the machine does not consume it."""

    text: str
    utterance_id: int = 0
