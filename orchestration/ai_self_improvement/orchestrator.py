"""
AI Self-Improvement Orchestrator — master controller.

Coordinates five specialised phases in a continuous learning loop:

    Phase 1  RequirementsAnalysis   — map coverage gaps and priorities
    Phase 2  TestGeneration         — generate tests / fixes for gaps
    Phase 3  CodeReview             — quality-assure generated artefacts
    Phase 4  LearningAnalytics      — extract patterns, update KB
    Phase 5  ContinuousOrchestrator — apply improvement actions

Key design principles
─────────────────────
• **Fully autonomous** — ``run_autonomous`` drives the loop without
  external supervision, stopping only when targets are met or the cycle
  ceiling is reached.
• **All improvement targets** — the orchestrator cycles through every
  target (success_rate, generation_quality, coverage_increase,
  execution_efficiency, error_reduction) in sequence, then optionally
  switches to whichever metric is worst (intelligent routing).
• **Persistent learning** — the knowledge base (JSON on disk) grows
  across runs.  Restarting the orchestrator continues from where it left
  off.
• **Template-rendered status** — each cycle renders a Jinja2 template
  that describes the current state in a human-readable format identical
  in structure to the original ES-1856 example use-case.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from jinja2 import Environment, FileSystemLoader
    _JINJA2_AVAILABLE = True
except ImportError:
    Environment = None  # type: ignore[assignment,misc]
    FileSystemLoader = None  # type: ignore[assignment,misc]
    _JINJA2_AVAILABLE = False

from .cycle_state import (
    IMPROVEMENT_TARGETS,
    INITIAL_METRICS,
    CycleMetrics,
    CycleState,
)
from .knowledge_base import KnowledgeBase
from .phases import (
    CodeReviewPhase,
    ContinuousOrchestratorPhase,
    LearningAnalyticsPhase,
    RequirementsAnalysisPhase,
    TestGenerationPhase,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Default file locations                                               #
# ------------------------------------------------------------------ #

_HERE = Path(__file__).parent
_DEFAULT_KB_PATH = _HERE / "data" / "knowledge_base.json"
_DEFAULT_STATE_PATH = _HERE / "data" / "orchestrator_state.json"
_TEMPLATE_DIR = _HERE / "prompt_templates"


class AISelfImprovementOrchestrator:
    """
    Master controller for the self-improvement loop.

    Parameters
    ----------
    knowledge_base_path:
        Where the persistent KB JSON file lives.
    state_path:
        Stores lightweight orchestrator state between runs (cycle counter,
        current target index, current metrics).
    intelligent_routing:
        When True the orchestrator overrides the fixed rotation after the
        first full rotation and picks the metric that is furthest from its
        target (worst-first).  Defaults to True.
    """

    def __init__(
        self,
        knowledge_base_path: Path = _DEFAULT_KB_PATH,
        state_path: Path = _DEFAULT_STATE_PATH,
        intelligent_routing: bool = True,
    ) -> None:
        self.kb = KnowledgeBase(knowledge_base_path)
        self.state_path = state_path
        self.intelligent_routing = intelligent_routing

        # Ordered pipeline of phases
        self._phases = [
            RequirementsAnalysisPhase(),
            TestGenerationPhase(),
            CodeReviewPhase(),
            LearningAnalyticsPhase(),
            ContinuousOrchestratorPhase(),
        ]

        # Jinja2 environment for cycle-prompt rendering
        self._jinja_env: Optional[Environment] = None
        if _JINJA2_AVAILABLE and _TEMPLATE_DIR.exists():
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(_TEMPLATE_DIR)),
                autoescape=False,
            )

        # Mutable orchestrator state — loaded from disk if it exists
        self._state: Dict[str, Any] = self._load_state()

    # ---------------------------------------------------------------- #
    # State persistence                                                  #
    # ---------------------------------------------------------------- #

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "cycle_number": 0,
            "target_index": 0,   # index into IMPROVEMENT_TARGETS
            "current_metrics": INITIAL_METRICS.copy(),
            "completed_cycles": [],
        }

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                with open(self.state_path) as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass
        return self._empty_state()

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as fh:
            json.dump(self._state, fh, indent=2)

    # ---------------------------------------------------------------- #
    # Target rotation                                                    #
    # ---------------------------------------------------------------- #

    def _current_target(self) -> str:
        idx = self._state["target_index"] % len(IMPROVEMENT_TARGETS)
        return IMPROVEMENT_TARGETS[idx]

    def _advance_target(self, completed_cycle: CycleState) -> None:
        """
        Move to the next improvement target.

        After the first full rotation (cycle > len(IMPROVEMENT_TARGETS)),
        intelligent routing picks the worst-performing metric instead of the
        fixed sequence — unless intelligent_routing is disabled.
        """
        cycles_done = self._state["cycle_number"]
        full_rotations = cycles_done // len(IMPROVEMENT_TARGETS)

        if self.intelligent_routing and full_rotations >= 1:
            # Recommend from Phase 5 or fall back to KB analysis
            rec = completed_cycle.next_cycle_recommendation
            if rec and rec in IMPROVEMENT_TARGETS:
                self._state["target_index"] = IMPROVEMENT_TARGETS.index(rec)
                return

        # Default: fixed rotation
        self._state["target_index"] = (
            self._state["target_index"] + 1
        ) % len(IMPROVEMENT_TARGETS)

    # ---------------------------------------------------------------- #
    # Current metrics                                                    #
    # ---------------------------------------------------------------- #

    def _current_metrics(self) -> CycleMetrics:
        raw = self._state.get("current_metrics", INITIAL_METRICS)
        return CycleMetrics(
            success_rate=raw.get("success_rate", INITIAL_METRICS["success_rate"]),
            coverage=raw.get("coverage", INITIAL_METRICS["coverage"]),
            quality_score=raw.get("quality_score", INITIAL_METRICS["quality_score"]),
            efficiency=raw.get("efficiency", INITIAL_METRICS["efficiency"]),
            error_rate=raw.get("error_rate", INITIAL_METRICS["error_rate"]),
        )

    def _sync_metrics_to_state(self, metrics: CycleMetrics) -> None:
        self._state["current_metrics"] = metrics.to_dict()

    # ---------------------------------------------------------------- #
    # Single cycle execution                                             #
    # ---------------------------------------------------------------- #

    async def run_cycle(self) -> CycleState:
        """
        Execute one full 5-phase improvement cycle.

        Returns the completed CycleState with before/after metrics,
        all phase results, and the recommendation for the next cycle.
        """
        cycle_number = self._state["cycle_number"] + 1
        target = self._current_target()
        metrics = self._current_metrics()

        cycle = CycleState.new(cycle_number, target, metrics)
        boost = self.kb.get_knowledge_boost(target)
        cycle.knowledge_boost_used = round(boost, 3)

        logger.info(
            "Starting cycle %d — target=%s, kb_boost=%.2f, health=%.1f%%",
            cycle_number,
            target,
            boost,
            metrics.overall_health() * 100,
        )

        # Run all phases sequentially
        for phase in self._phases:
            try:
                result = await phase.execute(cycle, self.kb)
                cycle.phase_results.append(result)
                if not result.success:
                    logger.warning("Phase %s reported failure in cycle %d", phase.name, cycle_number)
            except Exception as exc:  # noqa: BLE001
                logger.error("Phase %s raised %s in cycle %d", phase.name, exc, cycle_number)

        # Finalise
        cycle.mark_completed()
        cycle.improvement_actions_applied = [
            action
            for pr in cycle.phase_results
            for action in pr.details.get("actions_applied", [])
        ]

        # Persist
        self._state["cycle_number"] = cycle_number
        self._sync_metrics_to_state(cycle.metrics_after)
        self._advance_target(cycle)
        self._save_state()
        self.kb.record_cycle(cycle.to_dict())

        logger.info(
            "Cycle %d done — health %.1f%% → %.1f%%, improvement_rate=%.3f",
            cycle_number,
            cycle.metrics_before.overall_health() * 100,
            cycle.metrics_after.overall_health() * 100,
            cycle.improvement_rate(),
        )
        return cycle

    # ---------------------------------------------------------------- #
    # Autonomous multi-cycle loop                                        #
    # ---------------------------------------------------------------- #

    async def run_autonomous(
        self,
        max_cycles: int = 50,
        convergence_patience: int = 5,
        verbose: bool = True,
    ) -> List[CycleState]:
        """
        Run improvement cycles until convergence or *max_cycles* is reached.

        Convergence is declared when ALL metric targets are met for
        *convergence_patience* consecutive cycles.

        Parameters
        ----------
        max_cycles:
            Hard upper bound — prevents infinite loops.
        convergence_patience:
            Number of successive cycles that must all meet targets before
            the orchestrator declares convergence and stops.
        verbose:
            Print a rendered status prompt after each cycle.

        Returns
        -------
        List of CycleState objects, one per completed cycle.
        """
        history: List[CycleState] = []
        consecutive_converged = 0

        for _ in range(max_cycles):
            cycle = await self.run_cycle()
            history.append(cycle)

            if verbose:
                prompt = self.render_cycle_prompt(cycle)
                print(prompt)

            if cycle.metrics_after.meets_all_targets():
                consecutive_converged += 1
                logger.info(
                    "Convergence check: %d/%d cycles meet all targets",
                    consecutive_converged,
                    convergence_patience,
                )
                if consecutive_converged >= convergence_patience:
                    logger.info(
                        "Convergence achieved after %d cycles.", len(history)
                    )
                    break
            else:
                consecutive_converged = 0

        return history

    # ---------------------------------------------------------------- #
    # Template rendering                                                 #
    # ---------------------------------------------------------------- #

    def render_cycle_prompt(self, cycle: CycleState) -> str:
        """
        Render the Jinja2 orchestrator-cycle template for the given cycle.

        Returns a formatted string describing what the current cycle
        accomplished — identical in structure to the ES-1856 example in
        the task specification.
        """
        if self._jinja_env is None:
            return self._fallback_prompt(cycle)

        try:
            template = self._jinja_env.get_template("orchestrator_cycle.j2")
            m = cycle.metrics_after

            # Coverage numbers (like 110/156)
            total_reqs = 156
            covered_reqs = int(m.coverage * total_reqs)
            uncovered_reqs = total_reqs - covered_reqs

            return template.render(
                cycle_number=str(cycle.cycle_number),
                improvement_targets=cycle.improvement_target,
                metrics={
                    "success_rate": round(m.success_rate * 100, 1),
                    "coverage_pct": round(m.coverage * 100, 1),
                    "covered_reqs": covered_reqs,
                    "total_reqs": total_reqs,
                    "uncovered_reqs": uncovered_reqs,
                    "quality_score": round(m.quality_score, 1),
                    "efficiency_pct": round(m.efficiency * 100, 1),
                    "error_rate_pct": round(m.error_rate * 100, 1),
                },
                improvement_rate=round(cycle.improvement_rate() * 100, 2),
                kb_boost=round(cycle.knowledge_boost_used * 100, 1),
                kb_stats=self.kb.get_statistics(),
                next_target=cycle.next_cycle_recommendation,
                phase_results=[pr.to_dict() for pr in cycle.phase_results],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Template rendering failed (%s) — using fallback.", exc)
            return self._fallback_prompt(cycle)

    @staticmethod
    def _fallback_prompt(cycle: CycleState) -> str:
        """Plain-text status when the template is unavailable."""
        m = cycle.metrics_after
        sep = "━" * 50
        return (
            f"\nCycle {cycle.cycle_number} — target: {cycle.improvement_target}\n"
            f"{sep}\n"
            f"  Success Rate   │ {m.success_rate * 100:5.1f}%\n"
            f"  Coverage       │ {m.coverage * 100:5.1f}%\n"
            f"  Quality Score  │ {m.quality_score:5.1f}/100\n"
            f"  Efficiency     │ {m.efficiency * 100:5.1f}%\n"
            f"  Error Rate     │ {m.error_rate * 100:5.1f}%\n"
            f"{sep}\n"
            f"  Improvement    │ +{cycle.improvement_rate() * 100:.2f}%\n"
            f"  Converged?     │ {'YES' if m.meets_all_targets() else 'no'}\n"
            f"  Next target    │ {cycle.next_cycle_recommendation or 'TBD'}\n"
        )

    # ---------------------------------------------------------------- #
    # Introspection                                                      #
    # ---------------------------------------------------------------- #

    def status(self) -> Dict[str, Any]:
        """Return a snapshot of the orchestrator's current state."""
        m = self._current_metrics()
        return {
            "cycle_number": self._state["cycle_number"],
            "current_target": self._current_target(),
            "metrics": m.to_dict(),
            "converged": m.meets_all_targets(),
            "health_pct": round(m.overall_health() * 100, 2),
            "kb_statistics": self.kb.get_statistics(),
            "improvement_trend": round(
                self.kb.calculate_improvement_trend(last_n=5) * 100, 3
            ),
        }

    def reset(self, reset_knowledge_base: bool = False) -> None:
        """
        Reset orchestrator state to initial values.

        Parameters
        ----------
        reset_knowledge_base:
            If True, also wipe all accumulated knowledge.  Use with caution.
        """
        self._state = self._empty_state()
        if self.state_path.exists():
            self.state_path.unlink()
        if reset_knowledge_base:
            self.kb.reset()
        logger.info("Orchestrator reset (kb_reset=%s)", reset_knowledge_base)

    # ---------------------------------------------------------------- #
    # Convenience sync wrappers                                          #
    # ---------------------------------------------------------------- #

    def run_cycle_sync(self) -> CycleState:
        """Synchronous wrapper around run_cycle for non-async callers."""
        return asyncio.run(self.run_cycle())

    def run_autonomous_sync(
        self,
        max_cycles: int = 50,
        convergence_patience: int = 5,
        verbose: bool = True,
    ) -> List[CycleState]:
        """Synchronous wrapper around run_autonomous."""
        return asyncio.run(
            self.run_autonomous(
                max_cycles=max_cycles,
                convergence_patience=convergence_patience,
                verbose=verbose,
            )
        )
