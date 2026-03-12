"""
AI Self-Improvement Orchestrator package.

Provides a fully autonomous, continuously learning orchestration loop
for iterative quality improvement across firmware compliance targets.

Quick start
───────────
    from orchestration.ai_self_improvement import AISelfImprovementOrchestrator

    orchestrator = AISelfImprovementOrchestrator()

    # Run a single cycle
    import asyncio
    cycle = asyncio.run(orchestrator.run_cycle())
    print(orchestrator.render_cycle_prompt(cycle))

    # Run autonomously until convergence (or 50 cycles)
    history = orchestrator.run_autonomous_sync(max_cycles=50)

CLI
───
    python -m orchestration.ai_self_improvement run --max-cycles 20
    python -m orchestration.ai_self_improvement status
    python -m orchestration.ai_self_improvement reset
"""

from .cycle_state import (
    IMPROVEMENT_TARGETS,
    INITIAL_METRICS,
    TARGET_THRESHOLDS,
    CycleMetrics,
    CycleState,
    PhaseResult,
)
from .knowledge_base import KnowledgeBase, Pattern
from .orchestrator import AISelfImprovementOrchestrator

__all__ = [
    "AISelfImprovementOrchestrator",
    "CycleMetrics",
    "CycleState",
    "PhaseResult",
    "KnowledgeBase",
    "Pattern",
    "IMPROVEMENT_TARGETS",
    "INITIAL_METRICS",
    "TARGET_THRESHOLDS",
]
