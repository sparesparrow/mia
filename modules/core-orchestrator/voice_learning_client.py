"""
Voice Learning Client for Core Orchestrator

Provides interface for core orchestrator to call voice learning tools
via MCP connection to VoiceLearningServer.

Usage:
    client = VoiceLearningClient(orchestrator_url="ws://voice-learning:8001")
    await client.connect()

    # Analyze a single command
    learning = await client.analyze_command_learning(
        user_id="user123",
        raw_input="turn on the lights",
        intent="control.lights.on",
        success=True,
        confidence=0.95
    )

    # Run full learning cycle
    results = await client.run_learning_cycle(
        interactions=command_list,
        user_id="user123"
    )
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class VoiceLearningClient:
    """Client for calling voice learning MCP server"""

    def __init__(
        self,
        server_url: str = "ws://voice-learning:8001",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize voice learning client

        Args:
            server_url: WebSocket URL of VoiceLearningServer
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.server_url = server_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.connected = False
        self.websocket = None
        self.request_id_counter = 0
        self._pending_responses: Dict[int, asyncio.Future] = {}

        logger.info(f"Voice Learning Client initialized for {server_url}")

    async def connect(self) -> None:
        """Connect to VoiceLearningServer"""
        import websockets

        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info(f"Connected to voice learning server: {self.server_url}")

            # Start receive loop
            asyncio.create_task(self._receive_loop())

        except Exception as e:
            logger.error(f"Failed to connect to voice learning server: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from voice learning server")

    async def _receive_loop(self) -> None:
        """Background loop to receive and route responses"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    request_id = data.get("id")

                    # Route response to waiting request
                    if request_id in self._pending_responses:
                        future = self._pending_responses.pop(request_id)
                        future.set_result(data)
                    else:
                        logger.warning(f"Unexpected response with id {request_id}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response: {e}")
                except Exception as e:
                    logger.error(f"Error in receive loop: {e}")

        except asyncio.CancelledError:
            logger.info("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop failed: {e}")
            self.connected = False

    async def _call_tool(
        self,
        tool_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Call a tool on the voice learning server

        Args:
            tool_name: Name of tool to call
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        if not self.connected:
            raise RuntimeError("Not connected to voice learning server")

        # Prepare MCP request
        request_id = self.request_id_counter
        self.request_id_counter += 1

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": kwargs,
            },
        }

        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[request_id] = response_future

        try:
            # Send request
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent tool request: {tool_name}")

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=self.timeout)

            # Check for errors
            if "error" in response:
                raise RuntimeError(
                    f"Tool error: {response['error'].get('message', 'Unknown error')}"
                )

            # Extract result
            result = response.get("result", {})
            content = result.get("content", [])

            # Parse content
            if content and isinstance(content, list):
                text_content = content[0].get("text", "{}")
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return {"text": text_content}

            return result

        except asyncio.TimeoutError:
            logger.error(f"Tool request timed out: {tool_name}")
            raise
        except Exception as e:
            logger.error(f"Tool request failed: {tool_name} - {e}")
            raise

    # ========================================================================
    # Tool Methods
    # ========================================================================

    async def analyze_command_learning(
        self,
        user_id: str,
        raw_input: str,
        intent: str,
        success: bool,
        confidence: float,
        timestamp: Optional[str] = None,
        device_type: str = "unknown",
        location: str = "unknown",
        time_of_day: str = "unknown",
        parameters: Optional[Dict[str, Any]] = None,
        satisfaction_score: Optional[int] = None,
        actual_action: str = "",
        previous_intent: Optional[str] = None,
        recent_commands: Optional[List[str]] = None,
        device_state: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze learning from a voice command interaction

        Args:
            user_id: User identifier
            raw_input: What user said
            intent: Interpreted intent
            success: Whether command succeeded
            confidence: Confidence score (0-1)
            timestamp: When command was issued
            device_type: Type of device
            location: User's location
            time_of_day: Time of day
            parameters: Extracted parameters
            satisfaction_score: User satisfaction (1-5, optional)
            actual_action: Action taken
            previous_intent: Previous command intent
            recent_commands: Recent command history
            device_state: Current device state
            user_preferences: User preferences

        Returns:
            MiaVoiceCommandLearningOutput as dict
        """
        return await self._call_tool(
            "mia_analyze_command_learning",
            user_id=user_id,
            timestamp=timestamp or datetime.now().isoformat(),
            device_type=device_type,
            location=location,
            time_of_day=time_of_day,
            raw_input=raw_input,
            intent=intent,
            confidence=confidence,
            parameters=parameters or {},
            success=success,
            satisfaction_score=satisfaction_score,
            actual_action=actual_action,
            previous_intent=previous_intent,
            recent_commands=recent_commands or [],
            device_state=device_state or {},
            user_preferences=user_preferences or {},
        )

    async def analyze_failure(
        self,
        user_id: str,
        raw_input: str,
        interpreted_intent: str,
        actual_intent: str,
        user_clarification: str,
        timestamp: Optional[str] = None,
        device_type: str = "unknown",
        background_noise: Optional[str] = None,
        speech_characteristics: Optional[str] = None,
        extracted_parameters: Optional[Dict[str, Any]] = None,
        confidence_score: float = 0.5,
        executed_action: str = "",
        correct_parameters: Optional[Dict[str, Any]] = None,
        frustration_level: int = 3,
        recent_commands: Optional[List[str]] = None,
        device_state: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        time_of_day: str = "unknown",
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a voice command failure

        Args:
            user_id: User identifier
            raw_input: What user said
            interpreted_intent: What system thought
            actual_intent: What user wanted
            user_clarification: User's clarification
            timestamp: When failure occurred
            device_type: Device type
            background_noise: Background noise level
            speech_characteristics: User speech characteristics
            extracted_parameters: Parameters extracted
            confidence_score: System confidence
            executed_action: Action taken
            correct_parameters: Correct parameters
            frustration_level: User frustration (1-5)
            recent_commands: Command history
            device_state: Device state
            location: Location
            time_of_day: Time of day
            user_preferences: User preferences

        Returns:
            MiaVoiceCommandFailureOutput as dict
        """
        return await self._call_tool(
            "mia_analyze_failure",
            user_id=user_id,
            device_type=device_type,
            timestamp=timestamp or datetime.now().isoformat(),
            raw_input=raw_input,
            background_noise=background_noise,
            speech_characteristics=speech_characteristics,
            interpreted_intent=interpreted_intent,
            extracted_parameters=extracted_parameters or {},
            confidence_score=confidence_score,
            executed_action=executed_action,
            actual_intent=actual_intent,
            correct_parameters=correct_parameters or {},
            user_clarification=user_clarification,
            frustration_level=frustration_level,
            recent_commands=recent_commands or [],
            device_state=device_state or {},
            location=location,
            time_of_day=time_of_day,
            user_preferences=user_preferences or {},
        )

    async def synthesize_patterns(
        self,
        interactions: List[Dict[str, Any]],
        success_rate: float,
        avg_confidence: float,
        intent_count: int,
        user_count: int,
        interaction_count: Optional[int] = None,
        satisfaction_avg: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize patterns from multiple command interactions

        Args:
            interactions: List of interaction objects
            success_rate: Overall success rate
            avg_confidence: Average confidence score
            intent_count: Number of unique intents
            user_count: Number of unique users
            interaction_count: Total interactions (if None, uses len(interactions))
            satisfaction_avg: Average user satisfaction

        Returns:
            MiaVoiceCommandPatternOutput as dict
        """
        return await self._call_tool(
            "mia_synthesize_patterns",
            interaction_count=interaction_count or len(interactions),
            interactions=interactions,
            success_rate=success_rate,
            avg_confidence=avg_confidence,
            satisfaction_avg=satisfaction_avg,
            intent_count=intent_count,
            user_count=user_count,
        )

    async def analyze_context_effectiveness(
        self,
        sample_size: int,
        user_input: str,
        intent: str,
        raw_confidence: float,
        final_confidence: float,
        success: bool,
        no_context_accuracy: float,
        with_full_context: float,
        location: str = "unspecified",
        time_of_day: str = "unspecified",
        day_of_week: str = "unspecified",
        device_state: str = "idle",
        device_type: str = "unspecified",
        recent_activities: Optional[List[str]] = None,
        recent_commands: Optional[List[str]] = None,
        recent_count: int = 5,
        user_profile: Optional[Dict[str, Any]] = None,
        device_capabilities: Optional[List[str]] = None,
        network_status: str = "online",
        user_schedule: Optional[Dict[str, Any]] = None,
        ambient_conditions: Optional[Dict[str, Any]] = None,
        partial_context_accuracy: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Analyze context effectiveness in command interpretation

        Args:
            sample_size: Number of interactions analyzed
            user_input: Example user input
            intent: Command intent
            raw_confidence: Confidence without context
            final_confidence: Confidence with context
            success: Whether command succeeded
            no_context_accuracy: Accuracy without context
            with_full_context: Accuracy with full context
            location: User's location
            time_of_day: Time of day
            day_of_week: Day of week
            device_state: Device state
            device_type: Device type
            recent_activities: Recent user activities
            recent_commands: Recent commands
            recent_count: Number of recent commands
            user_profile: User profile
            device_capabilities: Device capabilities
            network_status: Network status
            user_schedule: User schedule
            ambient_conditions: Ambient conditions
            partial_context_accuracy: Accuracy with partial context

        Returns:
            MiaVoiceContextAnalyzerOutput as dict
        """
        return await self._call_tool(
            "mia_analyze_context_effectiveness",
            sample_size=sample_size,
            user_input=user_input,
            intent=intent,
            raw_confidence=raw_confidence,
            final_confidence=final_confidence,
            success=success,
            location=location,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            device_state=device_state,
            device_type=device_type,
            recent_activities=recent_activities or [],
            recent_commands=recent_commands or [],
            recent_count=recent_count,
            user_profile=user_profile or {},
            device_capabilities=device_capabilities or [],
            network_status=network_status,
            user_schedule=user_schedule,
            ambient_conditions=ambient_conditions or {},
            no_context_accuracy=no_context_accuracy,
            partial_context_accuracy=partial_context_accuracy,
            full_context_accuracy=with_full_context,
        )

    async def synthesize_knowledge(
        self,
        learning_insights: Dict[str, Any],
        failure_insights: Dict[str, Any],
        pattern_insights: Dict[str, Any],
        context_insights: Dict[str, Any],
        total_interactions: int = 0,
        time_period: Optional[str] = None,
        user_count: int = 0,
        device_count: int = 0,
        baseline_accuracy: float = 0.0,
        learning_count: int = 0,
        failure_count: int = 0,
        pattern_sample_size: int = 0,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize comprehensive knowledge from all learning dimensions

        Args:
            learning_insights: Command learning insights
            failure_insights: Failure analysis insights
            pattern_insights: Pattern synthesis insights
            context_insights: Context effectiveness insights
            total_interactions: Total interactions analyzed
            time_period: Time period covered
            user_count: Number of users
            device_count: Number of devices
            baseline_accuracy: Current baseline accuracy
            learning_count: Number of learning analyses
            failure_count: Number of failures analyzed
            pattern_sample_size: Size of pattern sample
            timestamp: Synthesis timestamp

        Returns:
            MiaVoiceCommandKnowledgeSynthesisOutput as dict
        """
        return await self._call_tool(
            "mia_synthesize_knowledge",
            learning_count=learning_count,
            learning_insights=learning_insights,
            failure_count=failure_count,
            failure_insights=failure_insights,
            pattern_sample_size=pattern_sample_size,
            pattern_insights=pattern_insights,
            context_insights=context_insights,
            timestamp=timestamp or datetime.now().isoformat(),
            total_interactions=total_interactions,
            time_period=time_period or "unspecified",
            user_count=user_count,
            device_count=device_count,
            baseline_accuracy=baseline_accuracy,
        )

    # ========================================================================
    # High-Level Workflows
    # ========================================================================

    async def run_learning_cycle(
        self,
        interactions: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        sample_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Run complete voice learning cycle on a batch of interactions

        Orchestrates: analyze → synthesize → analyze context → synthesize knowledge

        Args:
            interactions: List of command interaction objects
            user_id: Filter to specific user (optional)
            sample_size: Maximum interactions to analyze

        Returns:
            Complete learning cycle results
        """
        logger.info(f"Starting learning cycle with {len(interactions)} interactions")

        results = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "interaction_count": len(interactions),
            "learning_results": [],
            "pattern_results": None,
            "context_results": None,
            "synthesis_results": None,
            "errors": [],
        }

        try:
            # Step 1: Analyze learning from sample
            sample_interactions = interactions[:sample_size]
            for i, interaction in enumerate(sample_interactions):
                try:
                    learning = await self.analyze_command_learning(
                        user_id=user_id or interaction.get("user_id", "unknown"),
                        raw_input=interaction.get("raw_input", ""),
                        intent=interaction.get("intent", ""),
                        success=interaction.get("success", False),
                        confidence=interaction.get("confidence", 0.5),
                        timestamp=interaction.get("timestamp"),
                        device_type=interaction.get("device_type", "unknown"),
                        location=interaction.get("location", "unknown"),
                        time_of_day=interaction.get("time_of_day", "unknown"),
                        parameters=interaction.get("parameters"),
                        satisfaction_score=interaction.get("satisfaction_score"),
                        actual_action=interaction.get("actual_action", ""),
                        previous_intent=interaction.get("previous_intent"),
                        recent_commands=interaction.get("recent_commands"),
                        device_state=interaction.get("device_state"),
                        user_preferences=interaction.get("user_preferences"),
                    )
                    results["learning_results"].append(learning)

                    if (i + 1) % 20 == 0:
                        logger.info(f"Analyzed {i + 1} interactions")

                except Exception as e:
                    logger.warning(f"Learning analysis failed for interaction {i}: {e}")
                    results["errors"].append(str(e))

            # Step 2: Synthesize patterns
            try:
                success_count = sum(1 for i in interactions if i.get("success", False))
                success_rate = success_count / len(interactions) if interactions else 0.0
                avg_confidence = (
                    sum(i.get("confidence", 0.5) for i in interactions) / len(interactions)
                    if interactions
                    else 0.0
                )

                results["pattern_results"] = await self.synthesize_patterns(
                    interactions=interactions,
                    success_rate=success_rate,
                    avg_confidence=avg_confidence,
                    intent_count=len(set(i.get("intent") for i in interactions if i.get("intent"))),
                    user_count=1 if user_id else len(
                        set(i.get("user_id") for i in interactions if i.get("user_id"))
                    ),
                )
                logger.info("Pattern synthesis complete")

            except Exception as e:
                logger.error(f"Pattern synthesis failed: {e}")
                results["errors"].append(f"Pattern synthesis: {str(e)}")

            # Step 3: Analyze context effectiveness
            try:
                results["context_results"] = await self.analyze_context_effectiveness(
                    sample_size=len(interactions),
                    user_input="batch analysis",
                    intent="analysis",
                    raw_confidence=0.5,
                    final_confidence=0.7,
                    success=True,
                    no_context_accuracy=0.75,
                    with_full_context=0.89,
                )
                logger.info("Context analysis complete")

            except Exception as e:
                logger.error(f"Context analysis failed: {e}")
                results["errors"].append(f"Context analysis: {str(e)}")

            # Step 4: Synthesize comprehensive knowledge
            try:
                results["synthesis_results"] = await self.synthesize_knowledge(
                    learning_insights={
                        "count": len(results["learning_results"]),
                        "samples": results["learning_results"][:5],
                    },
                    failure_insights={},
                    pattern_insights=results["pattern_results"] or {},
                    context_insights=results["context_results"] or {},
                    total_interactions=len(interactions),
                    user_count=1 if user_id else len(
                        set(i.get("user_id") for i in interactions if i.get("user_id"))
                    ),
                    baseline_accuracy=success_rate if 'success_rate' in locals() else 0.0,
                )
                logger.info("Knowledge synthesis complete")

            except Exception as e:
                logger.error(f"Knowledge synthesis failed: {e}")
                results["errors"].append(f"Knowledge synthesis: {str(e)}")

            logger.info(
                f"Learning cycle complete: "
                f"{len(results['learning_results'])} analyses, "
                f"{len(results['errors'])} errors"
            )

        except Exception as e:
            logger.error(f"Learning cycle failed: {e}")
            results["errors"].append(f"Cycle failure: {str(e)}")

        return results
