"""
FlatBuffers Message Builder and Parser
Implements Phase 1.2: FlatBuffers Schema Design

Utilities for building and parsing FlatBuffers messages for ZeroMQ communication.
"""

from .builder import MessageBuilder
from .parser import MessageParser

__all__ = ['MessageBuilder', 'MessageParser']