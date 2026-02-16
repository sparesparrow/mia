"""
FastAPI Server for MIA Hardware Management
Phase 3: FastAPI & Remote Control

This module provides REST and WebSocket APIs for hardware control,
integrating with the ZeroMQ messaging layer and hardware abstraction.
"""

# Lazy import to avoid import cascade when importing api.auth
# Only import server.py when app is actually accessed
# This prevents relative import errors when api is imported as top-level module

_app = None

def __getattr__(name):
    """Lazy loader for app attribute"""
    global _app
    if name == 'app':
        if _app is None:
            try:
                from .server import app
                _app = app
            except ImportError as e:
                raise
        return _app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['app']