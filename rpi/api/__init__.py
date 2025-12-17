"""
FastAPI Server for MIA Hardware Management
Phase 3: FastAPI & Remote Control

This module provides REST and WebSocket APIs for hardware control,
integrating with the ZeroMQ messaging layer and hardware abstraction.
"""

from .server import app

__all__ = ['app']