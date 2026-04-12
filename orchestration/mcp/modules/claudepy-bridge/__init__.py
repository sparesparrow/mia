"""
Claudepy Bridge Module for MIA

Provides integration between MIA's voice pipeline and claudepy's AI orchestrator.
"""

from .main import ClaudepyBridge, VoiceCommandResult

__all__ = ["ClaudepyBridge", "VoiceCommandResult"]
