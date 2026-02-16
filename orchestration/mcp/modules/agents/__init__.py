"""
MIA Voice Learning Agents

Seven-agent architecture for continuous voice command learning:

Foundation Layer (must start first):
- VoiceCommandIntelligenceAgent: Core command processing
- ContextManagerAgent: Storage and context retrieval

Analysis Layer (depends on foundation):
- PerformanceMonitorAgent: Metrics collection
- ErrorCoordinatorAgent: Failure analysis
- VoicePatternAnalyzerAgent: Pattern detection

Learning Layer (depends on analysis):
- KnowledgeSynthesizerAgent: Knowledge synthesis
- LearningLoopOrchestratorAgent: Learning cycle coordination
"""

from .voice_command_intelligence import VoiceCommandIntelligenceAgent
from .context_manager import ContextManagerAgent
from .performance_monitor import PerformanceMonitorAgent
from .error_coordinator import ErrorCoordinatorAgent
from .voice_pattern_analyzer import VoicePatternAnalyzerAgent
from .knowledge_synthesizer import KnowledgeSynthesizerAgent
from .learning_loop_orchestrator import LearningLoopOrchestratorAgent

__all__ = [
    "VoiceCommandIntelligenceAgent",
    "ContextManagerAgent",
    "PerformanceMonitorAgent",
    "ErrorCoordinatorAgent",
    "VoicePatternAnalyzerAgent",
    "KnowledgeSynthesizerAgent",
    "LearningLoopOrchestratorAgent",
]
