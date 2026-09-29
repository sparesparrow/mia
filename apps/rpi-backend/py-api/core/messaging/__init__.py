"""
ZeroMQ Messaging Layer for MIA
Implements Phase 1.3: ZeroMQ Core Messaging Layer

This module provides Python clients for communicating with the ZeroMQ broker
using FlatBuffers serialized messages.
"""

from .client import MessagingClient

__all__ = ['MessagingClient']