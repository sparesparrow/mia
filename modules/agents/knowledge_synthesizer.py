"""
Knowledge Synthesizer Agent

Analyzes voice interaction patterns, extracts insights, generates improvement
recommendations, and synthesizes new knowledge from aggregated data.

Role: Pattern Extraction & Knowledge Synthesis
Parent System: learning_loop_orchestrator
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_framework import MCPServer, Tool

logger = logging.getLogger(__name__)


class InsightType(str, Enum):
    """Types of insights"""
    PATTERN = "pattern"           # Detected patterns
    IMPROVEMENT = "improvement"   # Improvement opportunities
    ANOMALY = "anomaly"          # Anomalies detected
    TREND = "trend"              # Trends identified
    RECOMMENDATION = "recommendation"


class ImplementationPriority(str, Enum):
    """Priority levels for recommendations"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Insight:
    """A synthesized insight"""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    confidence: float
    evidence: List[str]
    affected_components: List[str]
    recommendations: List[str]
    priority: ImplementationPriority = ImplementationPriority.MEDIUM


@dataclass
class KnowledgeSynthesis:
    """Complete knowledge synthesis result"""
    synthesis_id: str
    timestamp: str
    analysis_period: str
    data_sources: Dict[str, Any]
    insights: List[Insight]
    recommendations: List[Dict[str, Any]]
    new_patterns: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    implementation_priority: ImplementationPriority
    executive_summary: str


class KnowledgeSynthesizerAgent(MCPServer):
    """
    Pattern extraction and knowledge synthesis agent.

    Responsibilities:
    - Aggregate command patterns from multiple interactions
    - Detect successful command variations and synonyms
    - Identify common user preferences and contexts
    - Generate improvement recommendations
    - Create new training patterns from successful interactions
    - Synthesize domain-specific knowledge
    - Update NLP models with learned patterns

    Input Sources:
    - command_analysis_batch
    - pattern_detection_results
    - user_preference_aggregation
    - success_metrics_summary

    Algorithms:
    - Clustering (command similarity)
    - Frequent pattern mining (command sequences)
    - Recommendation scoring (impact assessment)
    - Confidence calculation (statistical significance)

    Success Metrics:
    - Insight quality: human-verified >85%
    - Recommendation adoption rate: >70%
    - Knowledge synthesis time: <2 minutes per batch
    - Pattern detection accuracy: >88%
    """

    def __init__(
        self,
        name: str = "knowledge-synthesizer",
        version: str = "1.0.0",
        context_manager: Optional[Any] = None,
        performance_monitor: Optional[Any] = None,
        voice_pattern_analyzer: Optional[Any] = None,
        error_coordinator: Optional[Any] = None,
        llm_client: Optional[Any] = None,
    ):
        super().__init__(name, version)

        # Connected agents
        self.context_manager = context_manager
        self.performance_monitor = performance_monitor
        self.voice_pattern_analyzer = voice_pattern_analyzer
        self.error_coordinator = error_coordinator
        self.llm_client = llm_client

        # Knowledge storage
        self._synthesized_knowledge: Dict[str, KnowledgeSynthesis] = {}
        self._insights: List[Insight] = []
        self._recommendation_history: List[Dict[str, Any]] = []

        # Metrics
        self.metrics = {
            "syntheses_completed": 0,
            "insights_generated": 0,
            "recommendations_generated": 0,
            "patterns_created": 0,
        }

        # Register tools
        self._register_tools()

        logger.info(f"KnowledgeSynthesizerAgent initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register MCP tools"""

        # Tool 1: Synthesize knowledge
        self.add_tool(Tool(
            name="synthesize_knowledge",
            description="Synthesize comprehensive knowledge from analysis data",
            inputSchema={
                "type": "object",
                "properties": {
                    "performance_data": {"type": "object"},
                    "pattern_data": {"type": "object"},
                    "failure_data": {"type": "object"},
                    "analysis_period": {"type": "string"},
                    "total_interactions": {"type": "integer"},
                    "baseline_accuracy": {"type": "number"},
                },
                "required": ["performance_data", "pattern_data", "failure_data"],
            },
            handler=self.synthesize_knowledge,
        ))

        # Tool 2: Generate insights
        self.add_tool(Tool(
            name="generate_insights",
            description="Generate insights from analysis data",
            inputSchema={
                "type": "object",
                "properties": {
                    "metrics": {"type": "object"},
                    "patterns": {"type": "array"},
                    "failures": {"type": "array"},
                },
                "required": ["metrics"],
            },
            handler=self.generate_insights,
        ))

        # Tool 3: Generate recommendations
        self.add_tool(Tool(
            name="generate_recommendations",
            description="Generate actionable recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "insights": {"type": "array"},
                    "context": {"type": "object"},
                },
                "required": ["insights"],
            },
            handler=self.generate_recommendations,
        ))

        # Tool 4: Create training patterns
        self.add_tool(Tool(
            name="create_training_patterns",
            description="Create new training patterns from successful interactions",
            inputSchema={
                "type": "object",
                "properties": {
                    "successful_commands": {"type": "array"},
                    "min_confidence": {"type": "number", "default": 0.8},
                },
                "required": ["successful_commands"],
            },
            handler=self.create_training_patterns,
        ))

        # Tool 5: Get synthesis history
        self.add_tool(Tool(
            name="get_synthesis_history",
            description="Get history of knowledge syntheses",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10},
                },
            },
            handler=self.get_synthesis_history,
        ))

        # Tool 6: Get recommendations
        self.add_tool(Tool(
            name="get_recommendations",
            description="Get pending and historical recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "implemented", "rejected", "all"]},
                    "priority": {"type": "string"},
                },
            },
            handler=self.get_recommendations,
        ))

        # Tool 7: Update recommendation status
        self.add_tool(Tool(
            name="update_recommendation_status",
            description="Update status of a recommendation",
            inputSchema={
                "type": "object",
                "properties": {
                    "recommendation_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["implemented", "rejected", "deferred"]},
                    "notes": {"type": "string"},
                },
                "required": ["recommendation_id", "status"],
            },
            handler=self.update_recommendation_status,
        ))

        logger.info(f"Registered {len(self.tools)} knowledge synthesizer tools")

    async def synthesize_knowledge(
        self,
        performance_data: Dict[str, Any],
        pattern_data: Dict[str, Any],
        failure_data: Dict[str, Any],
        analysis_period: str = "last_hour",
        total_interactions: int = 0,
        baseline_accuracy: float = 0.0,
    ) -> str:
        """Synthesize comprehensive knowledge from analysis data"""
        import uuid
        synthesis_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        try:
            # Generate insights
            insights_result = await self.generate_insights(
                metrics=performance_data,
                patterns=pattern_data.get("patterns", []),
                failures=failure_data.get("failures", []),
            )
            insights_data = json.loads(insights_result)
            insights = [
                Insight(
                    insight_id=str(uuid.uuid4()),
                    insight_type=InsightType(i.get("type", "pattern")),
                    title=i.get("title", ""),
                    description=i.get("description", ""),
                    confidence=i.get("confidence", 0.5),
                    evidence=i.get("evidence", []),
                    affected_components=i.get("affected_components", []),
                    recommendations=i.get("recommendations", []),
                    priority=ImplementationPriority(i.get("priority", "medium")),
                )
                for i in insights_data.get("insights", [])
            ]

            # Generate recommendations
            recommendations_result = await self.generate_recommendations(
                insights=[asdict(i) for i in insights],
                context={"analysis_period": analysis_period},
            )
            recommendations_data = json.loads(recommendations_result)
            recommendations = recommendations_data.get("recommendations", [])

            # Create new patterns
            patterns_result = await self.create_training_patterns(
                successful_commands=pattern_data.get("successful_commands", []),
            )
            patterns_data = json.loads(patterns_result)
            new_patterns = patterns_data.get("patterns", [])

            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(
                performance_data, pattern_data, failure_data
            )

            # Determine implementation priority
            implementation_priority = self._determine_priority(insights, recommendations)

            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                insights, recommendations, performance_data, analysis_period
            )

            # Create synthesis object
            synthesis = KnowledgeSynthesis(
                synthesis_id=synthesis_id,
                timestamp=timestamp,
                analysis_period=analysis_period,
                data_sources={
                    "total_interactions_analyzed": total_interactions,
                    "time_period": analysis_period,
                    "performance_data_available": bool(performance_data),
                    "pattern_data_available": bool(pattern_data),
                    "failure_data_available": bool(failure_data),
                    "baseline_accuracy": baseline_accuracy,
                },
                insights=insights,
                recommendations=recommendations,
                new_patterns=new_patterns,
                confidence_scores=confidence_scores,
                implementation_priority=implementation_priority,
                executive_summary=executive_summary,
            )

            # Store synthesis
            self._synthesized_knowledge[synthesis_id] = synthesis

            # Update metrics
            self.metrics["syntheses_completed"] += 1
            self.metrics["insights_generated"] += len(insights)
            self.metrics["recommendations_generated"] += len(recommendations)
            self.metrics["patterns_created"] += len(new_patterns)

            # Store in context manager if available
            if self.context_manager:
                try:
                    await self.context_manager.store_context(
                        key=f"synthesis:{synthesis_id}",
                        data={
                            "synthesis_id": synthesis_id,
                            "timestamp": timestamp,
                            "executive_summary": executive_summary,
                            "insight_count": len(insights),
                            "recommendation_count": len(recommendations),
                        },
                        layer="knowledge",
                    )
                except Exception as e:
                    logger.warning(f"Failed to store synthesis in context: {e}")

            return json.dumps({
                "status": "success",
                "synthesis_id": synthesis_id,
                "executive_summary": executive_summary,
                "insights_count": len(insights),
                "recommendations_count": len(recommendations),
                "new_patterns_count": len(new_patterns),
                "implementation_priority": implementation_priority.value,
                "confidence_scores": confidence_scores,
            })

        except Exception as e:
            logger.error(f"Knowledge synthesis failed: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
            })

    async def generate_insights(
        self,
        metrics: Dict[str, Any],
        patterns: Optional[List[Dict[str, Any]]] = None,
        failures: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate insights from analysis data"""
        import uuid
        patterns = patterns or []
        failures = failures or []
        insights = []

        # Insight 1: Success rate analysis
        success_rate = metrics.get("success_rate_percentage", 0)
        if success_rate < 90:
            insights.append({
                "type": "improvement",
                "title": "Success Rate Below Target",
                "description": f"Current success rate ({success_rate:.1f}%) is below the 90% target",
                "confidence": 0.95,
                "evidence": [f"Success rate: {success_rate:.1f}%"],
                "affected_components": ["voice_command_intelligence", "error_coordinator"],
                "recommendations": ["Analyze failure patterns", "Improve intent recognition"],
                "priority": "high" if success_rate < 80 else "medium",
            })
        else:
            insights.append({
                "type": "pattern",
                "title": "Healthy Success Rate",
                "description": f"Success rate ({success_rate:.1f}%) meets target",
                "confidence": 0.95,
                "evidence": [f"Success rate: {success_rate:.1f}%"],
                "affected_components": [],
                "recommendations": ["Maintain current performance"],
                "priority": "low",
            })

        # Insight 2: Latency analysis
        avg_latency = metrics.get("average_command_duration_ms", 0)
        p95_latency = metrics.get("p95_response_time", avg_latency * 1.5)
        if p95_latency > 500:
            insights.append({
                "type": "improvement",
                "title": "Latency Above Target",
                "description": f"P95 latency ({p95_latency:.0f}ms) exceeds 500ms target",
                "confidence": 0.9,
                "evidence": [f"Avg: {avg_latency:.0f}ms", f"P95: {p95_latency:.0f}ms"],
                "affected_components": ["voice_command_intelligence", "performance_monitor"],
                "recommendations": ["Optimize NLP processing", "Add caching"],
                "priority": "high" if p95_latency > 1000 else "medium",
            })

        # Insight 3: Pattern insights
        for pattern in patterns[:5]:  # Top 5 patterns
            if pattern.get("confidence", 0) > 0.7:
                insights.append({
                    "type": "pattern",
                    "title": f"Pattern: {pattern.get('pattern_name', 'Unknown')}",
                    "description": pattern.get("description", "Pattern detected"),
                    "confidence": pattern.get("confidence", 0.5),
                    "evidence": pattern.get("examples", []),
                    "affected_components": ["voice_pattern_analyzer", "knowledge_synthesizer"],
                    "recommendations": pattern.get("recommendations", []),
                    "priority": "medium",
                })

        # Insight 4: Failure patterns
        failure_types = defaultdict(int)
        for failure in failures:
            failure_types[failure.get("failure_type", "unknown")] += 1

        if failure_types:
            top_failure = max(failure_types.items(), key=lambda x: x[1])
            insights.append({
                "type": "anomaly",
                "title": f"Frequent Failure Type: {top_failure[0]}",
                "description": f"{top_failure[1]} occurrences of {top_failure[0]} failures",
                "confidence": 0.85,
                "evidence": [f"{k}: {v}" for k, v in failure_types.items()],
                "affected_components": ["error_coordinator"],
                "recommendations": [f"Investigate {top_failure[0]} failures"],
                "priority": "high" if top_failure[1] > 10 else "medium",
            })

        # Insight 5: Confidence calibration
        avg_confidence = metrics.get("confidence_score_average", 0)
        if avg_confidence < 0.7:
            insights.append({
                "type": "improvement",
                "title": "Low Average Confidence",
                "description": f"Average confidence ({avg_confidence:.2f}) is below 0.7 threshold",
                "confidence": 0.8,
                "evidence": [f"Average confidence: {avg_confidence:.2f}"],
                "affected_components": ["voice_command_intelligence"],
                "recommendations": ["Retrain intent classifier", "Add more training data"],
                "priority": "medium",
            })

        return json.dumps({
            "status": "success",
            "insights": insights,
            "total_insights": len(insights),
        })

    async def generate_recommendations(
        self,
        insights: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate actionable recommendations from insights"""
        import uuid
        context = context or {}
        recommendations = []

        for insight in insights:
            # Skip low-priority insights unless they have recommendations
            if insight.get("priority") == "low" and not insight.get("recommendations"):
                continue

            # Create recommendation for each insight recommendation
            for rec_text in insight.get("recommendations", []):
                rec_id = str(uuid.uuid4())
                recommendation = {
                    "recommendation_id": rec_id,
                    "title": rec_text[:50] + "..." if len(rec_text) > 50 else rec_text,
                    "description": rec_text,
                    "source_insight": insight.get("title", "Unknown"),
                    "priority": insight.get("priority", "medium"),
                    "affected_components": insight.get("affected_components", []),
                    "estimated_impact": self._estimate_impact(insight),
                    "implementation_effort": self._estimate_effort(rec_text),
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                }
                recommendations.append(recommendation)
                self._recommendation_history.append(recommendation)

        # Sort by priority and impact
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: (
            priority_order.get(x["priority"], 3),
            -x["estimated_impact"]
        ))

        return json.dumps({
            "status": "success",
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
        })

    def _estimate_impact(self, insight: Dict[str, Any]) -> float:
        """Estimate impact of implementing insight recommendation"""
        base_impact = insight.get("confidence", 0.5)

        # Boost for high priority
        if insight.get("priority") == "critical":
            base_impact += 0.3
        elif insight.get("priority") == "high":
            base_impact += 0.2

        # Boost for improvement type
        if insight.get("type") == "improvement":
            base_impact += 0.1

        return min(base_impact, 1.0)

    def _estimate_effort(self, recommendation: str) -> str:
        """Estimate implementation effort"""
        low_effort_keywords = ["adjust", "tune", "configure", "enable"]
        high_effort_keywords = ["retrain", "redesign", "rebuild", "implement"]

        rec_lower = recommendation.lower()

        if any(kw in rec_lower for kw in high_effort_keywords):
            return "high"
        elif any(kw in rec_lower for kw in low_effort_keywords):
            return "low"
        return "medium"

    async def create_training_patterns(
        self,
        successful_commands: List[Dict[str, Any]],
        min_confidence: float = 0.8,
    ) -> str:
        """Create new training patterns from successful interactions"""
        import uuid
        patterns = []

        # Filter high-confidence successful commands
        high_quality = [
            cmd for cmd in successful_commands
            if cmd.get("confidence", 0) >= min_confidence and cmd.get("success", False)
        ]

        # Group by intent
        by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for cmd in high_quality:
            by_intent[cmd.get("intent", "unknown")].append(cmd)

        # Create patterns
        for intent, commands in by_intent.items():
            if len(commands) >= 3:  # Need at least 3 examples
                # Extract unique phrasings
                phrasings = list(set(cmd.get("voice_text", "").lower().strip() for cmd in commands))

                # Extract common parameters
                all_params = defaultdict(list)
                for cmd in commands:
                    for k, v in cmd.get("parameters", {}).items():
                        all_params[k].append(v)

                pattern = {
                    "pattern_id": str(uuid.uuid4()),
                    "intent": intent,
                    "phrasings": phrasings[:10],
                    "common_parameters": dict(all_params),
                    "example_count": len(commands),
                    "avg_confidence": sum(c.get("confidence", 0) for c in commands) / len(commands),
                    "created_at": datetime.now().isoformat(),
                    "source": "successful_interactions",
                }
                patterns.append(pattern)

        return json.dumps({
            "status": "success",
            "patterns": patterns,
            "total_patterns": len(patterns),
            "commands_analyzed": len(successful_commands),
            "high_quality_commands": len(high_quality),
        })

    def _calculate_confidence_scores(
        self,
        performance_data: Dict[str, Any],
        pattern_data: Dict[str, Any],
        failure_data: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate confidence scores for synthesis"""
        scores = {}

        # Performance confidence based on sample size
        total = performance_data.get("total_commands_processed", 0)
        scores["performance_confidence"] = min(total / 100, 1.0)  # Full confidence at 100+ samples

        # Pattern confidence based on pattern count
        patterns = pattern_data.get("patterns", [])
        scores["pattern_confidence"] = min(len(patterns) / 10, 1.0)  # Full confidence at 10+ patterns

        # Failure analysis confidence
        failures = failure_data.get("failures", [])
        scores["failure_analysis_confidence"] = min(len(failures) / 20, 1.0)

        # Overall synthesis confidence
        scores["overall_confidence"] = (
            scores["performance_confidence"] * 0.4 +
            scores["pattern_confidence"] * 0.3 +
            scores["failure_analysis_confidence"] * 0.3
        )

        return scores

    def _determine_priority(
        self,
        insights: List[Insight],
        recommendations: List[Dict[str, Any]],
    ) -> ImplementationPriority:
        """Determine overall implementation priority"""
        # Check for critical insights
        if any(i.priority == ImplementationPriority.CRITICAL for i in insights):
            return ImplementationPriority.CRITICAL

        # Check for high priority items
        high_count = sum(1 for i in insights if i.priority == ImplementationPriority.HIGH)
        if high_count >= 2:
            return ImplementationPriority.HIGH

        # Check recommendations
        if any(r.get("priority") == "high" for r in recommendations):
            return ImplementationPriority.HIGH

        return ImplementationPriority.MEDIUM

    def _generate_executive_summary(
        self,
        insights: List[Insight],
        recommendations: List[Dict[str, Any]],
        performance_data: Dict[str, Any],
        analysis_period: str,
    ) -> str:
        """Generate executive summary of synthesis"""
        success_rate = performance_data.get("success_rate_percentage", 0)
        total = performance_data.get("total_commands_processed", 0)

        critical_count = sum(1 for i in insights if i.priority == ImplementationPriority.CRITICAL)
        high_count = sum(1 for i in insights if i.priority == ImplementationPriority.HIGH)

        summary_parts = [
            f"Analysis period: {analysis_period}.",
            f"Analyzed {total} commands with {success_rate:.1f}% success rate.",
            f"Generated {len(insights)} insights ({critical_count} critical, {high_count} high priority).",
            f"Produced {len(recommendations)} actionable recommendations.",
        ]

        if critical_count > 0:
            summary_parts.append("ATTENTION: Critical issues detected requiring immediate action.")

        return " ".join(summary_parts)

    async def get_synthesis_history(self, limit: int = 10) -> str:
        """Get history of knowledge syntheses"""
        syntheses = list(self._synthesized_knowledge.values())
        syntheses.sort(key=lambda x: x.timestamp, reverse=True)

        history = [
            {
                "synthesis_id": s.synthesis_id,
                "timestamp": s.timestamp,
                "analysis_period": s.analysis_period,
                "executive_summary": s.executive_summary,
                "insights_count": len(s.insights),
                "recommendations_count": len(s.recommendations),
                "implementation_priority": s.implementation_priority.value,
            }
            for s in syntheses[:limit]
        ]

        return json.dumps({
            "status": "success",
            "history": history,
            "total_syntheses": len(syntheses),
        })

    async def get_recommendations(
        self,
        status: str = "all",
        priority: Optional[str] = None,
    ) -> str:
        """Get pending and historical recommendations"""
        recommendations = self._recommendation_history.copy()

        # Filter by status
        if status != "all":
            recommendations = [r for r in recommendations if r.get("status") == status]

        # Filter by priority
        if priority:
            recommendations = [r for r in recommendations if r.get("priority") == priority]

        # Sort by created_at descending
        recommendations.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return json.dumps({
            "status": "success",
            "recommendations": recommendations[:50],  # Limit to 50
            "total_count": len(recommendations),
        })

    async def update_recommendation_status(
        self,
        recommendation_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> str:
        """Update status of a recommendation"""
        for rec in self._recommendation_history:
            if rec.get("recommendation_id") == recommendation_id:
                rec["status"] = status
                rec["updated_at"] = datetime.now().isoformat()
                if notes:
                    rec["notes"] = notes

                return json.dumps({
                    "status": "success",
                    "recommendation_id": recommendation_id,
                    "new_status": status,
                })

        return json.dumps({
            "status": "error",
            "error": f"Recommendation not found: {recommendation_id}",
        })


# Test/demo
if __name__ == "__main__":
    async def main():
        agent = KnowledgeSynthesizerAgent()

        # Synthesize knowledge
        result = await agent.synthesize_knowledge(
            performance_data={
                "total_commands_processed": 150,
                "successful_commands": 130,
                "success_rate_percentage": 86.7,
                "average_command_duration_ms": 350,
                "confidence_score_average": 0.78,
                "p95_response_time": 620,
            },
            pattern_data={
                "patterns": [
                    {"pattern_name": "synonyms_play_music", "confidence": 0.85, "description": "Multiple ways to say play music"},
                ],
                "successful_commands": [
                    {"voice_text": "play jazz", "intent": "play_music", "confidence": 0.92, "success": True, "parameters": {}},
                    {"voice_text": "listen to rock", "intent": "play_music", "confidence": 0.88, "success": True, "parameters": {}},
                ],
            },
            failure_data={
                "failures": [
                    {"failure_type": "interpretation", "count": 10},
                    {"failure_type": "recognition", "count": 5},
                ],
            },
            analysis_period="last_hour",
            total_interactions=150,
            baseline_accuracy=85.0,
        )

        print("Synthesis:", json.dumps(json.loads(result), indent=2))

    asyncio.run(main())
