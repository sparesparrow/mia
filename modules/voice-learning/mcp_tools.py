"""
MCP Tool Definitions for Voice Command Learning

Implements 5 MCP tools for voice command intelligence:
1. mia_analyze_command_learning - Extract learning from single command
2. mia_analyze_failure - Analyze command failure and recovery
3. mia_synthesize_patterns - Synthesize patterns from multiple commands
4. mia_analyze_context_effectiveness - Analyze context impact
5. mia_synthesize_knowledge - Comprehensive knowledge synthesis
"""

import json
import logging
from typing import Any, Dict, Optional, Callable, Awaitable
from dataclasses import asdict
import asyncio

from dtos import (
    MiaVoiceCommandLearningOutput,
    MiaVoiceCommandFailureOutput,
    MiaVoiceCommandPatternOutput,
    MiaVoiceContextAnalyzerOutput,
    MiaVoiceCommandKnowledgeSynthesisOutput,
)
from validation import (
    validate_and_parse_json,
    create_learning_output,
    create_failure_output,
    create_pattern_output,
    create_context_output,
    create_synthesis_output,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Input Schemas for Tool Calls
# ============================================================================

LEARNING_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {"type": "string"},
        "timestamp": {"type": "string"},
        "device_type": {"type": "string"},
        "location": {"type": "string"},
        "time_of_day": {"type": "string"},
        "raw_input": {"type": "string"},
        "intent": {"type": "string"},
        "confidence": {"type": "number"},
        "parameters": {"type": "object"},
        "success": {"type": "boolean"},
        "satisfaction_score": {"type": ["integer", "null"]},
        "actual_action": {"type": "string"},
        "previous_intent": {"type": ["string", "null"]},
        "recent_commands": {"type": "array"},
        "device_state": {"type": "object"},
        "user_preferences": {"type": "object"},
    },
    "required": ["user_id", "raw_input", "intent", "success"],
}

FAILURE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {"type": "string"},
        "device_type": {"type": "string"},
        "timestamp": {"type": "string"},
        "raw_input": {"type": "string"},
        "background_noise": {"type": ["string", "null"]},
        "speech_characteristics": {"type": ["string", "null"]},
        "interpreted_intent": {"type": "string"},
        "extracted_parameters": {"type": "object"},
        "confidence_score": {"type": "number"},
        "executed_action": {"type": "string"},
        "actual_intent": {"type": "string"},
        "correct_parameters": {"type": "object"},
        "user_clarification": {"type": "string"},
        "frustration_level": {"type": "integer"},
        "recent_commands": {"type": "array"},
        "device_state": {"type": "object"},
        "location": {"type": ["string", "null"]},
        "time_of_day": {"type": "string"},
        "user_preferences": {"type": "object"},
    },
    "required": ["user_id", "raw_input", "interpreted_intent", "actual_intent"],
}

PATTERN_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "interaction_count": {"type": "integer"},
        "interactions": {"type": "array"},
        "success_rate": {"type": "number"},
        "avg_confidence": {"type": "number"},
        "satisfaction_avg": {"type": ["number", "null"]},
        "intent_count": {"type": "integer"},
        "user_count": {"type": "integer"},
    },
    "required": ["interaction_count", "interactions"],
}

CONTEXT_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "sample_size": {"type": "integer"},
        "user_input": {"type": "string"},
        "intent": {"type": "string"},
        "raw_confidence": {"type": "number"},
        "final_confidence": {"type": "number"},
        "success": {"type": "boolean"},
        "location": {"type": "string"},
        "time_of_day": {"type": "string"},
        "day_of_week": {"type": "string"},
        "device_state": {"type": "string"},
        "device_type": {"type": "string"},
        "recent_activities": {"type": "array"},
        "recent_commands": {"type": "array"},
        "recent_count": {"type": "integer"},
        "user_profile": {"type": "object"},
        "device_capabilities": {"type": "array"},
        "network_status": {"type": "string"},
        "user_schedule": {"type": ["object", "null"]},
        "ambient_conditions": {"type": "object"},
        "no_context_accuracy": {"type": "number"},
        "partial_context_accuracy": {"type": "number"},
        "full_context_accuracy": {"type": "number"},
    },
    "required": ["sample_size", "user_input", "intent"],
}

SYNTHESIS_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "learning_count": {"type": "integer"},
        "learning_insights": {"type": ["object", "array"]},
        "failure_count": {"type": "integer"},
        "failure_insights": {"type": ["object", "array"]},
        "pattern_sample_size": {"type": "integer"},
        "pattern_insights": {"type": ["object", "array"]},
        "context_insights": {"type": ["object", "array"]},
        "timestamp": {"type": "string"},
        "total_interactions": {"type": "integer"},
        "time_period": {"type": "string"},
        "user_count": {"type": "integer"},
        "device_count": {"type": "integer"},
        "baseline_accuracy": {"type": "number"},
    },
    "required": ["learning_insights", "failure_insights", "pattern_insights", "context_insights"],
}


# ============================================================================
# Output Schemas for Tool Returns
# ============================================================================

LEARNING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "command_pattern_family": {"type": "string"},
        "phrasing_variations": {"type": "array"},
    },
    "required": ["success", "command_pattern_family"],
}

FAILURE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "failure_classification": {
            "type": "string",
            "enum": ["edge_case", "systematic", "user_specific"],
        },
        "preventable": {"type": "boolean"},
    },
    "required": ["failure_classification", "preventable"],
}

PATTERN_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "intent_families": {"type": "array"},
    },
    "required": ["summary"],
}

CONTEXT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "context_impact_summary": {"type": "string"},
        "accuracy_metrics": {"type": "object"},
    },
    "required": ["context_impact_summary"],
}

SYNTHESIS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "command_family_library": {"type": "array"},
    },
    "required": ["executive_summary"],
}


# ============================================================================
# Tool Handler Base Class
# ============================================================================

class VoiceToolHandler:
    """Base handler for voice learning tools"""

    def __init__(self, llm_client: Any = None, schemas_path: str = "schemas.json"):
        """
        Initialize handler

        Args:
            llm_client: LLM client for prompt rendering and completion
            schemas_path: Path to JSON schemas file
        """
        self.llm_client = llm_client
        self.schemas_path = schemas_path
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load validation schemas"""
        try:
            with open(self.schemas_path, 'r') as f:
                self.schemas = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Schemas file not found at {self.schemas_path}, continuing without validation")
            self.schemas = {}

    async def _validate_input(self, tool_id: str, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate input against schema"""
        from jsonschema import validate, ValidationError

        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            logger.warning(f"Input validation failed for {tool_id}: {e.message}")
            # Continue - allow best-effort processing


# ============================================================================
# Tool 1: Analyze Command Learning
# ============================================================================

class AnalyzeCommandLearningHandler(VoiceToolHandler):
    """Handler for mia_analyze_command_learning tool"""

    async def handle(self, **kwargs) -> str:
        """
        Analyze learning from a voice command interaction

        Args:
            user_id: User identifier
            timestamp: When command was issued
            device_type: Type of device (phone, car, etc)
            location: User's location
            time_of_day: Time of day
            raw_input: What user said
            intent: Interpreted intent
            confidence: Confidence score (0-1)
            parameters: Extracted parameters dict
            success: Whether command succeeded
            satisfaction_score: User satisfaction (1-5, optional)
            actual_action: What action was taken
            previous_intent: Previous command intent
            recent_commands: List of recent commands
            device_state: Current device state
            user_preferences: User preferences dict

        Returns:
            JSON string with MiaVoiceCommandLearningOutput
        """
        try:
            # Validate input
            await self._validate_input("mia_analyze_command_learning", kwargs, LEARNING_INPUT_SCHEMA)

            # Call LLM (if available) or return minimal analysis
            if self.llm_client:
                llm_response = await self.llm_client.analyze_command_learning(**kwargs)
                output_data = validate_and_parse_json(
                    "mia-voice-command-learning",
                    llm_response,
                    self.schemas.get("mia-voice-command-learning"),
                )
            else:
                # Fallback: minimal analysis
                output_data = {
                    "success": kwargs.get("success", False),
                    "command_pattern_family": kwargs.get("intent", "unknown"),
                    "phrasing_variations": [kwargs.get("raw_input", "")],
                }

            # Hydrate DTO
            result = create_learning_output(output_data)

            # Return as JSON string
            return json.dumps(self._dto_to_dict(result))

        except Exception as e:
            logger.error(f"Error in analyze_command_learning: {e}")
            raise

    def _dto_to_dict(self, dto: Any) -> Dict[str, Any]:
        """Convert DTO to dictionary"""
        from dtos import dto_to_dict
        return dto_to_dict(dto)


# ============================================================================
# Tool 2: Analyze Command Failure
# ============================================================================

class AnalyzeCommandFailureHandler(VoiceToolHandler):
    """Handler for mia_analyze_failure tool"""

    async def handle(self, **kwargs) -> str:
        """
        Analyze a voice command failure

        Args:
            user_id: User identifier
            device_type: Type of device
            timestamp: When failure occurred
            raw_input: What user said
            background_noise: Background noise level
            speech_characteristics: User's speech characteristics
            interpreted_intent: What MIA thought was intended
            extracted_parameters: Parameters MIA extracted
            confidence_score: MIA's confidence score
            executed_action: What action MIA took
            actual_intent: What user actually wanted
            correct_parameters: Correct parameters
            user_clarification: User's clarification
            frustration_level: User frustration (1-5)
            recent_commands: Recent command history
            device_state: Current device state
            location: User's location
            time_of_day: Time of day
            user_preferences: User preferences

        Returns:
            JSON string with MiaVoiceCommandFailureOutput
        """
        try:
            # Validate input
            await self._validate_input("mia_analyze_failure", kwargs, FAILURE_INPUT_SCHEMA)

            # Call LLM (if available) or return minimal analysis
            if self.llm_client:
                llm_response = await self.llm_client.analyze_failure(**kwargs)
                output_data = validate_and_parse_json(
                    "mia-voice-command-failure-analysis",
                    llm_response,
                    self.schemas.get("mia-voice-command-failure-analysis"),
                )
            else:
                # Fallback: classify as edge case
                output_data = {
                    "failure_classification": "edge_case",
                    "preventable": False,
                    "root_causes": ["unknown"],
                }

            # Hydrate DTO
            result = create_failure_output(output_data)

            # Return as JSON string
            return json.dumps(self._dto_to_dict(result))

        except Exception as e:
            logger.error(f"Error in analyze_failure: {e}")
            raise

    def _dto_to_dict(self, dto: Any) -> Dict[str, Any]:
        """Convert DTO to dictionary"""
        from dtos import dto_to_dict
        return dto_to_dict(dto)


# ============================================================================
# Tool 3: Synthesize Patterns
# ============================================================================

class SynthesizePatternsHandler(VoiceToolHandler):
    """Handler for mia_synthesize_patterns tool"""

    async def handle(self, **kwargs) -> str:
        """
        Synthesize patterns from multiple command interactions

        Args:
            interaction_count: Number of interactions to analyze
            interactions: List of interaction objects
            success_rate: Overall success rate
            avg_confidence: Average confidence score
            satisfaction_avg: Average user satisfaction
            intent_count: Number of unique intents
            user_count: Number of unique users

        Returns:
            JSON string with MiaVoiceCommandPatternOutput
        """
        try:
            # Validate input
            await self._validate_input("mia_synthesize_patterns", kwargs, PATTERN_INPUT_SCHEMA)

            # Validate minimum sample size for pattern synthesis
            interaction_count = kwargs.get("interaction_count", 0)
            if interaction_count < 10:
                logger.warning(f"Pattern synthesis called with only {interaction_count} interactions (minimum 10 recommended)")

            # Call LLM (if available) or return minimal analysis
            if self.llm_client:
                llm_response = await self.llm_client.synthesize_patterns(**kwargs)
                output_data = validate_and_parse_json(
                    "mia-voice-command-pattern-synthesis",
                    llm_response,
                    self.schemas.get("mia-voice-command-pattern-synthesis"),
                )
            else:
                # Fallback: minimal pattern output
                output_data = {
                    "summary": f"Analyzed {interaction_count} interactions",
                    "interaction_statistics": {
                        "total_analyzed": interaction_count,
                        "success_rate": kwargs.get("success_rate", 0.0),
                    },
                    "intent_families": [],
                }

            # Hydrate DTO
            result = create_pattern_output(output_data)

            # Return as JSON string
            return json.dumps(self._dto_to_dict(result))

        except Exception as e:
            logger.error(f"Error in synthesize_patterns: {e}")
            raise

    def _dto_to_dict(self, dto: Any) -> Dict[str, Any]:
        """Convert DTO to dictionary"""
        from dtos import dto_to_dict
        return dto_to_dict(dto)


# ============================================================================
# Tool 4: Analyze Context Effectiveness
# ============================================================================

class AnalyzeContextEffectivenessHandler(VoiceToolHandler):
    """Handler for mia_analyze_context_effectiveness tool"""

    async def handle(self, **kwargs) -> str:
        """
        Analyze how context improves command interpretation

        Args:
            sample_size: Number of interactions analyzed
            user_input: Example user input
            intent: Command intent
            raw_confidence: Confidence without context
            final_confidence: Confidence with context
            success: Whether command succeeded
            location: User's location
            time_of_day: Time of day
            day_of_week: Day of week
            device_state: Current device state
            device_type: Type of device
            recent_activities: Recent user activities
            recent_commands: Recent commands
            recent_count: Number of recent commands to consider
            user_profile: User profile information
            device_capabilities: Device capabilities
            network_status: Network connectivity status
            user_schedule: User's schedule
            ambient_conditions: Ambient conditions
            no_context_accuracy: Accuracy without context
            partial_context_accuracy: Accuracy with partial context
            full_context_accuracy: Accuracy with full context

        Returns:
            JSON string with MiaVoiceContextAnalyzerOutput
        """
        try:
            # Validate input
            await self._validate_input("mia_analyze_context_effectiveness", kwargs, CONTEXT_INPUT_SCHEMA)

            # Call LLM (if available) or return minimal analysis
            if self.llm_client:
                llm_response = await self.llm_client.analyze_context(**kwargs)
                output_data = validate_and_parse_json(
                    "mia-voice-context-analyzer",
                    llm_response,
                    self.schemas.get("mia-voice-context-analyzer"),
                )
            else:
                # Fallback: minimal context analysis
                output_data = {
                    "context_impact_summary": "Context analysis unavailable",
                    "accuracy_metrics": {
                        "without_context": kwargs.get("no_context_accuracy", 0.0),
                        "with_full_context": kwargs.get("full_context_accuracy", 0.0),
                        "context_improvement_percentage": 0.0,
                    },
                }

            # Hydrate DTO
            result = create_context_output(output_data)

            # Return as JSON string
            return json.dumps(self._dto_to_dict(result))

        except Exception as e:
            logger.error(f"Error in analyze_context_effectiveness: {e}")
            raise

    def _dto_to_dict(self, dto: Any) -> Dict[str, Any]:
        """Convert DTO to dictionary"""
        from dtos import dto_to_dict
        return dto_to_dict(dto)


# ============================================================================
# Tool 5: Synthesize Knowledge
# ============================================================================

class SynthesizeKnowledgeHandler(VoiceToolHandler):
    """Handler for mia_synthesize_knowledge tool"""

    async def handle(self, **kwargs) -> str:
        """
        Synthesize comprehensive knowledge from all learning dimensions

        Args:
            learning_count: Number of learning signals analyzed
            learning_insights: Command learning insights
            failure_count: Number of failures analyzed
            failure_insights: Failure analysis insights
            pattern_sample_size: Size of pattern sample
            pattern_insights: Pattern synthesis insights
            context_insights: Context effectiveness insights
            timestamp: Synthesis timestamp
            total_interactions: Total interactions analyzed
            time_period: Time period covered
            user_count: Number of users analyzed
            device_count: Number of devices analyzed
            baseline_accuracy: Current baseline accuracy

        Returns:
            JSON string with MiaVoiceCommandKnowledgeSynthesisOutput
        """
        try:
            # Validate input
            await self._validate_input("mia_synthesize_knowledge", kwargs, SYNTHESIS_INPUT_SCHEMA)

            # Call LLM (if available) or return minimal analysis
            if self.llm_client:
                llm_response = await self.llm_client.synthesize_knowledge(**kwargs)
                output_data = validate_and_parse_json(
                    "mia-voice-command-knowledge-synthesis",
                    llm_response,
                    self.schemas.get("mia-voice-command-knowledge-synthesis"),
                )
            else:
                # Fallback: minimal knowledge synthesis
                from datetime import datetime
                output_data = {
                    "executive_summary": "Knowledge synthesis unavailable",
                    "synthesis_timestamp": datetime.now().isoformat(),
                    "data_sources": {
                        "total_interactions_analyzed": kwargs.get("total_interactions", 0),
                        "time_period": kwargs.get("time_period"),
                        "users_represented": kwargs.get("user_count", 0),
                        "baseline_accuracy": kwargs.get("baseline_accuracy", 0.0),
                    },
                }

            # Hydrate DTO
            result = create_synthesis_output(output_data)

            # Return as JSON string
            return json.dumps(self._dto_to_dict(result))

        except Exception as e:
            logger.error(f"Error in synthesize_knowledge: {e}")
            raise

    def _dto_to_dict(self, dto: Any) -> Dict[str, Any]:
        """Convert DTO to dictionary"""
        from dtos import dto_to_dict
        return dto_to_dict(dto)


# ============================================================================
# Tool Registry
# ============================================================================

class VoiceLearningToolRegistry:
    """Registry for all voice learning tools"""

    def __init__(self, llm_client: Any = None, schemas_path: str = "schemas.json"):
        """Initialize tool registry with handlers"""
        self.handlers = {
            "mia_analyze_command_learning": AnalyzeCommandLearningHandler(llm_client, schemas_path),
            "mia_analyze_failure": AnalyzeCommandFailureHandler(llm_client, schemas_path),
            "mia_synthesize_patterns": SynthesizePatternsHandler(llm_client, schemas_path),
            "mia_analyze_context_effectiveness": AnalyzeContextEffectivenessHandler(llm_client, schemas_path),
            "mia_synthesize_knowledge": SynthesizeKnowledgeHandler(llm_client, schemas_path),
        }

        self.tools = [
            {
                "name": "mia_analyze_command_learning",
                "description": "Extract learning signals from a voice command interaction. Analyzes success patterns, identifies user variations, and discovers learning opportunities.",
                "inputSchema": LEARNING_INPUT_SCHEMA,
            },
            {
                "name": "mia_analyze_failure",
                "description": "Analyze voice command failures and misinterpretations. Identifies root causes, recovery strategies, and prevention opportunities.",
                "inputSchema": FAILURE_INPUT_SCHEMA,
            },
            {
                "name": "mia_synthesize_patterns",
                "description": "Synthesize generalizable patterns from multiple voice command interactions. Extracts command families, variations, and improved recognition rules.",
                "inputSchema": PATTERN_INPUT_SCHEMA,
            },
            {
                "name": "mia_analyze_context_effectiveness",
                "description": "Analyze how context signals (location, time, device state, history) influence command interpretation accuracy.",
                "inputSchema": CONTEXT_INPUT_SCHEMA,
            },
            {
                "name": "mia_synthesize_knowledge",
                "description": "Synthesize all learning from voice command analysis into comprehensive improvement strategies and knowledge updates.",
                "inputSchema": SYNTHESIS_INPUT_SCHEMA,
            },
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> str:
        """Call a tool by name with given arguments"""
        if tool_name not in self.handlers:
            raise ValueError(f"Unknown tool: {tool_name}")

        handler = self.handlers[tool_name]
        return await handler.handle(**kwargs)
