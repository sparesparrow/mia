"""
Voice Command Intelligence Agent

Core agent for voice command processing with intent recognition, parameter extraction,
and success/failure tracking. The front door for the learning system.

Role: Voice Command Processing & Analysis
Parent System: core-orchestrator
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_framework import MCPServer, Tool, MCPMessage

logger = logging.getLogger(__name__)


class CommandStatus(str, Enum):
    """Command processing status"""
    RECEIVED = "received"
    PROCESSING = "processing"
    INTERPRETED = "interpreted"
    VALIDATED = "validated"
    EXECUTED = "executed"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass
class VoiceCommandRequest:
    """Input contract for voice command processing"""
    voice_text: str
    user_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    device_type: str = "unknown"
    acoustic_features: Optional[Dict[str, Any]] = None
    user_context: Optional[Dict[str, Any]] = None
    device_context: Optional[Dict[str, Any]] = None
    environmental_data: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None


@dataclass
class VoiceCommandAnalysis:
    """Output contract for command analysis"""
    command_id: str
    intent: str
    confidence: float
    parameters: Dict[str, Any]
    execution_plan: List[Dict[str, Any]]
    safety_check: Dict[str, Any]
    analysis_metadata: Dict[str, Any]
    status: CommandStatus = CommandStatus.COMPLETED
    error: Optional[str] = None


class VoiceCommandIntelligenceAgent(MCPServer):
    """
    Core voice command processing agent.

    Responsibilities:
    - Parse and classify voice commands
    - Extract command parameters and context
    - Validate command safety and feasibility
    - Generate formatted command execution logs
    - Track command success/failure metrics

    Success Metrics:
    - Command recognition accuracy: >95%
    - Parameter extraction accuracy: >92%
    - Response time: <500ms
    - Failure detection rate: >99%
    """

    def __init__(
        self,
        name: str = "voice-command-intelligence",
        version: str = "1.0.0",
        nlp_processor: Optional[Any] = None,
        context_manager: Optional[Any] = None,
        message_bus: Optional[Any] = None,
    ):
        super().__init__(name, version)

        self.nlp_processor = nlp_processor
        self.context_manager = context_manager
        self.message_bus = message_bus

        # Metrics tracking
        self.metrics = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "total_latency_ms": 0,
            "confidence_sum": 0.0,
        }

        # Intent patterns (fallback when NLP processor not available)
        self.intent_patterns = {
            "play_music": ["play", "music", "song", "track"],
            "stop": ["stop", "pause", "halt"],
            "volume": ["volume", "louder", "quieter", "mute"],
            "navigation": ["navigate", "directions", "route", "go to"],
            "climate": ["temperature", "ac", "heat", "cool", "fan"],
            "call": ["call", "phone", "dial"],
            "message": ["text", "message", "send"],
            "query": ["what", "who", "when", "where", "how"],
        }

        # Command handlers registry
        self._command_handlers: Dict[str, Callable] = {}

        # Register MCP tools
        self._register_tools()

        logger.info(f"VoiceCommandIntelligenceAgent initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register MCP tools for voice command processing"""

        # Tool 1: Process voice command
        self.add_tool(Tool(
            name="process_voice_command",
            description="Process a voice command end-to-end: recognition, interpretation, validation, execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "voice_text": {"type": "string", "description": "The voice command text"},
                    "user_id": {"type": "string", "description": "User identifier"},
                    "device_type": {"type": "string", "description": "Device type"},
                    "context": {"type": "object", "description": "Additional context"},
                },
                "required": ["voice_text", "user_id"],
            },
            handler=self.process_voice_command,
        ))

        # Tool 2: Extract intent
        self.add_tool(Tool(
            name="extract_intent",
            description="Extract intent from voice command text",
            inputSchema={
                "type": "object",
                "properties": {
                    "voice_text": {"type": "string", "description": "The voice command text"},
                    "context": {"type": "object", "description": "Context for interpretation"},
                },
                "required": ["voice_text"],
            },
            handler=self.extract_intent,
        ))

        # Tool 3: Validate parameters
        self.add_tool(Tool(
            name="validate_parameters",
            description="Validate extracted command parameters",
            inputSchema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "description": "Extracted intent"},
                    "parameters": {"type": "object", "description": "Parameters to validate"},
                    "context": {"type": "object", "description": "Context for validation"},
                },
                "required": ["intent", "parameters"],
            },
            handler=self.validate_parameters,
        ))

        # Tool 4: Execute command
        self.add_tool(Tool(
            name="execute_command",
            description="Execute a validated command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {"type": "string", "description": "Command ID"},
                    "intent": {"type": "string", "description": "Command intent"},
                    "parameters": {"type": "object", "description": "Command parameters"},
                    "execution_plan": {"type": "array", "description": "Execution steps"},
                },
                "required": ["command_id", "intent"],
            },
            handler=self.execute_command,
        ))

        # Tool 5: Get command metrics
        self.add_tool(Tool(
            name="get_command_metrics",
            description="Get current command processing metrics",
            inputSchema={
                "type": "object",
                "properties": {},
            },
            handler=self.get_command_metrics,
        ))

        logger.info(f"Registered {len(self.tools)} voice command intelligence tools")

    async def process_voice_command(
        self,
        voice_text: str,
        user_id: str,
        device_type: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Process a voice command end-to-end.

        Flow:
        1. on_command_received - Log receipt
        2. Extract intent and parameters
        3. Validate safety and feasibility
        4. Execute command
        5. on_execution_complete - Log result
        """
        command_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        context = context or {}

        try:
            # Hook: Command received
            await self._on_command_received(voice_text, user_id, device_type, command_id)

            # Retrieve user context if available
            user_context = {}
            if self.context_manager:
                try:
                    user_context = await self.context_manager.retrieve_context(user_id)
                except Exception as e:
                    logger.warning(f"Failed to retrieve user context: {e}")

            merged_context = {**context, **user_context}

            # Step 1: Extract intent
            intent_result = await self.extract_intent(voice_text, merged_context)
            intent_data = json.loads(intent_result)

            intent = intent_data["intent"]
            confidence = intent_data["confidence"]
            parameters = intent_data["parameters"]

            # Hook: Interpretation complete
            await self._on_interpretation_complete(
                command_id, intent, confidence, parameters
            )

            # Step 2: Validate parameters
            validation_result = await self.validate_parameters(
                intent, parameters, merged_context
            )
            validation_data = json.loads(validation_result)

            if not validation_data["valid"]:
                raise ValueError(f"Validation failed: {validation_data['issues']}")

            # Step 3: Build execution plan
            execution_plan = self._build_execution_plan(intent, parameters)

            # Step 4: Safety check
            safety_check = await self._check_safety(intent, parameters, merged_context)
            if not safety_check["safe"]:
                raise ValueError(f"Safety check failed: {safety_check['reason']}")

            # Step 5: Execute
            execution_result = await self.execute_command(
                command_id, intent, parameters, execution_plan
            )
            execution_data = json.loads(execution_result)

            success = execution_data["status"] == "success"

            # Calculate latency
            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000

            # Update metrics
            self.metrics["total_commands"] += 1
            self.metrics["total_latency_ms"] += duration_ms
            self.metrics["confidence_sum"] += confidence
            if success:
                self.metrics["successful_commands"] += 1
            else:
                self.metrics["failed_commands"] += 1

            # Hook: Execution complete
            await self._on_execution_complete(
                command_id, success, execution_data.get("result"), duration_ms
            )

            # Publish event to message bus
            await self._publish_command_event(
                command_id, voice_text, user_id, intent, confidence,
                parameters, success, duration_ms
            )

            # Build response
            analysis = VoiceCommandAnalysis(
                command_id=command_id,
                intent=intent,
                confidence=confidence,
                parameters=parameters,
                execution_plan=execution_plan,
                safety_check=safety_check,
                analysis_metadata={
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "device_type": device_type,
                    "timestamp": datetime.now().isoformat(),
                },
                status=CommandStatus.COMPLETED if success else CommandStatus.FAILED,
            )

            return json.dumps(asdict(analysis))

        except Exception as e:
            logger.error(f"Command processing failed: {e}")

            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000

            self.metrics["total_commands"] += 1
            self.metrics["failed_commands"] += 1

            # Hook: Execution complete (failure)
            await self._on_execution_complete(command_id, False, None, duration_ms)

            # Publish failure event
            await self._publish_failure_event(
                command_id, voice_text, user_id, str(e)
            )

            analysis = VoiceCommandAnalysis(
                command_id=command_id,
                intent="unknown",
                confidence=0.0,
                parameters={},
                execution_plan=[],
                safety_check={"safe": False, "reason": str(e)},
                analysis_metadata={
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                status=CommandStatus.FAILED,
                error=str(e),
            )

            return json.dumps(asdict(analysis))

    async def extract_intent(
        self,
        voice_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Extract intent from voice command text"""
        context = context or {}

        # Use NLP processor if available
        if self.nlp_processor:
            try:
                result = await self.nlp_processor.process(voice_text, context)
                return json.dumps({
                    "intent": result.get("intent", "unknown"),
                    "confidence": result.get("confidence", 0.5),
                    "parameters": result.get("parameters", {}),
                    "alternatives": result.get("alternatives", []),
                })
            except Exception as e:
                logger.warning(f"NLP processor failed, using fallback: {e}")

        # Fallback: Pattern-based intent extraction
        voice_lower = voice_text.lower()
        best_intent = "unknown"
        best_score = 0.0

        for intent, keywords in self.intent_patterns.items():
            matches = sum(1 for kw in keywords if kw in voice_lower)
            score = matches / len(keywords) if keywords else 0
            if score > best_score:
                best_score = score
                best_intent = intent

        # Extract basic parameters
        parameters = self._extract_basic_parameters(voice_text, best_intent)

        confidence = min(best_score + 0.3, 0.95) if best_score > 0 else 0.3

        return json.dumps({
            "intent": best_intent,
            "confidence": confidence,
            "parameters": parameters,
            "alternatives": [],
        })

    def _extract_basic_parameters(
        self,
        voice_text: str,
        intent: str,
    ) -> Dict[str, Any]:
        """Extract basic parameters from voice text"""
        params = {}
        voice_lower = voice_text.lower()

        # Extract common parameter patterns
        if intent == "play_music":
            # Try to extract song/artist name
            if "play " in voice_lower:
                params["target"] = voice_text.split("play ", 1)[-1].strip()
        elif intent == "volume":
            if "percent" in voice_lower or "%" in voice_text:
                import re
                match = re.search(r'(\d+)', voice_text)
                if match:
                    params["level"] = int(match.group(1))
            elif "up" in voice_lower:
                params["action"] = "increase"
            elif "down" in voice_lower:
                params["action"] = "decrease"
        elif intent == "navigation":
            if "to " in voice_lower:
                params["destination"] = voice_text.split("to ", 1)[-1].strip()
        elif intent == "climate":
            import re
            match = re.search(r'(\d+)', voice_text)
            if match:
                params["temperature"] = int(match.group(1))

        return params

    async def validate_parameters(
        self,
        intent: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Validate extracted parameters"""
        issues = []
        validated_params = parameters.copy()

        # Intent-specific validation
        if intent == "volume" and "level" in parameters:
            level = parameters["level"]
            if not 0 <= level <= 100:
                issues.append(f"Volume level {level} out of range (0-100)")
                validated_params["level"] = max(0, min(100, level))

        if intent == "climate" and "temperature" in parameters:
            temp = parameters["temperature"]
            if not 16 <= temp <= 30:
                issues.append(f"Temperature {temp} out of range (16-30)")
                validated_params["temperature"] = max(16, min(30, temp))

        if intent == "navigation" and "destination" not in parameters:
            issues.append("Navigation requires destination parameter")

        return json.dumps({
            "valid": len(issues) == 0,
            "issues": issues,
            "validated_parameters": validated_params,
        })

    async def _check_safety(
        self,
        intent: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check command safety and feasibility"""
        context = context or {}

        # Check for dangerous commands while driving
        is_driving = context.get("vehicle_state", {}).get("is_moving", False)

        dangerous_while_driving = ["message", "video", "browse"]
        if is_driving and intent in dangerous_while_driving:
            return {
                "safe": False,
                "reason": f"Cannot perform '{intent}' while vehicle is moving",
                "requires_confirmation": True,
            }

        return {
            "safe": True,
            "reason": None,
            "requires_confirmation": False,
        }

    def _build_execution_plan(
        self,
        intent: str,
        parameters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build execution plan for command"""
        plan = []

        # Common pre-execution steps
        plan.append({
            "step": 1,
            "action": "validate_context",
            "description": "Verify execution context is valid",
        })

        # Intent-specific steps
        if intent == "play_music":
            plan.extend([
                {"step": 2, "action": "connect_audio", "description": "Connect to audio system"},
                {"step": 3, "action": "search_music", "description": f"Search for: {parameters.get('target', 'music')}"},
                {"step": 4, "action": "start_playback", "description": "Start playback"},
            ])
        elif intent == "navigation":
            plan.extend([
                {"step": 2, "action": "geocode_destination", "description": f"Geocode: {parameters.get('destination', 'destination')}"},
                {"step": 3, "action": "calculate_route", "description": "Calculate optimal route"},
                {"step": 4, "action": "start_navigation", "description": "Start navigation"},
            ])
        elif intent == "climate":
            plan.extend([
                {"step": 2, "action": "set_temperature", "description": f"Set to {parameters.get('temperature', 22)}°C"},
                {"step": 3, "action": "confirm_setting", "description": "Confirm temperature set"},
            ])
        else:
            plan.append({
                "step": 2,
                "action": f"execute_{intent}",
                "description": f"Execute {intent} command",
            })

        return plan

    async def execute_command(
        self,
        command_id: str,
        intent: str,
        parameters: Optional[Dict[str, Any]] = None,
        execution_plan: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Execute a validated command"""
        parameters = parameters or {}
        execution_plan = execution_plan or []

        # Check if we have a handler for this intent
        if intent in self._command_handlers:
            try:
                result = await self._command_handlers[intent](parameters)
                return json.dumps({
                    "status": "success",
                    "command_id": command_id,
                    "result": result,
                })
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "command_id": command_id,
                    "error": str(e),
                })

        # Default: Simulate execution
        logger.info(f"Executing command {command_id}: {intent} with {parameters}")

        # Simulate execution steps
        for step in execution_plan:
            await asyncio.sleep(0.01)  # Simulate step execution
            logger.debug(f"  Step {step.get('step')}: {step.get('description')}")

        return json.dumps({
            "status": "success",
            "command_id": command_id,
            "result": f"Command '{intent}' executed successfully",
            "steps_completed": len(execution_plan),
        })

    async def get_command_metrics(self) -> str:
        """Get current command processing metrics"""
        total = self.metrics["total_commands"]

        metrics = {
            "total_commands_processed": total,
            "successful_commands": self.metrics["successful_commands"],
            "failed_commands": self.metrics["failed_commands"],
            "success_rate_percentage": (
                (self.metrics["successful_commands"] / total * 100)
                if total > 0 else 0.0
            ),
            "average_command_duration_ms": (
                self.metrics["total_latency_ms"] / total
                if total > 0 else 0.0
            ),
            "confidence_score_average": (
                self.metrics["confidence_sum"] / total
                if total > 0 else 0.0
            ),
        }

        return json.dumps(metrics)

    def register_command_handler(
        self,
        intent: str,
        handler: Callable,
    ) -> None:
        """Register a handler for a specific intent"""
        self._command_handlers[intent] = handler
        logger.info(f"Registered handler for intent: {intent}")

    # ========================================================================
    # Event Hooks
    # ========================================================================

    async def _on_command_received(
        self,
        voice_text: str,
        user_id: str,
        device_type: str,
        command_id: str,
    ) -> None:
        """Hook: Called when command is received"""
        logger.info(
            f"Command received: {command_id} | "
            f"user={user_id} | device={device_type} | text='{voice_text[:50]}...'"
        )

    async def _on_interpretation_complete(
        self,
        command_id: str,
        intent: str,
        confidence: float,
        parameters: Dict[str, Any],
    ) -> None:
        """Hook: Called when interpretation is complete"""
        logger.info(
            f"Interpretation complete: {command_id} | "
            f"intent={intent} | confidence={confidence:.2f} | params={parameters}"
        )

    async def _on_execution_complete(
        self,
        command_id: str,
        success: bool,
        result: Optional[Any],
        duration_ms: float,
    ) -> None:
        """Hook: Called when execution is complete"""
        status = "SUCCESS" if success else "FAILED"
        logger.info(
            f"Execution {status}: {command_id} | duration={duration_ms:.1f}ms"
        )

    # ========================================================================
    # Message Bus Publishing
    # ========================================================================

    async def _publish_command_event(
        self,
        command_id: str,
        voice_text: str,
        user_id: str,
        intent: str,
        confidence: float,
        parameters: Dict[str, Any],
        success: bool,
        duration_ms: float,
    ) -> None:
        """Publish command event to message bus"""
        if not self.message_bus:
            return

        event = {
            "event_type": "command_analyzed",
            "command_id": command_id,
            "voice_text": voice_text,
            "user_id": user_id,
            "intent": intent,
            "confidence": confidence,
            "parameters": parameters,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await self.message_bus.publish("stream:command_analyzed", event)
            logger.debug(f"Published command event: {command_id}")
        except Exception as e:
            logger.error(f"Failed to publish command event: {e}")

    async def _publish_failure_event(
        self,
        command_id: str,
        voice_text: str,
        user_id: str,
        error: str,
    ) -> None:
        """Publish failure event to message bus"""
        if not self.message_bus:
            return

        event = {
            "event_type": "command_failed",
            "command_id": command_id,
            "voice_text": voice_text,
            "user_id": user_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await self.message_bus.publish("stream:command_failed", event)
            logger.debug(f"Published failure event: {command_id}")
        except Exception as e:
            logger.error(f"Failed to publish failure event: {e}")


# Test/demo
if __name__ == "__main__":
    async def main():
        agent = VoiceCommandIntelligenceAgent()

        # Test processing
        result = await agent.process_voice_command(
            voice_text="play some jazz music",
            user_id="user123",
            device_type="car",
        )
        print("Result:", json.dumps(json.loads(result), indent=2))

        # Get metrics
        metrics = await agent.get_command_metrics()
        print("Metrics:", json.dumps(json.loads(metrics), indent=2))

    asyncio.run(main())
