"""
Learning Loop Orchestrator Agent

Coordinates the entire learning cycle, triggers improvements, manages knowledge
updates, and optimizes continuous learning.

Role: Learning Cycle Coordination & System Improvement
Parent System: core-orchestrator
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_framework import MCPServer, Tool

logger = logging.getLogger(__name__)


class CyclePhase(str, Enum):
    """Learning cycle phases"""
    COLLECTION = "collection"         # Continuous data collection
    AGGREGATION = "aggregation"       # Aggregate raw data (5 min)
    ANALYSIS = "parallel_analysis"    # Parallel analysis (5-15 min)
    SYNTHESIS = "synthesis"           # Knowledge synthesis (5-30 min)
    PLANNING = "planning"             # Plan improvements (2-5 min)
    IMPLEMENTATION = "implementation"  # Apply improvements (5-60 min)
    VALIDATION = "validation"         # Validate improvements (ongoing)


class TriggerType(str, Enum):
    """Types of cycle triggers"""
    TIME_BASED = "time_based"
    METRIC_BASED = "metric_based"
    EVENT_BASED = "event_based"
    MANUAL = "manual"


class CycleStatus(str, Enum):
    """Cycle execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class LearningCycle:
    """A learning cycle execution"""
    cycle_id: str
    trigger_type: TriggerType
    trigger_reason: str
    status: CycleStatus
    current_phase: CyclePhase
    started_at: str
    completed_at: Optional[str] = None
    phases_completed: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class LearningLoopOrchestratorAgent(MCPServer):
    """
    Learning cycle coordination agent.

    Responsibilities:
    - Orchestrate multi-agent learning workflows
    - Trigger knowledge synthesis cycles
    - Coordinate pattern analysis and detection
    - Manage model updates and retraining
    - Prioritize improvement actions
    - Monitor learning loop health
    - Implement feedback loops
    - Measure learning effectiveness

    Learning Cycle Phases:
    1. Collection (continuous): Collect voice command interactions
    2. Aggregation (5 min): Aggregate raw data via Context Manager
    3. Parallel Analysis (5-15 min): Performance Monitor, Error Coordinator, Pattern Analyzer
    4. Synthesis (5-30 min): Knowledge Synthesizer aggregates insights
    5. Planning (2-5 min): Prioritize improvement plan
    6. Implementation (5-60 min): Apply improvements to Voice Command Intelligence
    7. Validation (ongoing): Validate via Performance Monitor

    Triggering Conditions:
    - Time-based: every 5 min (quick), hourly (full), daily (comprehensive)
    - Metric-based: error_rate_increase >5%, success_rate_decrease >3%
    - Event-based: user_feedback, new_user, model_degradation, system_update

    Success Metrics:
    - Learning cycle completion rate: >98%
    - Improvement implementation time: <30 minutes
    - Model performance improvement: >2% per cycle
    - System stability: 99.9% uptime
    """

    def __init__(
        self,
        name: str = "learning-loop-orchestrator",
        version: str = "1.0.0",
        voice_command_intelligence: Optional[Any] = None,
        context_manager: Optional[Any] = None,
        performance_monitor: Optional[Any] = None,
        error_coordinator: Optional[Any] = None,
        voice_pattern_analyzer: Optional[Any] = None,
        knowledge_synthesizer: Optional[Any] = None,
    ):
        super().__init__(name, version)

        # Connected agents
        self.voice_command_intelligence = voice_command_intelligence
        self.context_manager = context_manager
        self.performance_monitor = performance_monitor
        self.error_coordinator = error_coordinator
        self.voice_pattern_analyzer = voice_pattern_analyzer
        self.knowledge_synthesizer = knowledge_synthesizer

        # Cycle tracking
        self._cycles: Dict[str, LearningCycle] = {}
        self._current_cycle: Optional[LearningCycle] = None
        self._cycle_history: List[Dict[str, Any]] = []

        # Scheduled tasks
        self._scheduled_tasks: List[asyncio.Task] = []
        self._running = False

        # Trigger thresholds
        self._thresholds = {
            "error_rate_increase": 5.0,  # Trigger if error rate increases by 5%
            "success_rate_decrease": 3.0,  # Trigger if success rate drops by 3%
            "min_samples_for_cycle": 50,  # Minimum samples before triggering
        }

        # Metrics
        self.metrics = {
            "cycles_started": 0,
            "cycles_completed": 0,
            "cycles_failed": 0,
            "improvements_applied": 0,
            "total_cycle_time_ms": 0,
        }

        # Human approval callback
        self._approval_callback: Optional[Callable] = None
        self._auto_approve_low_risk = True

        # Register tools
        self._register_tools()

        logger.info(f"LearningLoopOrchestratorAgent initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register MCP tools"""

        # Tool 1: Execute learning cycle
        self.add_tool(Tool(
            name="execute_learning_cycle",
            description="Execute a complete learning cycle",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_type": {"type": "string", "enum": ["time_based", "metric_based", "event_based", "manual"]},
                    "trigger_reason": {"type": "string"},
                    "skip_phases": {"type": "array", "items": {"type": "string"}},
                    "auto_approve": {"type": "boolean", "default": False},
                },
            },
            handler=self.execute_learning_cycle,
        ))

        # Tool 2: Get cycle status
        self.add_tool(Tool(
            name="get_cycle_status",
            description="Get status of a learning cycle",
            inputSchema={
                "type": "object",
                "properties": {
                    "cycle_id": {"type": "string"},
                },
            },
            handler=self.get_cycle_status,
        ))

        # Tool 3: Trigger quick analysis
        self.add_tool(Tool(
            name="trigger_quick_analysis",
            description="Trigger a quick analysis (5-minute cycle)",
            inputSchema={"type": "object", "properties": {}},
            handler=self.trigger_quick_analysis,
        ))

        # Tool 4: Trigger full synthesis
        self.add_tool(Tool(
            name="trigger_full_synthesis",
            description="Trigger a full synthesis cycle (hourly)",
            inputSchema={"type": "object", "properties": {}},
            handler=self.trigger_full_synthesis,
        ))

        # Tool 5: Get cycle history
        self.add_tool(Tool(
            name="get_cycle_history",
            description="Get history of learning cycles",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10},
                    "status": {"type": "string"},
                },
            },
            handler=self.get_cycle_history,
        ))

        # Tool 6: Check trigger conditions
        self.add_tool(Tool(
            name="check_trigger_conditions",
            description="Check if any trigger conditions are met",
            inputSchema={"type": "object", "properties": {}},
            handler=self.check_trigger_conditions,
        ))

        # Tool 7: Apply improvement
        self.add_tool(Tool(
            name="apply_improvement",
            description="Apply a recommended improvement",
            inputSchema={
                "type": "object",
                "properties": {
                    "recommendation_id": {"type": "string"},
                    "force": {"type": "boolean", "default": False},
                },
                "required": ["recommendation_id"],
            },
            handler=self.apply_improvement,
        ))

        # Tool 8: Get orchestrator metrics
        self.add_tool(Tool(
            name="get_orchestrator_metrics",
            description="Get learning loop orchestrator metrics",
            inputSchema={"type": "object", "properties": {}},
            handler=self.get_orchestrator_metrics,
        ))

        logger.info(f"Registered {len(self.tools)} learning loop orchestrator tools")

    async def execute_learning_cycle(
        self,
        trigger_type: str = "manual",
        trigger_reason: str = "Manual trigger",
        skip_phases: Optional[List[str]] = None,
        auto_approve: bool = False,
    ) -> str:
        """Execute a complete learning cycle"""
        import uuid
        cycle_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        skip_phases = skip_phases or []

        # Create cycle object
        cycle = LearningCycle(
            cycle_id=cycle_id,
            trigger_type=TriggerType(trigger_type),
            trigger_reason=trigger_reason,
            status=CycleStatus.RUNNING,
            current_phase=CyclePhase.COLLECTION,
            started_at=datetime.now().isoformat(),
        )

        self._cycles[cycle_id] = cycle
        self._current_cycle = cycle
        self.metrics["cycles_started"] += 1

        logger.info(f"Starting learning cycle {cycle_id}: {trigger_reason}")

        try:
            # Phase 1: Collection (get recent data)
            if CyclePhase.COLLECTION.value not in skip_phases:
                cycle.current_phase = CyclePhase.COLLECTION
                raw_data = await self._phase_collection()
                cycle.results["collection"] = {"data_points": len(raw_data)}
                cycle.phases_completed.append(CyclePhase.COLLECTION.value)

            # Phase 2: Aggregation
            if CyclePhase.AGGREGATION.value not in skip_phases:
                cycle.current_phase = CyclePhase.AGGREGATION
                aggregated_data = await self._phase_aggregation(raw_data if "raw_data" in dir() else [])
                cycle.results["aggregation"] = {"aggregated": True}
                cycle.phases_completed.append(CyclePhase.AGGREGATION.value)
            else:
                aggregated_data = {}

            # Phase 3: Parallel Analysis
            if CyclePhase.ANALYSIS.value not in skip_phases:
                cycle.current_phase = CyclePhase.ANALYSIS
                analysis_results = await self._phase_parallel_analysis(aggregated_data)
                cycle.results["analysis"] = analysis_results
                cycle.phases_completed.append(CyclePhase.ANALYSIS.value)
            else:
                analysis_results = {}

            # Phase 4: Synthesis
            if CyclePhase.SYNTHESIS.value not in skip_phases:
                cycle.current_phase = CyclePhase.SYNTHESIS
                synthesis_results = await self._phase_synthesis(analysis_results)
                cycle.results["synthesis"] = synthesis_results
                cycle.phases_completed.append(CyclePhase.SYNTHESIS.value)
            else:
                synthesis_results = {}

            # Phase 5: Planning
            if CyclePhase.PLANNING.value not in skip_phases:
                cycle.current_phase = CyclePhase.PLANNING
                improvement_plan = await self._phase_planning(synthesis_results)
                cycle.results["planning"] = improvement_plan
                cycle.phases_completed.append(CyclePhase.PLANNING.value)
            else:
                improvement_plan = {"recommendations": []}

            # Phase 6: Implementation (with optional approval)
            if CyclePhase.IMPLEMENTATION.value not in skip_phases:
                cycle.current_phase = CyclePhase.IMPLEMENTATION

                if auto_approve or self._auto_approve_low_risk:
                    implementation_results = await self._phase_implementation(improvement_plan)
                else:
                    # Request human approval
                    implementation_results = await self._request_approval_and_implement(improvement_plan)

                cycle.results["implementation"] = implementation_results
                cycle.phases_completed.append(CyclePhase.IMPLEMENTATION.value)

            # Phase 7: Validation
            if CyclePhase.VALIDATION.value not in skip_phases:
                cycle.current_phase = CyclePhase.VALIDATION
                validation_results = await self._phase_validation()
                cycle.results["validation"] = validation_results
                cycle.phases_completed.append(CyclePhase.VALIDATION.value)

            # Complete cycle
            cycle.status = CycleStatus.COMPLETED
            cycle.completed_at = datetime.now().isoformat()
            self.metrics["cycles_completed"] += 1

            # Calculate duration
            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000
            self.metrics["total_cycle_time_ms"] += duration_ms

            # Store in history
            self._cycle_history.append({
                "cycle_id": cycle_id,
                "status": cycle.status.value,
                "trigger_type": trigger_type,
                "duration_ms": duration_ms,
                "phases_completed": cycle.phases_completed,
                "timestamp": cycle.started_at,
            })

            logger.info(f"Learning cycle {cycle_id} completed in {duration_ms:.0f}ms")

            return json.dumps({
                "status": "success",
                "cycle_id": cycle_id,
                "duration_ms": duration_ms,
                "phases_completed": cycle.phases_completed,
                "results_summary": {
                    k: {"completed": True} if isinstance(v, dict) else v
                    for k, v in cycle.results.items()
                },
            })

        except Exception as e:
            logger.error(f"Learning cycle {cycle_id} failed: {e}")
            cycle.status = CycleStatus.FAILED
            cycle.errors.append(str(e))
            self.metrics["cycles_failed"] += 1

            return json.dumps({
                "status": "error",
                "cycle_id": cycle_id,
                "error": str(e),
                "phases_completed": cycle.phases_completed,
            })

        finally:
            self._current_cycle = None

    async def _phase_collection(self) -> List[Dict[str, Any]]:
        """Phase 1: Collect recent command data"""
        logger.info("Phase 1: Collection")

        data = []

        # Get from context manager
        if self.context_manager:
            try:
                result = await self.context_manager.query_history(
                    window_hours=1,
                    limit=500,
                )
                result_data = json.loads(result) if isinstance(result, str) else result
                data.extend(result_data.get("results", []))
            except Exception as e:
                logger.warning(f"Failed to collect from context manager: {e}")

        return data

    async def _phase_aggregation(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phase 2: Aggregate raw data"""
        logger.info("Phase 2: Aggregation")

        aggregated = {
            "total_commands": len(raw_data),
            "by_intent": {},
            "by_user": {},
            "success_count": 0,
            "failure_count": 0,
        }

        for item in raw_data:
            data = item.get("data", item)

            # Count by intent
            intent = data.get("intent", "unknown")
            if intent not in aggregated["by_intent"]:
                aggregated["by_intent"][intent] = 0
            aggregated["by_intent"][intent] += 1

            # Count by user
            user_id = data.get("user_id", "unknown")
            if user_id not in aggregated["by_user"]:
                aggregated["by_user"][user_id] = 0
            aggregated["by_user"][user_id] += 1

            # Count success/failure
            if data.get("success", True):
                aggregated["success_count"] += 1
            else:
                aggregated["failure_count"] += 1

        return aggregated

    async def _phase_parallel_analysis(
        self,
        aggregated_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Phase 3: Run parallel analysis"""
        logger.info("Phase 3: Parallel Analysis")

        results = {
            "performance": {},
            "failures": {},
            "patterns": {},
        }

        # Run analyses in parallel
        tasks = []

        # Performance analysis
        if self.performance_monitor:
            tasks.append(("performance", self.performance_monitor.get_dashboard_summary()))

        # Failure analysis
        if self.error_coordinator:
            tasks.append(("failures", self.error_coordinator.get_failure_summary()))

        # Pattern analysis
        if self.voice_pattern_analyzer:
            tasks.append(("patterns", self.voice_pattern_analyzer.detect_patterns()))

        # Execute in parallel
        if tasks:
            async_tasks = [t[1] for t in tasks]
            try:
                completed = await asyncio.gather(*async_tasks, return_exceptions=True)
                for i, (name, _) in enumerate(tasks):
                    if isinstance(completed[i], Exception):
                        logger.warning(f"Analysis {name} failed: {completed[i]}")
                        results[name] = {"error": str(completed[i])}
                    else:
                        results[name] = json.loads(completed[i]) if isinstance(completed[i], str) else completed[i]
            except Exception as e:
                logger.error(f"Parallel analysis failed: {e}")

        return results

    async def _phase_synthesis(
        self,
        analysis_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Phase 4: Synthesize knowledge"""
        logger.info("Phase 4: Synthesis")

        if not self.knowledge_synthesizer:
            return {"skipped": True, "reason": "No knowledge synthesizer available"}

        try:
            result = await self.knowledge_synthesizer.synthesize_knowledge(
                performance_data=analysis_results.get("performance", {}),
                pattern_data=analysis_results.get("patterns", {}),
                failure_data=analysis_results.get("failures", {}),
                analysis_period="last_hour",
            )
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {"error": str(e)}

    async def _phase_planning(
        self,
        synthesis_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Phase 5: Plan improvements"""
        logger.info("Phase 5: Planning")

        recommendations = synthesis_results.get("recommendations", [])

        # Prioritize recommendations
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        prioritized = sorted(
            recommendations,
            key=lambda r: (
                priority_order.get(r.get("priority", "low"), 3),
                -r.get("estimated_impact", 0)
            )
        )

        return {
            "recommendations": prioritized,
            "total_recommendations": len(prioritized),
            "critical_count": sum(1 for r in prioritized if r.get("priority") == "critical"),
            "auto_approvable": sum(
                1 for r in prioritized
                if r.get("priority") in ["low", "medium"] and r.get("implementation_effort") == "low"
            ),
        }

    async def _phase_implementation(
        self,
        improvement_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Phase 6: Implement improvements"""
        logger.info("Phase 6: Implementation")

        implemented = []
        skipped = []

        for rec in improvement_plan.get("recommendations", [])[:5]:  # Top 5
            try:
                # Check if safe to auto-implement
                if rec.get("implementation_effort") == "low" and rec.get("priority") != "critical":
                    # Apply improvement
                    result = await self._apply_single_improvement(rec)
                    if result.get("success"):
                        implemented.append(rec.get("recommendation_id"))
                        self.metrics["improvements_applied"] += 1
                    else:
                        skipped.append({"id": rec.get("recommendation_id"), "reason": result.get("error")})
                else:
                    skipped.append({"id": rec.get("recommendation_id"), "reason": "Requires manual review"})
            except Exception as e:
                skipped.append({"id": rec.get("recommendation_id"), "reason": str(e)})

        return {
            "implemented": implemented,
            "skipped": skipped,
            "total_implemented": len(implemented),
        }

    async def _request_approval_and_implement(
        self,
        improvement_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Request human approval before implementing"""
        logger.info("Requesting approval for improvements")

        if self._approval_callback:
            try:
                approved = await self._approval_callback(improvement_plan["recommendations"])
                if approved:
                    return await self._phase_implementation(improvement_plan)
            except Exception as e:
                logger.error(f"Approval callback failed: {e}")

        # Default: Log for manual review
        return {
            "awaiting_approval": True,
            "recommendations": improvement_plan.get("recommendations", []),
            "message": "Recommendations logged for manual review",
        }

    async def _apply_single_improvement(
        self,
        recommendation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply a single improvement recommendation"""
        rec_id = recommendation.get("recommendation_id", "unknown")
        logger.info(f"Applying improvement: {rec_id}")

        # Update recommendation status
        if self.knowledge_synthesizer:
            try:
                await self.knowledge_synthesizer.update_recommendation_status(
                    recommendation_id=rec_id,
                    status="implemented",
                    notes="Auto-implemented by learning loop",
                )
            except Exception as e:
                logger.warning(f"Failed to update recommendation status: {e}")

        return {"success": True, "recommendation_id": rec_id}

    async def _phase_validation(self) -> Dict[str, Any]:
        """Phase 7: Validate improvements"""
        logger.info("Phase 7: Validation")

        if not self.performance_monitor:
            return {"skipped": True, "reason": "No performance monitor available"}

        try:
            result = await self.performance_monitor.validate_improvements()
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return {"error": str(e)}

    async def get_cycle_status(self, cycle_id: Optional[str] = None) -> str:
        """Get status of a learning cycle"""
        if cycle_id and cycle_id in self._cycles:
            cycle = self._cycles[cycle_id]
            return json.dumps({
                "status": "success",
                "cycle": {
                    "cycle_id": cycle.cycle_id,
                    "status": cycle.status.value,
                    "current_phase": cycle.current_phase.value,
                    "phases_completed": cycle.phases_completed,
                    "started_at": cycle.started_at,
                    "completed_at": cycle.completed_at,
                    "errors": cycle.errors,
                },
            })

        if self._current_cycle:
            cycle = self._current_cycle
            return json.dumps({
                "status": "success",
                "cycle": {
                    "cycle_id": cycle.cycle_id,
                    "status": cycle.status.value,
                    "current_phase": cycle.current_phase.value,
                    "phases_completed": cycle.phases_completed,
                    "started_at": cycle.started_at,
                },
            })

        return json.dumps({
            "status": "no_active_cycle",
            "message": "No active learning cycle",
        })

    async def trigger_quick_analysis(self) -> str:
        """Trigger a quick 5-minute analysis cycle"""
        return await self.execute_learning_cycle(
            trigger_type="time_based",
            trigger_reason="Quick 5-minute analysis",
            skip_phases=["implementation"],
            auto_approve=False,
        )

    async def trigger_full_synthesis(self) -> str:
        """Trigger a full synthesis cycle"""
        return await self.execute_learning_cycle(
            trigger_type="time_based",
            trigger_reason="Full hourly synthesis",
            auto_approve=True,
        )

    async def get_cycle_history(
        self,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> str:
        """Get history of learning cycles"""
        history = self._cycle_history.copy()

        if status:
            history = [h for h in history if h.get("status") == status]

        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return json.dumps({
            "status": "success",
            "history": history[:limit],
            "total_cycles": len(self._cycle_history),
        })

    async def check_trigger_conditions(self) -> str:
        """Check if any trigger conditions are met"""
        conditions_met = []

        # Check with performance monitor
        if self.performance_monitor:
            try:
                metrics_result = await self.performance_monitor.get_dashboard_summary()
                metrics = json.loads(metrics_result) if isinstance(metrics_result, str) else metrics_result

                cmd_metrics = metrics.get("command_metrics", {})
                success_rate = cmd_metrics.get("success_rate_percentage", 100)
                error_rate = 100 - success_rate

                # Check error rate threshold
                if error_rate > self._thresholds["error_rate_increase"]:
                    conditions_met.append({
                        "type": "metric_based",
                        "reason": f"Error rate ({error_rate:.1f}%) exceeds threshold",
                        "priority": "high",
                    })

                # Check success rate threshold
                if success_rate < (100 - self._thresholds["success_rate_decrease"]):
                    conditions_met.append({
                        "type": "metric_based",
                        "reason": f"Success rate ({success_rate:.1f}%) below threshold",
                        "priority": "high",
                    })

            except Exception as e:
                logger.warning(f"Failed to check metrics: {e}")

        # Check for active alerts
        if self.performance_monitor:
            try:
                alerts_result = await self.performance_monitor.get_active_alerts()
                alerts = json.loads(alerts_result) if isinstance(alerts_result, str) else alerts_result

                critical_count = alerts.get("critical_count", 0)
                if critical_count > 0:
                    conditions_met.append({
                        "type": "event_based",
                        "reason": f"{critical_count} critical alerts active",
                        "priority": "critical",
                    })

            except Exception as e:
                logger.warning(f"Failed to check alerts: {e}")

        return json.dumps({
            "status": "success",
            "conditions_met": conditions_met,
            "should_trigger": len(conditions_met) > 0,
            "highest_priority": max(
                (c.get("priority", "low") for c in conditions_met),
                default="none",
                key=lambda p: {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(p, 0)
            ),
        })

    async def apply_improvement(
        self,
        recommendation_id: str,
        force: bool = False,
    ) -> str:
        """Apply a specific improvement recommendation"""
        # Get recommendation details
        if self.knowledge_synthesizer:
            try:
                recs_result = await self.knowledge_synthesizer.get_recommendations(status="pending")
                recs = json.loads(recs_result) if isinstance(recs_result, str) else recs_result

                target_rec = None
                for rec in recs.get("recommendations", []):
                    if rec.get("recommendation_id") == recommendation_id:
                        target_rec = rec
                        break

                if not target_rec:
                    return json.dumps({
                        "status": "error",
                        "error": f"Recommendation not found: {recommendation_id}",
                    })

                # Apply improvement
                result = await self._apply_single_improvement(target_rec)
                self.metrics["improvements_applied"] += 1

                return json.dumps({
                    "status": "success",
                    "recommendation_id": recommendation_id,
                    "applied": True,
                })

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "error": str(e),
                })

        return json.dumps({
            "status": "error",
            "error": "No knowledge synthesizer available",
        })

    async def get_orchestrator_metrics(self) -> str:
        """Get learning loop orchestrator metrics"""
        avg_cycle_time = (
            self.metrics["total_cycle_time_ms"] / self.metrics["cycles_completed"]
            if self.metrics["cycles_completed"] > 0 else 0
        )

        return json.dumps({
            "status": "success",
            "metrics": {
                "cycles_started": self.metrics["cycles_started"],
                "cycles_completed": self.metrics["cycles_completed"],
                "cycles_failed": self.metrics["cycles_failed"],
                "completion_rate": (
                    self.metrics["cycles_completed"] / self.metrics["cycles_started"]
                    if self.metrics["cycles_started"] > 0 else 0
                ),
                "improvements_applied": self.metrics["improvements_applied"],
                "average_cycle_time_ms": avg_cycle_time,
                "current_cycle_active": self._current_cycle is not None,
            },
        })


# Test/demo
if __name__ == "__main__":
    async def main():
        agent = LearningLoopOrchestratorAgent()

        # Execute a learning cycle
        result = await agent.execute_learning_cycle(
            trigger_type="manual",
            trigger_reason="Test execution",
            skip_phases=["implementation", "validation"],
        )
        print("Cycle result:", json.dumps(json.loads(result), indent=2))

        # Get metrics
        metrics = await agent.get_orchestrator_metrics()
        print("Metrics:", json.dumps(json.loads(metrics), indent=2))

    asyncio.run(main())
