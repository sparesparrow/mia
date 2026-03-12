"""
Persistent knowledge base for the AI Self-Improvement Orchestrator.

The knowledge base stores learned patterns, cycle history, insights, and
hardware behaviour models across runs.  It provides:

- Pattern confidence tracking (low → medium → high) as patterns accumulate
- Knowledge-boost computation — more validated patterns → higher boost
- Full cycle history for trend analysis
- Insight accumulation for meta-learning
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Pattern:
    """A learned behaviour or strategy discovered during a cycle."""

    pattern_id: str
    pattern_type: str          # "generation" | "review" | "error" | "optimization" | "meta"
    improvement_target: str    # Which target this pattern helps with
    description: str
    success_count: int = 1
    confidence: str = "low"    # "low" | "medium" | "high"
    created_at: str = ""
    last_used: str = ""

    def bump(self) -> None:
        """Record one more successful use and update confidence."""
        self.success_count += 1
        self.last_used = datetime.now(timezone.utc).isoformat()
        if self.success_count >= 4:
            self.confidence = "high"
        elif self.success_count >= 2:
            self.confidence = "medium"
        else:
            self.confidence = "low"


class KnowledgeBase:
    """
    JSON-backed knowledge store.

    All writes are immediately flushed to disk so the orchestrator can
    resume cleanly after an interruption.
    """

    _SCHEMA_VERSION = "2.0"

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._data: Dict[str, Any] = self._empty_store()
        self._load()

    # ------------------------------------------------------------------ #
    # Internal I/O                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _empty_store() -> Dict[str, Any]:
        return {
            "schema_version": KnowledgeBase._SCHEMA_VERSION,
            "total_cycles": 0,
            "total_patterns": 0,
            "current_metrics": {},
            "cycle_history": [],
            "patterns": {},              # keyed by pattern_id
            "insights": [],
            "hardware_behavior_models": {},
            "improvement_rules": {},
            "target_pattern_counts": {   # quick lookup: target -> count
                t: 0 for t in [
                    "success_rate", "generation_quality",
                    "coverage_increase", "execution_efficiency", "error_reduction"
                ]
            },
        }

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as fh:
                    saved = json.load(fh)
                # Merge saved data — unknown keys from older schemas are kept
                self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                # Corrupt file — start fresh, don't abort the orchestrator
                pass

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as fh:
            json.dump(self._data, fh, indent=2)

    # ------------------------------------------------------------------ #
    # Pattern management                                                   #
    # ------------------------------------------------------------------ #

    def add_pattern(self, pattern: Pattern) -> None:
        """
        Store a newly discovered pattern, or strengthen an existing one.
        Identical pattern_ids are treated as the same pattern being
        confirmed again — we bump its success count and confidence.
        """
        now = datetime.now(timezone.utc).isoformat()
        pid = pattern.pattern_id

        if pid in self._data["patterns"]:
            existing = self._data["patterns"][pid]
            existing["success_count"] += 1
            existing["last_used"] = now
            sc = existing["success_count"]
            existing["confidence"] = "high" if sc >= 4 else "medium" if sc >= 2 else "low"
        else:
            entry = asdict(pattern)
            entry["created_at"] = now
            entry["last_used"] = now
            self._data["patterns"][pid] = entry
            self._data["total_patterns"] += 1
            target = pattern.improvement_target
            if target in self._data["target_pattern_counts"]:
                self._data["target_pattern_counts"][target] += 1

        self._save()

    def get_patterns(
        self,
        improvement_target: Optional[str] = None,
        pattern_type: Optional[str] = None,
        min_confidence: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return patterns matching the given filters."""
        conf_rank = {"low": 0, "medium": 1, "high": 2}
        min_rank = conf_rank.get(min_confidence or "low", 0)

        results = []
        for p in self._data["patterns"].values():
            if improvement_target and p.get("improvement_target") != improvement_target:
                continue
            if pattern_type and p.get("pattern_type") != pattern_type:
                continue
            if conf_rank.get(p.get("confidence", "low"), 0) < min_rank:
                continue
            results.append(p)
        return results

    def count_patterns(self, improvement_target: Optional[str] = None) -> int:
        return len(self.get_patterns(improvement_target=improvement_target))

    def get_knowledge_boost(self, improvement_target: str) -> float:
        """
        Knowledge boost factor ∈ [0, 1].

        Computed from the confidence-weighted sum of patterns for the given
        target.  Saturates to 1.0 when ~5 high-confidence patterns exist.

        0.0 → no boost (first cycle for this target)
        1.0 → maximum boost (~5 high-confidence patterns)
        """
        patterns = self.get_patterns(improvement_target=improvement_target)
        score = sum(
            {"high": 1.0, "medium": 0.5, "low": 0.2}.get(p.get("confidence", "low"), 0.2)
            for p in patterns
        )
        return min(1.0, score / 5.0)

    # ------------------------------------------------------------------ #
    # Cycle history                                                        #
    # ------------------------------------------------------------------ #

    def record_cycle(self, cycle_dict: Dict[str, Any]) -> None:
        self._data["cycle_history"].append(cycle_dict)
        self._data["total_cycles"] += 1
        self._data["current_metrics"] = cycle_dict.get("metrics_after", {})
        self._save()

    def get_cycle_history(self) -> List[Dict[str, Any]]:
        return list(self._data["cycle_history"])

    def get_current_metrics(self) -> Dict[str, float]:
        return dict(self._data.get("current_metrics", {}))

    def get_total_cycles(self) -> int:
        return int(self._data.get("total_cycles", 0))

    def get_last_n_cycles(self, n: int = 5) -> List[Dict[str, Any]]:
        return self._data["cycle_history"][-n:]

    # ------------------------------------------------------------------ #
    # Insights, models, rules                                              #
    # ------------------------------------------------------------------ #

    def add_insight(self, insight: str, cycle_number: int) -> None:
        self._data["insights"].append(
            {
                "insight": insight,
                "cycle_number": cycle_number,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._save()

    def update_hardware_model(self, model_name: str, model_data: Dict[str, Any]) -> None:
        self._data["hardware_behavior_models"][model_name] = {
            **model_data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def update_improvement_rule(self, rule_name: str, rule_data: Dict[str, Any]) -> None:
        self._data["improvement_rules"][rule_name] = {
            **rule_data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    # ------------------------------------------------------------------ #
    # Trend analysis helpers                                               #
    # ------------------------------------------------------------------ #

    def calculate_improvement_trend(self, last_n: int = 5) -> float:
        """
        Average improvement_rate over the last *n* completed cycles.
        Returns 0.0 if no history is available.
        """
        recent = self.get_last_n_cycles(last_n)
        rates = [c.get("improvement_rate", 0.0) for c in recent if c.get("completed")]
        return sum(rates) / len(rates) if rates else 0.0

    def worst_metric(self, current_metrics: Dict[str, float]) -> str:
        """
        Return the IMPROVEMENT_TARGET whose corresponding metric is
        furthest from its target threshold (relative distance).

        Used to implement intelligent target selection as an alternative to
        the fixed rotation order.
        """
        from .cycle_state import TARGET_THRESHOLDS

        metric_for_target = {
            "success_rate": ("success_rate", False),      # higher-is-better
            "generation_quality": ("quality_score", False),
            "coverage_increase": ("coverage", False),
            "execution_efficiency": ("efficiency", False),
            "error_reduction": ("error_rate", True),      # lower-is-better
        }

        worst_target = "coverage_increase"
        worst_gap = -1.0

        for target, (metric_key, lower_is_better) in metric_for_target.items():
            value = current_metrics.get(metric_key, 0.0)
            threshold = TARGET_THRESHOLDS[metric_key]

            if lower_is_better:
                gap = (value - threshold) / threshold if threshold > 0 else 0.0
            else:
                gap = (threshold - value) / threshold if threshold > 0 else 0.0

            gap = max(0.0, gap)
            if gap > worst_gap:
                worst_gap = gap
                worst_target = target

        return worst_target

    # ------------------------------------------------------------------ #
    # Stats                                                                #
    # ------------------------------------------------------------------ #

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_cycles": self._data["total_cycles"],
            "total_patterns": self._data["total_patterns"],
            "insights_count": len(self._data["insights"]),
            "hardware_models": len(self._data["hardware_behavior_models"]),
            "improvement_rules": len(self._data["improvement_rules"]),
            "patterns_by_target": self._data.get("target_pattern_counts", {}),
        }

    def reset(self) -> None:
        """Wipe all accumulated knowledge. Useful for fresh-start tests."""
        self._data = self._empty_store()
        if self.storage_path.exists():
            self.storage_path.unlink()
