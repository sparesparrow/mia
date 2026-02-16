"""
Error Coordinator Agent

Analyzes command failures, identifies root causes, coordinates error recovery,
and drives systematic improvements.

Role: Failure Analysis & Error Recovery
Parent System: learning_loop_orchestrator
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_framework import MCPServer, Tool

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """Classification of failure types"""
    RECOGNITION = "recognition"      # Voice not recognized/misinterpreted
    INTERPRETATION = "interpretation"  # Intent/parameters wrong
    EXECUTION = "execution"          # Command failed to execute
    RESPONSE = "response"            # Response generation failed


class RecoveryStrategy(str, Enum):
    """Recovery strategies"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CLARIFY = "clarify"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class FailureReport:
    """Report of a command failure"""
    failure_id: str
    command_id: str
    failure_type: FailureType
    error_message: str
    voice_text: str
    interpreted_intent: Optional[str]
    actual_intent: Optional[str]
    user_feedback: Optional[str]
    timestamp: str
    user_id: str
    device_type: str = "unknown"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureAnalysis:
    """Analysis of a failure"""
    analysis_id: str
    failure_id: str
    failure_classification: FailureType
    root_cause: str
    impact_assessment: Dict[str, Any]
    recommended_actions: List[Dict[str, Any]]
    priority_level: str
    recovery_plan: Dict[str, Any]
    pattern_detected: Optional[str] = None


class FailurePatternDetector:
    """Detects recurring failure patterns"""

    def __init__(self, pattern_threshold: int = 3, time_window_hours: int = 24):
        self.pattern_threshold = pattern_threshold
        self.time_window_hours = time_window_hours
        self._failures: List[FailureReport] = []
        self._detected_patterns: Dict[str, Dict[str, Any]] = {}

    def add_failure(self, failure: FailureReport) -> Optional[str]:
        """Add failure and check for patterns"""
        self._failures.append(failure)

        # Clean old failures
        cutoff = datetime.now() - timedelta(hours=self.time_window_hours)
        self._failures = [
            f for f in self._failures
            if datetime.fromisoformat(f.timestamp) > cutoff
        ]

        # Check for patterns
        return self._detect_patterns(failure)

    def _detect_patterns(self, recent_failure: FailureReport) -> Optional[str]:
        """Detect patterns in recent failures"""
        patterns_found = []

        # Pattern 1: Same failure type from same user
        user_type_failures = [
            f for f in self._failures
            if f.user_id == recent_failure.user_id
            and f.failure_type == recent_failure.failure_type
        ]
        if len(user_type_failures) >= self.pattern_threshold:
            pattern_id = f"user_{recent_failure.user_id}_{recent_failure.failure_type.value}"
            self._detected_patterns[pattern_id] = {
                "type": "user_specific",
                "failure_type": recent_failure.failure_type.value,
                "user_id": recent_failure.user_id,
                "count": len(user_type_failures),
                "detected_at": datetime.now().isoformat(),
            }
            patterns_found.append(pattern_id)

        # Pattern 2: Same interpreted intent failing
        if recent_failure.interpreted_intent:
            intent_failures = [
                f for f in self._failures
                if f.interpreted_intent == recent_failure.interpreted_intent
            ]
            if len(intent_failures) >= self.pattern_threshold:
                pattern_id = f"intent_{recent_failure.interpreted_intent}"
                self._detected_patterns[pattern_id] = {
                    "type": "intent_specific",
                    "intent": recent_failure.interpreted_intent,
                    "count": len(intent_failures),
                    "detected_at": datetime.now().isoformat(),
                }
                patterns_found.append(pattern_id)

        # Pattern 3: Similar voice text patterns (simple substring match)
        similar_text_failures = [
            f for f in self._failures
            if self._text_similarity(f.voice_text, recent_failure.voice_text) > 0.6
        ]
        if len(similar_text_failures) >= self.pattern_threshold:
            pattern_id = f"text_pattern_{hash(recent_failure.voice_text[:20])}"
            self._detected_patterns[pattern_id] = {
                "type": "text_pattern",
                "sample_text": recent_failure.voice_text[:50],
                "count": len(similar_text_failures),
                "detected_at": datetime.now().isoformat(),
            }
            patterns_found.append(pattern_id)

        return patterns_found[0] if patterns_found else None

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def get_patterns(self) -> Dict[str, Dict[str, Any]]:
        return self._detected_patterns


class ErrorCoordinatorAgent(MCPServer):
    """
    Failure analysis and error recovery agent.

    Responsibilities:
    - Capture command failure details
    - Classify failure types and root causes
    - Detect failure patterns and trends
    - Generate failure analysis reports
    - Recommend corrective actions
    - Coordinate error recovery procedures
    - Track failure remediation effectiveness
    - Identify systematic issues

    Failure Classifications:
    - Recognition: Voice not recognized (accent, noise, pronunciation)
    - Interpretation: Wrong intent/parameters (ambiguous, context miss)
    - Execution: Service unavailable, permission denied, timeout
    - Response: TTS error, formatting error

    Success Metrics:
    - Failure classification accuracy: >93%
    - Root cause identification rate: >85%
    - Recovery success rate: >80%
    - Remediation effectiveness: >75%
    """

    def __init__(
        self,
        name: str = "error-coordinator",
        version: str = "1.0.0",
        context_manager: Optional[Any] = None,
        message_bus: Optional[Any] = None,
    ):
        super().__init__(name, version)

        self.context_manager = context_manager
        self.message_bus = message_bus

        # Pattern detector
        self._pattern_detector = FailurePatternDetector()

        # Failure registry
        self._failures: Dict[str, FailureReport] = {}
        self._analyses: Dict[str, FailureAnalysis] = {}

        # Metrics
        self.metrics = {
            "total_failures": 0,
            "failures_by_type": defaultdict(int),
            "recoveries_attempted": 0,
            "recoveries_successful": 0,
            "patterns_detected": 0,
        }

        # Recovery handlers
        self._recovery_handlers: Dict[FailureType, List[Dict[str, Any]]] = {
            FailureType.RECOGNITION: [
                {"strategy": RecoveryStrategy.RETRY, "description": "Retry with noise filtering"},
                {"strategy": RecoveryStrategy.CLARIFY, "description": "Ask user to repeat"},
            ],
            FailureType.INTERPRETATION: [
                {"strategy": RecoveryStrategy.CLARIFY, "description": "Ask for clarification"},
                {"strategy": RecoveryStrategy.FALLBACK, "description": "Use broader intent matching"},
            ],
            FailureType.EXECUTION: [
                {"strategy": RecoveryStrategy.RETRY, "description": "Retry with exponential backoff"},
                {"strategy": RecoveryStrategy.FALLBACK, "description": "Use alternative service"},
                {"strategy": RecoveryStrategy.ESCALATE, "description": "Notify user of issue"},
            ],
            FailureType.RESPONSE: [
                {"strategy": RecoveryStrategy.FALLBACK, "description": "Use simple text response"},
                {"strategy": RecoveryStrategy.RETRY, "description": "Retry TTS"},
            ],
        }

        # Register tools
        self._register_tools()

        logger.info(f"ErrorCoordinatorAgent initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register MCP tools"""

        # Tool 1: Report failure
        self.add_tool(Tool(
            name="report_failure",
            description="Report a command failure for analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {"type": "string"},
                    "failure_type": {"type": "string", "enum": ["recognition", "interpretation", "execution", "response"]},
                    "error_message": {"type": "string"},
                    "voice_text": {"type": "string"},
                    "interpreted_intent": {"type": "string"},
                    "actual_intent": {"type": "string"},
                    "user_feedback": {"type": "string"},
                    "user_id": {"type": "string"},
                    "device_type": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["command_id", "failure_type", "error_message", "voice_text", "user_id"],
            },
            handler=self.report_failure,
        ))

        # Tool 2: Analyze failure
        self.add_tool(Tool(
            name="analyze_failure",
            description="Analyze a reported failure to determine root cause and recovery",
            inputSchema={
                "type": "object",
                "properties": {
                    "failure_id": {"type": "string"},
                },
                "required": ["failure_id"],
            },
            handler=self.analyze_failure,
        ))

        # Tool 3: Get recovery plan
        self.add_tool(Tool(
            name="get_recovery_plan",
            description="Get recovery plan for a failure",
            inputSchema={
                "type": "object",
                "properties": {
                    "failure_id": {"type": "string"},
                },
                "required": ["failure_id"],
            },
            handler=self.get_recovery_plan,
        ))

        # Tool 4: Execute recovery
        self.add_tool(Tool(
            name="execute_recovery",
            description="Execute recovery for a failure",
            inputSchema={
                "type": "object",
                "properties": {
                    "failure_id": {"type": "string"},
                    "strategy": {"type": "string", "enum": ["retry", "fallback", "clarify", "escalate", "abort"]},
                },
                "required": ["failure_id", "strategy"],
            },
            handler=self.execute_recovery,
        ))

        # Tool 5: Get failure patterns
        self.add_tool(Tool(
            name="get_failure_patterns",
            description="Get detected failure patterns",
            inputSchema={"type": "object", "properties": {}},
            handler=self.get_failure_patterns,
        ))

        # Tool 6: Get failure summary
        self.add_tool(Tool(
            name="get_failure_summary",
            description="Get summary of failures in time window",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_hours": {"type": "integer", "default": 24},
                },
            },
            handler=self.get_failure_summary,
        ))

        # Tool 7: Analyze failures batch
        self.add_tool(Tool(
            name="analyze_failures_batch",
            description="Analyze batch of failures for patterns and insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_hours": {"type": "integer", "default": 1},
                },
            },
            handler=self.analyze_failures_batch,
        ))

        logger.info(f"Registered {len(self.tools)} error coordinator tools")

    async def report_failure(
        self,
        command_id: str,
        failure_type: str,
        error_message: str,
        voice_text: str,
        user_id: str,
        interpreted_intent: Optional[str] = None,
        actual_intent: Optional[str] = None,
        user_feedback: Optional[str] = None,
        device_type: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Report a command failure"""
        import uuid
        failure_id = str(uuid.uuid4())

        failure = FailureReport(
            failure_id=failure_id,
            command_id=command_id,
            failure_type=FailureType(failure_type),
            error_message=error_message,
            voice_text=voice_text,
            interpreted_intent=interpreted_intent,
            actual_intent=actual_intent,
            user_feedback=user_feedback,
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            device_type=device_type,
            context=context or {},
        )

        # Store failure
        self._failures[failure_id] = failure

        # Update metrics
        self.metrics["total_failures"] += 1
        self.metrics["failures_by_type"][failure_type] += 1

        # Check for patterns
        pattern_id = self._pattern_detector.add_failure(failure)
        if pattern_id:
            self.metrics["patterns_detected"] += 1
            logger.warning(f"Failure pattern detected: {pattern_id}")

        # Store in context manager if available
        if self.context_manager:
            try:
                await self.context_manager.store_context(
                    key=f"failure:{failure_id}",
                    data=asdict(failure),
                    layer="historical",
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning(f"Failed to store failure in context: {e}")

        # Publish to message bus
        if self.message_bus:
            try:
                await self.message_bus.publish("stream:command_failed", {
                    "event_type": "failure_reported",
                    "failure_id": failure_id,
                    "failure_type": failure_type,
                    "command_id": command_id,
                    "pattern_detected": pattern_id,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.warning(f"Failed to publish failure event: {e}")

        return json.dumps({
            "status": "success",
            "failure_id": failure_id,
            "pattern_detected": pattern_id,
            "failure_type": failure_type,
        })

    async def analyze_failure(self, failure_id: str) -> str:
        """Analyze a reported failure"""
        if failure_id not in self._failures:
            return json.dumps({
                "status": "error",
                "error": f"Failure not found: {failure_id}",
            })

        failure = self._failures[failure_id]
        import uuid
        analysis_id = str(uuid.uuid4())

        # Determine root cause
        root_cause = self._determine_root_cause(failure)

        # Assess impact
        impact = self._assess_impact(failure)

        # Get recommended actions
        actions = self._get_recommended_actions(failure)

        # Determine priority
        priority = self._determine_priority(failure, impact)

        # Build recovery plan
        recovery_plan = self._build_recovery_plan(failure)

        # Check for patterns
        patterns = self._pattern_detector.get_patterns()
        pattern_match = None
        for pid, pdata in patterns.items():
            if failure.user_id in pid or (failure.interpreted_intent and failure.interpreted_intent in pid):
                pattern_match = pid
                break

        analysis = FailureAnalysis(
            analysis_id=analysis_id,
            failure_id=failure_id,
            failure_classification=failure.failure_type,
            root_cause=root_cause,
            impact_assessment=impact,
            recommended_actions=actions,
            priority_level=priority,
            recovery_plan=recovery_plan,
            pattern_detected=pattern_match,
        )

        self._analyses[analysis_id] = analysis

        return json.dumps({
            "status": "success",
            "analysis": {
                "analysis_id": analysis_id,
                "failure_id": failure_id,
                "failure_classification": failure.failure_type.value,
                "root_cause": root_cause,
                "impact_assessment": impact,
                "recommended_actions": actions,
                "priority_level": priority,
                "recovery_plan": recovery_plan,
                "pattern_detected": pattern_match,
            },
        })

    def _determine_root_cause(self, failure: FailureReport) -> str:
        """Determine the root cause of failure"""
        if failure.failure_type == FailureType.RECOGNITION:
            if "noise" in failure.error_message.lower():
                return "Background noise interference"
            elif "accent" in failure.error_message.lower():
                return "Accent not recognized"
            elif "pronunciation" in failure.error_message.lower():
                return "Pronunciation variation"
            return "Voice recognition failed"

        elif failure.failure_type == FailureType.INTERPRETATION:
            if failure.interpreted_intent and failure.actual_intent:
                return f"Intent misclassified: expected '{failure.actual_intent}', got '{failure.interpreted_intent}'"
            elif "ambiguous" in failure.error_message.lower():
                return "Ambiguous command"
            return "Intent interpretation failed"

        elif failure.failure_type == FailureType.EXECUTION:
            if "timeout" in failure.error_message.lower():
                return "Service timeout"
            elif "unavailable" in failure.error_message.lower():
                return "Service unavailable"
            elif "permission" in failure.error_message.lower():
                return "Permission denied"
            return "Command execution failed"

        elif failure.failure_type == FailureType.RESPONSE:
            if "tts" in failure.error_message.lower():
                return "Text-to-speech error"
            return "Response generation failed"

        return "Unknown root cause"

    def _assess_impact(self, failure: FailureReport) -> Dict[str, Any]:
        """Assess the impact of the failure"""
        # Count similar recent failures
        similar_count = sum(
            1 for f in self._failures.values()
            if f.failure_type == failure.failure_type
            and (datetime.now() - datetime.fromisoformat(f.timestamp)).total_seconds() < 3600
        )

        return {
            "user_affected": failure.user_id,
            "similar_failures_last_hour": similar_count,
            "severity": "high" if similar_count > 5 else "medium" if similar_count > 2 else "low",
            "affects_core_functionality": failure.failure_type in [FailureType.RECOGNITION, FailureType.INTERPRETATION],
        }

    def _get_recommended_actions(self, failure: FailureReport) -> List[Dict[str, Any]]:
        """Get recommended actions for failure"""
        actions = []

        handlers = self._recovery_handlers.get(failure.failure_type, [])
        for i, handler in enumerate(handlers):
            actions.append({
                "priority": i + 1,
                "action": handler["strategy"].value,
                "description": handler["description"],
                "estimated_success_rate": 0.8 - (i * 0.15),
            })

        # Add user-specific actions if pattern detected
        patterns = self._pattern_detector.get_patterns()
        for pid, pdata in patterns.items():
            if failure.user_id in pid:
                actions.append({
                    "priority": len(actions) + 1,
                    "action": "personalize",
                    "description": f"Create personalized handling for user pattern: {pdata['type']}",
                    "estimated_success_rate": 0.7,
                })
                break

        return actions

    def _determine_priority(self, failure: FailureReport, impact: Dict[str, Any]) -> str:
        """Determine priority level"""
        if impact["severity"] == "high" or impact["affects_core_functionality"]:
            return "critical"
        elif impact["severity"] == "medium":
            return "high"
        elif failure.user_feedback:
            return "high"  # User explicitly reported issue
        return "medium"

    def _build_recovery_plan(self, failure: FailureReport) -> Dict[str, Any]:
        """Build recovery plan for failure"""
        handlers = self._recovery_handlers.get(failure.failure_type, [])

        return {
            "primary_strategy": handlers[0]["strategy"].value if handlers else "abort",
            "fallback_strategies": [h["strategy"].value for h in handlers[1:]],
            "clarifying_questions": self._get_clarifying_questions(failure),
            "alternative_interpretations": self._get_alternatives(failure),
            "missing_context_signals": self._identify_missing_context(failure),
        }

    def _get_clarifying_questions(self, failure: FailureReport) -> List[str]:
        """Generate clarifying questions"""
        questions = []

        if failure.failure_type == FailureType.INTERPRETATION:
            questions.append("Could you please rephrase your request?")
            questions.append(f"Did you mean '{failure.interpreted_intent}'?")

        if failure.failure_type == FailureType.RECOGNITION:
            questions.append("I didn't catch that. Could you repeat?")

        return questions

    def _get_alternatives(self, failure: FailureReport) -> List[str]:
        """Get alternative interpretations"""
        alternatives = []

        if failure.interpreted_intent:
            # Suggest related intents
            intent_map = {
                "play_music": ["play_audio", "start_music", "resume_playback"],
                "navigation": ["get_directions", "go_to", "find_route"],
                "climate": ["set_temperature", "adjust_ac", "control_fan"],
            }
            alternatives = intent_map.get(failure.interpreted_intent, [])

        return alternatives

    def _identify_missing_context(self, failure: FailureReport) -> List[str]:
        """Identify missing context signals"""
        missing = []
        context = failure.context

        if "location" not in context:
            missing.append("user_location")
        if "time_of_day" not in context:
            missing.append("time_of_day")
        if "device_state" not in context:
            missing.append("device_state")
        if "recent_commands" not in context:
            missing.append("recent_commands")

        return missing

    async def get_recovery_plan(self, failure_id: str) -> str:
        """Get recovery plan for a failure"""
        if failure_id not in self._failures:
            return json.dumps({
                "status": "error",
                "error": f"Failure not found: {failure_id}",
            })

        failure = self._failures[failure_id]
        plan = self._build_recovery_plan(failure)

        return json.dumps({
            "status": "success",
            "failure_id": failure_id,
            "recovery_plan": plan,
        })

    async def execute_recovery(
        self,
        failure_id: str,
        strategy: str,
    ) -> str:
        """Execute recovery strategy"""
        if failure_id not in self._failures:
            return json.dumps({
                "status": "error",
                "error": f"Failure not found: {failure_id}",
            })

        self.metrics["recoveries_attempted"] += 1

        # Simulate recovery execution
        recovery_success = strategy in ["retry", "fallback", "clarify"]

        if recovery_success:
            self.metrics["recoveries_successful"] += 1

        return json.dumps({
            "status": "success",
            "failure_id": failure_id,
            "strategy_executed": strategy,
            "recovery_successful": recovery_success,
            "message": f"Recovery strategy '{strategy}' executed",
        })

    async def get_failure_patterns(self) -> str:
        """Get detected failure patterns"""
        patterns = self._pattern_detector.get_patterns()

        return json.dumps({
            "status": "success",
            "patterns": patterns,
            "total_patterns": len(patterns),
        })

    async def get_failure_summary(self, window_hours: int = 24) -> str:
        """Get summary of failures in time window"""
        cutoff = datetime.now() - timedelta(hours=window_hours)

        recent_failures = [
            f for f in self._failures.values()
            if datetime.fromisoformat(f.timestamp) > cutoff
        ]

        by_type = defaultdict(int)
        by_user = defaultdict(int)
        by_intent = defaultdict(int)

        for f in recent_failures:
            by_type[f.failure_type.value] += 1
            by_user[f.user_id] += 1
            if f.interpreted_intent:
                by_intent[f.interpreted_intent] += 1

        return json.dumps({
            "status": "success",
            "window_hours": window_hours,
            "total_failures": len(recent_failures),
            "failures_by_type": dict(by_type),
            "top_users_affected": dict(sorted(by_user.items(), key=lambda x: -x[1])[:5]),
            "top_failing_intents": dict(sorted(by_intent.items(), key=lambda x: -x[1])[:5]),
            "patterns_detected": len(self._pattern_detector.get_patterns()),
            "recovery_success_rate": (
                self.metrics["recoveries_successful"] / self.metrics["recoveries_attempted"]
                if self.metrics["recoveries_attempted"] > 0 else 0.0
            ),
        })

    async def analyze_failures_batch(self, window_hours: int = 1) -> str:
        """Analyze batch of failures for patterns and insights"""
        cutoff = datetime.now() - timedelta(hours=window_hours)

        recent_failures = [
            f for f in self._failures.values()
            if datetime.fromisoformat(f.timestamp) > cutoff
        ]

        if not recent_failures:
            return json.dumps({
                "status": "success",
                "message": "No failures in time window",
                "insights": [],
            })

        # Analyze batch
        insights = []

        # Check for spikes
        by_type = defaultdict(int)
        for f in recent_failures:
            by_type[f.failure_type.value] += 1

        for ftype, count in by_type.items():
            if count >= 3:
                insights.append({
                    "type": "failure_spike",
                    "failure_type": ftype,
                    "count": count,
                    "recommendation": f"Investigate {ftype} failures - {count} occurrences in {window_hours}h",
                })

        # Check patterns
        patterns = self._pattern_detector.get_patterns()
        for pid, pdata in patterns.items():
            insights.append({
                "type": "pattern_detected",
                "pattern_id": pid,
                "pattern_data": pdata,
                "recommendation": f"Address recurring pattern: {pdata['type']}",
            })

        return json.dumps({
            "status": "success",
            "window_hours": window_hours,
            "failures_analyzed": len(recent_failures),
            "insights": insights,
            "patterns": patterns,
        })


# Test/demo
if __name__ == "__main__":
    async def main():
        agent = ErrorCoordinatorAgent()

        # Report some failures
        for i in range(5):
            result = await agent.report_failure(
                command_id=f"cmd-{i}",
                failure_type="interpretation" if i % 2 == 0 else "recognition",
                error_message="Intent misclassified" if i % 2 == 0 else "Voice not recognized",
                voice_text=f"play some music track {i}",
                interpreted_intent="play_music",
                actual_intent="play_playlist",
                user_id="user123",
            )
            print(f"Report {i}:", result)

        # Analyze a failure
        result = await agent.analyze_failure(list(agent._failures.keys())[0])
        print("Analysis:", json.dumps(json.loads(result), indent=2))

        # Get patterns
        patterns = await agent.get_failure_patterns()
        print("Patterns:", patterns)

        # Get summary
        summary = await agent.get_failure_summary()
        print("Summary:", json.dumps(json.loads(summary), indent=2))

    asyncio.run(main())
