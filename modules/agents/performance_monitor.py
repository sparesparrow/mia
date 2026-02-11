"""
Performance Monitor Agent

Continuously tracks system performance, command success rates, identifies bottlenecks,
and measures learning effectiveness.

Role: Metrics Collection & Success Tracking
Parent System: core-orchestrator
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_framework import MCPServer, Tool

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """A single metric measurement"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """An alert triggered by threshold breach"""
    metric: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: str


class TimeSeriesBuffer:
    """Rolling time-series buffer for metrics"""

    def __init__(self, max_age_seconds: int = 3600, bucket_seconds: int = 5):
        self.max_age = max_age_seconds
        self.bucket_seconds = bucket_seconds
        self._data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_age_seconds // bucket_seconds))

    def add(self, metric: str, value: float, timestamp: Optional[float] = None) -> None:
        timestamp = timestamp or time.time()
        bucket = int(timestamp // self.bucket_seconds) * self.bucket_seconds
        self._data[metric].append((bucket, value))

    def get_window(
        self,
        metric: str,
        window_seconds: int = 300,
    ) -> List[Tuple[float, float]]:
        """Get metrics in time window"""
        cutoff = time.time() - window_seconds
        return [(t, v) for t, v in self._data.get(metric, []) if t >= cutoff]

    def aggregate(
        self,
        metric: str,
        window_seconds: int = 300,
        agg_func: str = "avg",
    ) -> Optional[float]:
        """Aggregate metrics over window"""
        values = [v for _, v in self.get_window(metric, window_seconds)]
        if not values:
            return None

        if agg_func == "avg":
            return statistics.mean(values)
        elif agg_func == "sum":
            return sum(values)
        elif agg_func == "min":
            return min(values)
        elif agg_func == "max":
            return max(values)
        elif agg_func == "count":
            return len(values)
        elif agg_func == "p50":
            return statistics.median(values)
        elif agg_func == "p95":
            return statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values)
        elif agg_func == "p99":
            return statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
        return None


class PerformanceMonitorAgent(MCPServer):
    """
    Metrics collection and success tracking agent.

    Responsibilities:
    - Collect real-time performance metrics
    - Track command success/failure rates
    - Measure response times and latencies
    - Identify performance bottlenecks
    - Aggregate metrics for trend analysis
    - Generate performance reports
    - Trigger alerts on anomalies
    - Measure learning loop effectiveness

    Metrics Categories:
    - Command: total, successful, failed, success_rate, duration, confidence
    - Response: avg, p50, p95, p99 latency, timeout_rate, error_rate
    - Learning: improvement_rate, adoption_rate, synthesis_frequency, cycle_time
    - System: agent_health, resource_utilization, queue_depth, cache_hit_ratio

    Success Metrics:
    - Metric collection accuracy: 99.95%
    - Anomaly detection rate: >90%
    - Alert false positive rate: <5%
    - Report generation time: <5 seconds
    """

    def __init__(
        self,
        name: str = "performance-monitor",
        version: str = "1.0.0",
        message_bus: Optional[Any] = None,
        alert_callback: Optional[Any] = None,
    ):
        super().__init__(name, version)

        self.message_bus = message_bus
        self.alert_callback = alert_callback

        # Time-series storage
        self._metrics = TimeSeriesBuffer(max_age_seconds=3600, bucket_seconds=5)

        # Counters (cumulative)
        self._counters: Dict[str, int] = defaultdict(int)

        # Gauges (current values)
        self._gauges: Dict[str, float] = {}

        # Histograms (distributions)
        self._histograms: Dict[str, List[float]] = defaultdict(list)

        # Active alerts
        self._alerts: List[Alert] = []

        # Alert thresholds
        self._thresholds = {
            "success_rate": {"threshold": 90.0, "comparison": "lt", "severity": AlertSeverity.CRITICAL},
            "response_time_p95": {"threshold": 2000.0, "comparison": "gt", "severity": AlertSeverity.WARNING},
            "error_rate": {"threshold": 10.0, "comparison": "gt", "severity": AlertSeverity.WARNING},
            "agent_uptime": {"threshold": 99.0, "comparison": "lt", "severity": AlertSeverity.CRITICAL},
            "learning_cycle_failure_rate": {"threshold": 5.0, "comparison": "gt", "severity": AlertSeverity.WARNING},
        }

        # Register tools
        self._register_tools()

        logger.info(f"PerformanceMonitorAgent initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register MCP tools"""

        # Tool 1: Record metric
        self.add_tool(Tool(
            name="record_metric",
            description="Record a performance metric",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "description": "Metric name"},
                    "value": {"type": "number", "description": "Metric value"},
                    "metric_type": {"type": "string", "enum": ["counter", "gauge", "histogram"]},
                    "tags": {"type": "object", "description": "Metric tags"},
                },
                "required": ["metric_name", "value"],
            },
            handler=self.record_metric,
        ))

        # Tool 2: Record command event
        self.add_tool(Tool(
            name="record_command_event",
            description="Record a command execution event with all metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {"type": "string"},
                    "success": {"type": "boolean"},
                    "duration_ms": {"type": "number"},
                    "confidence": {"type": "number"},
                    "intent": {"type": "string"},
                    "user_id": {"type": "string"},
                },
                "required": ["command_id", "success", "duration_ms"],
            },
            handler=self.record_command_event,
        ))

        # Tool 3: Get metrics
        self.add_tool(Tool(
            name="get_metrics",
            description="Get metrics for a time window",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_names": {"type": "array", "items": {"type": "string"}},
                    "window_seconds": {"type": "integer", "default": 300},
                    "aggregation": {"type": "string", "enum": ["avg", "sum", "min", "max", "p50", "p95", "p99"]},
                },
            },
            handler=self.get_metrics,
        ))

        # Tool 4: Get dashboard summary
        self.add_tool(Tool(
            name="get_dashboard_summary",
            description="Get summary of all key metrics for dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_seconds": {"type": "integer", "default": 300},
                },
            },
            handler=self.get_dashboard_summary,
        ))

        # Tool 5: Analyze trends
        self.add_tool(Tool(
            name="analyze_trends",
            description="Analyze metric trends over time",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                    "window_seconds": {"type": "integer", "default": 3600},
                    "bucket_seconds": {"type": "integer", "default": 60},
                },
                "required": ["metric_name"],
            },
            handler=self.analyze_trends,
        ))

        # Tool 6: Get active alerts
        self.add_tool(Tool(
            name="get_active_alerts",
            description="Get all active alerts",
            inputSchema={"type": "object", "properties": {}},
            handler=self.get_active_alerts,
        ))

        # Tool 7: Validate improvements
        self.add_tool(Tool(
            name="validate_improvements",
            description="Validate if recent learning cycle improved metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "before_window_seconds": {"type": "integer", "default": 1800},
                    "after_window_seconds": {"type": "integer", "default": 300},
                },
            },
            handler=self.validate_improvements,
        ))

        logger.info(f"Registered {len(self.tools)} performance monitor tools")

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: str = "gauge",
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Record a performance metric"""
        timestamp = time.time()

        if metric_type == "counter":
            self._counters[metric_name] += int(value)
            self._metrics.add(metric_name, self._counters[metric_name], timestamp)
        elif metric_type == "gauge":
            self._gauges[metric_name] = value
            self._metrics.add(metric_name, value, timestamp)
        elif metric_type == "histogram":
            self._histograms[metric_name].append(value)
            # Keep last 10000 values
            if len(self._histograms[metric_name]) > 10000:
                self._histograms[metric_name] = self._histograms[metric_name][-10000:]
            self._metrics.add(metric_name, value, timestamp)

        # Check thresholds
        await self._check_thresholds(metric_name, value)

        return json.dumps({
            "status": "success",
            "metric": metric_name,
            "value": value,
            "type": metric_type,
            "timestamp": timestamp,
        })

    async def record_command_event(
        self,
        command_id: str,
        success: bool,
        duration_ms: float,
        confidence: float = 0.0,
        intent: str = "unknown",
        user_id: str = "unknown",
    ) -> str:
        """Record a command execution event"""
        timestamp = time.time()

        # Update counters
        self._counters["total_commands"] += 1
        if success:
            self._counters["successful_commands"] += 1
        else:
            self._counters["failed_commands"] += 1

        # Record time-series metrics
        self._metrics.add("command_duration_ms", duration_ms, timestamp)
        self._metrics.add("command_confidence", confidence, timestamp)
        self._metrics.add("command_success", 1.0 if success else 0.0, timestamp)

        # Per-intent metrics
        intent_metric = f"intent_{intent}_count"
        self._counters[intent_metric] += 1

        # Calculate current rates
        total = self._counters["total_commands"]
        success_rate = (self._counters["successful_commands"] / total * 100) if total > 0 else 0
        self._gauges["success_rate"] = success_rate

        # Check for alerts
        await self._check_thresholds("success_rate", success_rate)

        # Publish to message bus
        if self.message_bus:
            try:
                await self.message_bus.publish("stream:metrics", {
                    "event_type": "command_recorded",
                    "command_id": command_id,
                    "success": success,
                    "duration_ms": duration_ms,
                    "confidence": confidence,
                    "intent": intent,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.warning(f"Failed to publish metrics event: {e}")

        return json.dumps({
            "status": "success",
            "command_id": command_id,
            "metrics_recorded": {
                "total_commands": total,
                "success_rate": success_rate,
                "avg_duration_ms": self._metrics.aggregate("command_duration_ms", 300, "avg"),
            },
        })

    async def get_metrics(
        self,
        metric_names: Optional[List[str]] = None,
        window_seconds: int = 300,
        aggregation: str = "avg",
    ) -> str:
        """Get metrics for a time window"""
        results = {}

        if metric_names:
            for name in metric_names:
                value = self._metrics.aggregate(name, window_seconds, aggregation)
                results[name] = value
        else:
            # Get all tracked metrics
            for name in self._gauges:
                results[name] = self._gauges[name]
            for name in self._counters:
                results[name] = self._counters[name]

        return json.dumps({
            "status": "success",
            "window_seconds": window_seconds,
            "aggregation": aggregation,
            "metrics": results,
        })

    async def get_dashboard_summary(
        self,
        window_seconds: int = 300,
    ) -> str:
        """Get summary of all key metrics"""
        total = self._counters["total_commands"]
        successful = self._counters["successful_commands"]
        failed = self._counters["failed_commands"]

        # Command metrics
        command_metrics = {
            "total_commands_processed": total,
            "successful_commands": successful,
            "failed_commands": failed,
            "success_rate_percentage": (successful / total * 100) if total > 0 else 0.0,
            "average_command_duration_ms": self._metrics.aggregate("command_duration_ms", window_seconds, "avg") or 0.0,
            "confidence_score_average": self._metrics.aggregate("command_confidence", window_seconds, "avg") or 0.0,
        }

        # Response metrics
        response_metrics = {
            "average_response_time": self._metrics.aggregate("command_duration_ms", window_seconds, "avg") or 0.0,
            "p50_response_time": self._metrics.aggregate("command_duration_ms", window_seconds, "p50") or 0.0,
            "p95_response_time": self._metrics.aggregate("command_duration_ms", window_seconds, "p95") or 0.0,
            "p99_response_time": self._metrics.aggregate("command_duration_ms", window_seconds, "p99") or 0.0,
            "timeout_rate": self._gauges.get("timeout_rate", 0.0),
            "error_rate": (failed / total * 100) if total > 0 else 0.0,
        }

        # Learning metrics
        learning_metrics = {
            "pattern_improvement_rate": self._gauges.get("pattern_improvement_rate", 0.0),
            "recommendation_adoption_rate": self._gauges.get("recommendation_adoption_rate", 0.0),
            "knowledge_synthesis_frequency": self._gauges.get("synthesis_frequency", 0.0),
            "model_update_effectiveness": self._gauges.get("model_effectiveness", 0.0),
            "learning_loop_cycle_time": self._gauges.get("cycle_time", 0.0),
        }

        # System metrics
        system_metrics = {
            "agent_health_status": self._gauges.get("agent_health", 100.0),
            "resource_utilization": self._gauges.get("resource_utilization", 0.0),
            "queue_depth": self._gauges.get("queue_depth", 0.0),
            "cache_hit_ratio": self._gauges.get("cache_hit_ratio", 0.0),
        }

        return json.dumps({
            "status": "success",
            "window_seconds": window_seconds,
            "generated_at": datetime.now().isoformat(),
            "command_metrics": command_metrics,
            "response_metrics": response_metrics,
            "learning_metrics": learning_metrics,
            "system_metrics": system_metrics,
            "active_alerts": len(self._alerts),
        })

    async def analyze_trends(
        self,
        metric_name: str,
        window_seconds: int = 3600,
        bucket_seconds: int = 60,
    ) -> str:
        """Analyze metric trends over time"""
        data_points = self._metrics.get_window(metric_name, window_seconds)

        if not data_points:
            return json.dumps({
                "status": "no_data",
                "metric": metric_name,
            })

        # Group by bucket
        buckets: Dict[int, List[float]] = defaultdict(list)
        for timestamp, value in data_points:
            bucket = int(timestamp // bucket_seconds) * bucket_seconds
            buckets[bucket].append(value)

        # Calculate per-bucket averages
        trend_data = []
        for bucket_time in sorted(buckets.keys()):
            values = buckets[bucket_time]
            trend_data.append({
                "timestamp": datetime.fromtimestamp(bucket_time).isoformat(),
                "avg": statistics.mean(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            })

        # Calculate trend direction
        if len(trend_data) >= 2:
            first_half = [d["avg"] for d in trend_data[:len(trend_data)//2]]
            second_half = [d["avg"] for d in trend_data[len(trend_data)//2:]]
            first_avg = statistics.mean(first_half) if first_half else 0
            second_avg = statistics.mean(second_half) if second_half else 0
            trend_direction = "increasing" if second_avg > first_avg * 1.05 else \
                             "decreasing" if second_avg < first_avg * 0.95 else "stable"
        else:
            trend_direction = "insufficient_data"

        return json.dumps({
            "status": "success",
            "metric": metric_name,
            "window_seconds": window_seconds,
            "bucket_seconds": bucket_seconds,
            "trend_direction": trend_direction,
            "data_points": len(data_points),
            "buckets": len(trend_data),
            "trend_data": trend_data,
        })

    async def _check_thresholds(self, metric_name: str, value: float) -> None:
        """Check if metric breaches threshold and generate alert"""
        if metric_name not in self._thresholds:
            return

        config = self._thresholds[metric_name]
        threshold = config["threshold"]
        comparison = config["comparison"]
        severity = config["severity"]

        breach = False
        if comparison == "lt" and value < threshold:
            breach = True
        elif comparison == "gt" and value > threshold:
            breach = True
        elif comparison == "eq" and value == threshold:
            breach = True

        if breach:
            alert = Alert(
                metric=metric_name,
                severity=severity,
                message=f"{metric_name} breached threshold: {value} {comparison} {threshold}",
                value=value,
                threshold=threshold,
                timestamp=datetime.now().isoformat(),
            )
            self._alerts.append(alert)

            # Keep last 100 alerts
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]

            logger.warning(f"Alert triggered: {alert.message}")

            # Call alert callback if configured
            if self.alert_callback:
                try:
                    await self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    async def get_active_alerts(self) -> str:
        """Get all active alerts"""
        # Filter alerts from last hour
        cutoff = datetime.now() - timedelta(hours=1)

        active = [
            {
                "metric": a.metric,
                "severity": a.severity.value,
                "message": a.message,
                "value": a.value,
                "threshold": a.threshold,
                "timestamp": a.timestamp,
            }
            for a in self._alerts
            if datetime.fromisoformat(a.timestamp) > cutoff
        ]

        return json.dumps({
            "status": "success",
            "active_alerts": active,
            "total_alerts": len(active),
            "critical_count": sum(1 for a in active if a["severity"] == "critical"),
            "warning_count": sum(1 for a in active if a["severity"] == "warning"),
        })

    async def validate_improvements(
        self,
        before_window_seconds: int = 1800,
        after_window_seconds: int = 300,
    ) -> str:
        """Validate if recent learning cycle improved metrics"""
        now = time.time()

        # Get metrics from before period (30 min - 5 min ago)
        before_start = now - before_window_seconds
        before_end = now - after_window_seconds

        before_data = [v for t, v in self._metrics.get_window("command_success", before_window_seconds)
                       if t < before_end]
        after_data = [v for t, v in self._metrics.get_window("command_success", after_window_seconds)]

        if not before_data or not after_data:
            return json.dumps({
                "status": "insufficient_data",
                "message": "Not enough data to compare periods",
            })

        before_rate = statistics.mean(before_data) * 100
        after_rate = statistics.mean(after_data) * 100
        improvement = after_rate - before_rate

        # Duration comparison
        before_duration = self._metrics.aggregate("command_duration_ms", before_window_seconds, "avg") or 0
        after_duration = self._metrics.aggregate("command_duration_ms", after_window_seconds, "avg") or 0
        duration_improvement = before_duration - after_duration

        return json.dumps({
            "status": "success",
            "validation_result": {
                "success_rate_before": before_rate,
                "success_rate_after": after_rate,
                "success_rate_improvement": improvement,
                "duration_before_ms": before_duration,
                "duration_after_ms": after_duration,
                "duration_improvement_ms": duration_improvement,
                "improvement_detected": improvement > 0 or duration_improvement > 0,
            },
            "before_window_seconds": before_window_seconds,
            "after_window_seconds": after_window_seconds,
        })


# Test/demo
if __name__ == "__main__":
    async def main():
        agent = PerformanceMonitorAgent()

        # Record some command events
        for i in range(10):
            success = i % 3 != 0  # 70% success rate
            await agent.record_command_event(
                command_id=f"cmd-{i}",
                success=success,
                duration_ms=100 + i * 10,
                confidence=0.8 + (i * 0.01),
                intent="play_music",
            )

        # Get dashboard
        dashboard = await agent.get_dashboard_summary()
        print("Dashboard:", json.dumps(json.loads(dashboard), indent=2))

        # Get alerts
        alerts = await agent.get_active_alerts()
        print("Alerts:", alerts)

    asyncio.run(main())
