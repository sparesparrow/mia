"""
Cycle state data models for the AI Self-Improvement Orchestrator.

CycleState captures everything about a single improvement cycle:
- Which improvement target is being optimized
- Metrics before and after the cycle
- Phase results and what was learned
- Recommendations for the next cycle
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

# ------------------------------------------------------------------
# Ordered rotation of improvement targets — the orchestrator cycles
# through all five in sequence, one per improvement cycle.
# ------------------------------------------------------------------
IMPROVEMENT_TARGETS: List[str] = [
    "success_rate",
    "generation_quality",
    "coverage_increase",
    "execution_efficiency",
    "error_reduction",
]

# ------------------------------------------------------------------
# Convergence thresholds — the orchestrator stops when ALL are met.
# ------------------------------------------------------------------
TARGET_THRESHOLDS: Dict[str, float] = {
    "success_rate": 0.90,     # ≥90 %
    "coverage": 0.95,         # ≥95 %
    "quality_score": 85.0,    # ≥85/100
    "efficiency": 0.90,       # ≥90 %
    "error_rate": 0.05,       # ≤ 5 %
}

# Initial baseline values — what a system looks like before any
# self-improvement cycles have run.
INITIAL_METRICS: Dict[str, float] = {
    "success_rate": 0.75,
    "coverage": 0.705,        # 110/156 requirements covered
    "quality_score": 70.0,
    "efficiency": 0.65,
    "error_rate": 0.20,
}


@dataclass
class CycleMetrics:
    """Snapshot of system performance at a point in time."""

    success_rate: float = 0.75    # 0–1,   target ≥ 0.90
    coverage: float = 0.705       # 0–1,   target ≥ 0.95
    quality_score: float = 70.0   # 0–100, target ≥ 85
    efficiency: float = 0.65      # 0–1,   target ≥ 0.90
    error_rate: float = 0.20      # 0–1,   target ≤ 0.05

    # ---------------------------------------------------------------
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def copy(self) -> CycleMetrics:
        return CycleMetrics(**asdict(self))

    # ---------------------------------------------------------------
    # Clamping helpers so metrics never drift outside sensible bounds.
    # ---------------------------------------------------------------
    def clamp(self) -> CycleMetrics:
        self.success_rate = max(0.0, min(1.0, self.success_rate))
        self.coverage = max(0.0, min(1.0, self.coverage))
        self.quality_score = max(0.0, min(100.0, self.quality_score))
        self.efficiency = max(0.0, min(1.0, self.efficiency))
        self.error_rate = max(0.0, min(1.0, self.error_rate))
        return self

    def meets_all_targets(self) -> bool:
        return (
            self.success_rate >= TARGET_THRESHOLDS["success_rate"]
            and self.coverage >= TARGET_THRESHOLDS["coverage"]
            and self.quality_score >= TARGET_THRESHOLDS["quality_score"]
            and self.efficiency >= TARGET_THRESHOLDS["efficiency"]
            and self.error_rate <= TARGET_THRESHOLDS["error_rate"]
        )

    def overall_health(self) -> float:
        """Composite health score in [0, 1]; higher is better."""
        scores = [
            self.success_rate / TARGET_THRESHOLDS["success_rate"],
            self.coverage / TARGET_THRESHOLDS["coverage"],
            self.quality_score / TARGET_THRESHOLDS["quality_score"],
            self.efficiency / TARGET_THRESHOLDS["efficiency"],
            (1.0 - self.error_rate) / (1.0 - TARGET_THRESHOLDS["error_rate"]),
        ]
        return min(1.0, sum(scores) / len(scores))


@dataclass
class PhaseResult:
    """Output produced by one of the five improvement phases."""

    phase_name: str
    success: bool
    duration_ms: float
    patterns_learned: List[str] = field(default_factory=list)
    metrics_delta: Dict[str, float] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CycleState:
    """Complete record of one improvement cycle."""

    cycle_number: int
    improvement_target: str          # One of IMPROVEMENT_TARGETS
    started_at: str = ""
    completed_at: str = ""
    completed: bool = False

    metrics_before: CycleMetrics = field(default_factory=CycleMetrics)
    metrics_after: CycleMetrics = field(default_factory=CycleMetrics)

    phase_results: List[PhaseResult] = field(default_factory=list)
    improvement_actions_applied: List[str] = field(default_factory=list)
    next_cycle_recommendation: str = ""

    knowledge_boost_used: float = 0.0   # [0, 1] — how much KB helped this cycle

    # ---------------------------------------------------------------
    @classmethod
    def new(
        cls, cycle_number: int, improvement_target: str, current_metrics: CycleMetrics
    ) -> CycleState:
        return cls(
            cycle_number=cycle_number,
            improvement_target=improvement_target,
            started_at=datetime.now(timezone.utc).isoformat(),
            metrics_before=current_metrics.copy(),
            metrics_after=current_metrics.copy(),
        )

    def mark_completed(self) -> None:
        self.completed = True
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def improvement_rate(self) -> float:
        """Overall health delta between cycle start and end."""
        return self.metrics_after.overall_health() - self.metrics_before.overall_health()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_number": self.cycle_number,
            "improvement_target": self.improvement_target,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "completed": self.completed,
            "metrics_before": self.metrics_before.to_dict(),
            "metrics_after": self.metrics_after.to_dict(),
            "phase_results": [p.to_dict() for p in self.phase_results],
            "improvement_actions_applied": self.improvement_actions_applied,
            "next_cycle_recommendation": self.next_cycle_recommendation,
            "knowledge_boost_used": self.knowledge_boost_used,
            "improvement_rate": self.improvement_rate(),
        }
