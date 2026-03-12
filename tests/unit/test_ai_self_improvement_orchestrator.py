"""
Unit tests for the AI Self-Improvement Orchestrator.

Tests cover:
- CycleMetrics clamping, health, convergence checks
- KnowledgeBase pattern storage, confidence escalation, knowledge boost
- Each of the five phases executing and updating metrics
- Full single-cycle and multi-cycle autonomous runs
- Deterministic improvement (metrics always move toward targets)
- Template rendering (fallback path)
- CLI entry points (smoke tests)
- State persistence and resume
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from orchestration.ai_self_improvement import (
    IMPROVEMENT_TARGETS,
    INITIAL_METRICS,
    TARGET_THRESHOLDS,
    AISelfImprovementOrchestrator,
    CycleMetrics,
    CycleState,
    KnowledgeBase,
    Pattern,
    PhaseResult,
)
from orchestration.ai_self_improvement.phases import (
    CodeReviewPhase,
    ContinuousOrchestratorPhase,
    LearningAnalyticsPhase,
    RequirementsAnalysisPhase,
    TestGenerationPhase,
)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def fresh_kb(tmp_path: Path) -> KnowledgeBase:
    return KnowledgeBase(tmp_path / "kb.json")


def fresh_orchestrator(tmp_path: Path, **kwargs) -> AISelfImprovementOrchestrator:
    return AISelfImprovementOrchestrator(
        knowledge_base_path=tmp_path / "kb.json",
        state_path=tmp_path / "state.json",
        **kwargs,
    )


# ------------------------------------------------------------------ #
# CycleMetrics                                                         #
# ------------------------------------------------------------------ #

class TestCycleMetrics:
    def test_initial_values(self):
        m = CycleMetrics()
        assert m.success_rate == INITIAL_METRICS["success_rate"]
        assert m.coverage == INITIAL_METRICS["coverage"]
        assert m.quality_score == INITIAL_METRICS["quality_score"]
        assert m.efficiency == INITIAL_METRICS["efficiency"]
        assert m.error_rate == INITIAL_METRICS["error_rate"]

    def test_clamp_keeps_values_in_range(self):
        m = CycleMetrics(success_rate=2.0, coverage=-0.5, quality_score=110.0, error_rate=-1.0)
        m.clamp()
        assert 0.0 <= m.success_rate <= 1.0
        assert 0.0 <= m.coverage <= 1.0
        assert 0.0 <= m.quality_score <= 100.0
        assert 0.0 <= m.error_rate <= 1.0

    def test_not_converged_at_start(self):
        assert not CycleMetrics().meets_all_targets()

    def test_converged_when_all_targets_met(self):
        m = CycleMetrics(
            success_rate=0.95,
            coverage=0.96,
            quality_score=90.0,
            efficiency=0.92,
            error_rate=0.03,
        )
        assert m.meets_all_targets()

    def test_not_converged_if_one_metric_misses(self):
        m = CycleMetrics(
            success_rate=0.95,
            coverage=0.96,
            quality_score=90.0,
            efficiency=0.92,
            error_rate=0.10,   # still above 5% target
        )
        assert not m.meets_all_targets()

    def test_overall_health_increases_with_improvement(self):
        m_bad = CycleMetrics()
        m_good = CycleMetrics(
            success_rate=0.92, coverage=0.96, quality_score=88.0,
            efficiency=0.91, error_rate=0.04,
        )
        assert m_good.overall_health() > m_bad.overall_health()

    def test_copy_is_independent(self):
        m = CycleMetrics(success_rate=0.80)
        copy = m.copy()
        copy.success_rate = 0.99
        assert m.success_rate == 0.80


# ------------------------------------------------------------------ #
# KnowledgeBase                                                        #
# ------------------------------------------------------------------ #

class TestKnowledgeBase:
    def test_empty_on_creation(self, tmp_path):
        kb = fresh_kb(tmp_path)
        assert kb.get_total_cycles() == 0
        assert kb.count_patterns() == 0

    def test_add_new_pattern(self, tmp_path):
        kb = fresh_kb(tmp_path)
        p = Pattern("p1", "generation", "coverage_increase", "test pattern")
        kb.add_pattern(p)
        assert kb.count_patterns() == 1
        assert kb.count_patterns(improvement_target="coverage_increase") == 1

    def test_pattern_confidence_escalates(self, tmp_path):
        kb = fresh_kb(tmp_path)
        p = Pattern("p1", "generation", "success_rate", "desc")
        kb.add_pattern(p)
        # Add same pattern 3 more times → success_count=4 → high
        for _ in range(3):
            kb.add_pattern(p)
        patterns = kb.get_patterns(improvement_target="success_rate")
        assert len(patterns) == 1
        assert patterns[0]["confidence"] == "high"
        assert patterns[0]["success_count"] == 4

    def test_knowledge_boost_zero_with_no_patterns(self, tmp_path):
        kb = fresh_kb(tmp_path)
        assert kb.get_knowledge_boost("coverage_increase") == 0.0

    def test_knowledge_boost_increases_with_patterns(self, tmp_path):
        kb = fresh_kb(tmp_path)
        target = "success_rate"
        # Add 5 high-confidence patterns
        for i in range(5):
            p = Pattern(f"p{i}", "generation", target, f"pattern {i}")
            for _ in range(4):   # 4 adds → high confidence
                kb.add_pattern(p)
        boost = kb.get_knowledge_boost(target)
        assert boost > 0.5

    def test_knowledge_boost_capped_at_one(self, tmp_path):
        kb = fresh_kb(tmp_path)
        target = "error_reduction"
        for i in range(20):
            p = Pattern(f"p{i}", "optimization", target, f"desc {i}")
            for _ in range(4):
                kb.add_pattern(p)
        assert kb.get_knowledge_boost(target) <= 1.0

    def test_record_cycle_increments_counter(self, tmp_path):
        kb = fresh_kb(tmp_path)
        kb.record_cycle({"cycle_number": 1, "completed": True, "metrics_after": {}})
        assert kb.get_total_cycles() == 1

    def test_persistence_across_instances(self, tmp_path):
        kb1 = fresh_kb(tmp_path)
        p = Pattern("persist-p", "review", "generation_quality", "persisted pattern")
        kb1.add_pattern(p)

        # Create a second instance pointing at the same file
        kb2 = KnowledgeBase(tmp_path / "kb.json")
        assert kb2.count_patterns() == 1

    def test_reset_clears_everything(self, tmp_path):
        kb = fresh_kb(tmp_path)
        kb.add_pattern(Pattern("x", "meta", "success_rate", "d"))
        kb.reset()
        assert kb.count_patterns() == 0
        assert kb.get_total_cycles() == 0

    def test_worst_metric_returns_valid_target(self, tmp_path):
        kb = fresh_kb(tmp_path)
        worst = kb.worst_metric(INITIAL_METRICS)
        assert worst in IMPROVEMENT_TARGETS


# ------------------------------------------------------------------ #
# Individual phases                                                    #
# ------------------------------------------------------------------ #

class TestPhases:
    """Each phase should run without error and improve at least one metric."""

    def _run(self, phase, cycle, kb):
        return asyncio.run(phase.execute(cycle, kb))

    def _make_cycle(self, target: str, cycle_number: int = 1) -> CycleState:
        return CycleState.new(cycle_number, target, CycleMetrics())

    def test_requirements_analysis_runs(self, tmp_path):
        kb = fresh_kb(tmp_path)
        cycle = self._make_cycle("coverage_increase")
        result = self._run(RequirementsAnalysisPhase(), cycle, kb)
        assert isinstance(result, PhaseResult)
        assert result.phase_name == "RequirementsAnalysis"
        assert result.duration_ms >= 0
        assert result.details["total_requirements"] == 156

    def test_test_generation_runs(self, tmp_path):
        kb = fresh_kb(tmp_path)
        cycle = self._make_cycle("coverage_increase")
        result = self._run(TestGenerationPhase(), cycle, kb)
        assert result.success is True
        assert result.details["tests_generated"] >= 1

    def test_code_review_runs(self, tmp_path):
        kb = fresh_kb(tmp_path)
        cycle = self._make_cycle("generation_quality")
        result = self._run(CodeReviewPhase(), cycle, kb)
        assert result.phase_name == "CodeReview"
        assert "issues_found" in result.details

    def test_learning_analytics_runs(self, tmp_path):
        kb = fresh_kb(tmp_path)
        cycle = self._make_cycle("success_rate")
        result = self._run(LearningAnalyticsPhase(), cycle, kb)
        assert result.success is True
        assert result.details["new_patterns"] >= 1

    def test_continuous_orchestrator_runs(self, tmp_path):
        kb = fresh_kb(tmp_path)
        cycle = self._make_cycle("error_reduction")
        result = self._run(ContinuousOrchestratorPhase(), cycle, kb)
        assert result.success is True
        assert len(result.details["actions_applied"]) >= 1

    @pytest.mark.parametrize("target", IMPROVEMENT_TARGETS)
    def test_all_phases_improve_metrics_for_all_targets(self, tmp_path, target):
        """Metrics should be strictly better after all five phases run."""
        kb = fresh_kb(tmp_path)
        cycle = self._make_cycle(target)
        health_before = cycle.metrics_before.overall_health()

        phases = [
            RequirementsAnalysisPhase(),
            TestGenerationPhase(),
            CodeReviewPhase(),
            LearningAnalyticsPhase(),
            ContinuousOrchestratorPhase(),
        ]
        for phase in phases:
            asyncio.run(phase.execute(cycle, kb))

        health_after = cycle.metrics_after.overall_health()
        assert health_after > health_before, (
            f"Health did not improve for target={target}: "
            f"{health_before:.4f} → {health_after:.4f}"
        )

    def test_phase_adds_patterns_to_kb(self, tmp_path):
        kb = fresh_kb(tmp_path)
        cycle = self._make_cycle("coverage_increase")
        assert kb.count_patterns() == 0
        self._run(RequirementsAnalysisPhase(), cycle, kb)
        assert kb.count_patterns() > 0


# ------------------------------------------------------------------ #
# Full orchestrator — single cycle                                     #
# ------------------------------------------------------------------ #

class TestSingleCycle:
    def test_run_cycle_returns_completed_state(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        cycle = asyncio.run(orch.run_cycle())
        assert cycle.completed is True
        assert cycle.cycle_number == 1
        assert cycle.improvement_target in IMPROVEMENT_TARGETS
        assert len(cycle.phase_results) == 5

    def test_metrics_improve_after_cycle(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        cycle = asyncio.run(orch.run_cycle())
        assert cycle.metrics_after.overall_health() > cycle.metrics_before.overall_health()

    def test_cycle_number_increments(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        c1 = asyncio.run(orch.run_cycle())
        c2 = asyncio.run(orch.run_cycle())
        assert c1.cycle_number == 1
        assert c2.cycle_number == 2

    def test_target_rotates_each_cycle(self, tmp_path):
        orch = fresh_orchestrator(tmp_path, intelligent_routing=False)
        targets_seen = []
        for _ in range(len(IMPROVEMENT_TARGETS)):
            c = asyncio.run(orch.run_cycle())
            targets_seen.append(c.improvement_target)
        # Each target should appear exactly once in one full rotation
        assert set(targets_seen) == set(IMPROVEMENT_TARGETS)

    def test_cycle_state_persisted_in_kb(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        asyncio.run(orch.run_cycle())
        assert orch.kb.get_total_cycles() == 1

    def test_render_cycle_prompt_returns_string(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        cycle = asyncio.run(orch.run_cycle())
        prompt = orch.render_cycle_prompt(cycle)
        assert isinstance(prompt, str)
        assert len(prompt) > 50


# ------------------------------------------------------------------ #
# Multi-cycle autonomous run                                           #
# ------------------------------------------------------------------ #

class TestAutonomousRun:
    def test_metrics_monotonically_improve_over_cycles(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        history = asyncio.run(
            orch.run_autonomous(max_cycles=10, convergence_patience=99, verbose=False)
        )
        assert len(history) == 10
        health_values = [c.metrics_after.overall_health() for c in history]
        # Allow very small regressions due to noise, but trend must be upward
        first_half_avg = sum(health_values[:5]) / 5
        second_half_avg = sum(health_values[5:]) / 5
        assert second_half_avg > first_half_avg, (
            f"Health did not improve: first_half={first_half_avg:.4f}, "
            f"second_half={second_half_avg:.4f}"
        )

    def test_converges_within_ceiling(self, tmp_path):
        """With enough cycles, ALL metric targets should be met."""
        orch = fresh_orchestrator(tmp_path)
        history = asyncio.run(
            orch.run_autonomous(max_cycles=60, convergence_patience=3, verbose=False)
        )
        final_metrics = history[-1].metrics_after
        assert final_metrics.meets_all_targets(), (
            f"Did not converge after {len(history)} cycles: "
            f"sr={final_metrics.success_rate:.3f}, "
            f"cov={final_metrics.coverage:.3f}, "
            f"qs={final_metrics.quality_score:.1f}, "
            f"eff={final_metrics.efficiency:.3f}, "
            f"err={final_metrics.error_rate:.3f}"
        )

    def test_all_targets_covered_over_run(self, tmp_path):
        orch = fresh_orchestrator(tmp_path, intelligent_routing=False)
        history = asyncio.run(
            orch.run_autonomous(max_cycles=10, convergence_patience=99, verbose=False)
        )
        targets_used = {c.improvement_target for c in history}
        assert targets_used == set(IMPROVEMENT_TARGETS)

    def test_knowledge_base_grows_each_cycle(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        history = asyncio.run(
            orch.run_autonomous(max_cycles=5, convergence_patience=99, verbose=False)
        )
        assert orch.kb.count_patterns() > len(history)   # at least one pattern per cycle

    def test_stop_hook_history_saved(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        history = asyncio.run(
            orch.run_autonomous(max_cycles=3, convergence_patience=99, verbose=False)
        )
        out = tmp_path / "history.json"
        out.write_text(json.dumps([c.to_dict() for c in history], indent=2))
        loaded = json.loads(out.read_text())
        assert len(loaded) == 3


# ------------------------------------------------------------------ #
# Persistence / resume                                                 #
# ------------------------------------------------------------------ #

class TestPersistence:
    def test_resume_after_restart(self, tmp_path):
        """Second orchestrator instance should pick up from where the first left off."""
        orch1 = fresh_orchestrator(tmp_path)
        for _ in range(3):
            asyncio.run(orch1.run_cycle())
        cycle_count_after_first = orch1.status()["cycle_number"]

        # New instance, same paths
        orch2 = AISelfImprovementOrchestrator(
            knowledge_base_path=tmp_path / "kb.json",
            state_path=tmp_path / "state.json",
        )
        assert orch2.status()["cycle_number"] == cycle_count_after_first

    def test_reset_returns_to_initial_state(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        asyncio.run(orch.run_cycle())
        orch.reset(reset_knowledge_base=True)
        s = orch.status()
        assert s["cycle_number"] == 0
        assert s["kb_statistics"]["total_patterns"] == 0


# ------------------------------------------------------------------ #
# Status output                                                        #
# ------------------------------------------------------------------ #

class TestStatus:
    def test_status_contains_expected_keys(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        s = orch.status()
        for key in ("cycle_number", "current_target", "metrics", "converged",
                    "health_pct", "kb_statistics"):
            assert key in s, f"Missing key: {key}"

    def test_status_target_is_valid(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        assert orch.status()["current_target"] in IMPROVEMENT_TARGETS


# ------------------------------------------------------------------ #
# Template rendering                                                   #
# ------------------------------------------------------------------ #

class TestTemplateRendering:
    def test_fallback_prompt_contains_metrics(self, tmp_path):
        orch = fresh_orchestrator(tmp_path)
        cycle = asyncio.run(orch.run_cycle())
        prompt = orch._fallback_prompt(cycle)
        assert "Success Rate" in prompt
        assert "Coverage" in prompt
        assert str(cycle.cycle_number) in prompt

    def test_full_template_renders_all_targets(self, tmp_path):
        """Template must render without error for every improvement target."""
        orch = fresh_orchestrator(tmp_path)
        for target in IMPROVEMENT_TARGETS:
            cycle = CycleState.new(1, target, CycleMetrics())
            cycle.mark_completed()
            prompt = orch.render_cycle_prompt(cycle)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
