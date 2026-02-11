"""
Integration Tests for Voice Learning System

Tests the end-to-end flow:
1. Tool handlers with mocked LLM
2. DTO instantiation and validation
3. Server registration and tool discovery
4. Client-server communication
5. Full learning cycle orchestration
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, AsyncMock, patch

# Import voice learning modules
from modules.voice_learning import (
    MiaVoiceCommandLearningOutput,
    MiaVoiceCommandFailureOutput,
    MiaVoiceCommandPatternOutput,
    MiaVoiceContextAnalyzerOutput,
    MiaVoiceCommandKnowledgeSynthesisOutput,
    VoiceLearningToolRegistry,
    validate_and_parse_json,
)
from modules.voice_learning.voice_learning_server import VoiceLearningServer
from modules.core_orchestrator.voice_learning_client import VoiceLearningClient


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_interaction():
    """Sample command interaction for testing"""
    return {
        "id": "cmd_001",
        "user_id": "user_test",
        "timestamp": datetime.now().isoformat(),
        "device_type": "phone",
        "location": "home",
        "time_of_day": "morning",
        "raw_input": "turn on the lights",
        "intent": "control.lights.on",
        "confidence": 0.95,
        "parameters": {"target": "lights", "state": "on"},
        "success": True,
        "satisfaction_score": 5,
        "actual_action": "turned_on_lights",
    }


@pytest.fixture
def failed_interaction():
    """Sample failed command interaction"""
    return {
        "id": "cmd_002",
        "user_id": "user_test",
        "timestamp": datetime.now().isoformat(),
        "device_type": "phone",
        "location": "car",
        "time_of_day": "afternoon",
        "raw_input": "play music",
        "interpreted_intent": "control.music.play_artist",
        "actual_intent": "control.music.play_playlist",
        "confidence": 0.62,
        "success": False,
        "frustration_level": 3,
    }


@pytest.fixture
def interaction_batch(sample_interaction, failed_interaction):
    """Batch of interactions for testing"""
    return [sample_interaction] * 10 + [failed_interaction] * 5


# ============================================================================
# DTO Tests
# ============================================================================

class TestDTOInstantiation:
    """Test DTO creation and serialization"""

    def test_learning_output_creation(self):
        """Test MiaVoiceCommandLearningOutput instantiation"""
        output = MiaVoiceCommandLearningOutput(
            success=True,
            command_pattern_family="control.lights.on",
            phrasing_variations=["turn on lights", "lights on"],
        )

        assert output.success is True
        assert output.command_pattern_family == "control.lights.on"
        assert len(output.phrasing_variations) == 2

    def test_failure_output_with_enum(self):
        """Test MiaVoiceCommandFailureOutput with enum"""
        from modules.voice_learning.dtos import FailureClassification

        output = MiaVoiceCommandFailureOutput(
            failure_classification=FailureClassification.SYSTEMATIC,
            preventable=True,
            root_causes=["speech_recognition_error"],
        )

        assert output.failure_classification == FailureClassification.SYSTEMATIC
        assert output.preventable is True

    def test_dto_serialization_with_datetime(self):
        """Test DTO serialization handles datetime"""
        from modules.voice_learning.dtos import dto_to_dict

        output = MiaVoiceCommandLearningOutput(
            success=True,
            command_pattern_family="test",
            extracted_at=datetime.now(),
        )

        result = dto_to_dict(output)
        assert isinstance(result["extracted_at"], str)  # Should be ISO string


# ============================================================================
# Validation Tests
# ============================================================================

class TestValidation:
    """Test JSON parsing and validation"""

    def test_validate_and_parse_json_success(self):
        """Test successful JSON parsing"""
        json_response = json.dumps({
            "success": True,
            "command_pattern_family": "lights.control",
            "phrasing_variations": ["turn on", "lights on"],
        })

        result = validate_and_parse_json("mia-voice-command-learning", json_response)

        assert result["success"] is True
        assert result["command_pattern_family"] == "lights.control"

    def test_validate_with_type_coercion(self):
        """Test type coercion (percentage to float)"""
        json_response = json.dumps({
            "success": "true",  # String instead of bool
            "command_pattern_family": "test",
            "parameter_extraction_quality": {
                "success": True,
                "confidence": "0.85",  # String percentage
            },
        })

        result = validate_and_parse_json("mia-voice-command-learning", json_response)
        # Should coerce to correct types
        assert isinstance(result["success"], bool)

    def test_partial_data_recovery(self):
        """Test graceful handling of missing optional fields"""
        json_response = json.dumps({
            "success": True,
            "command_pattern_family": "test",
            # Missing optional fields
        })

        result = validate_and_parse_json("mia-voice-command-learning", json_response)
        assert result["success"] is True
        # Should not raise error


# ============================================================================
# Tool Handler Tests
# ============================================================================

class TestToolHandlers:
    """Test individual tool handlers"""

    @pytest.mark.asyncio
    async def test_analyze_command_learning_handler(self, sample_interaction):
        """Test command learning handler"""
        registry = VoiceLearningToolRegistry()

        result_str = await registry.handlers["mia_analyze_command_learning"].handle(
            user_id=sample_interaction["user_id"],
            timestamp=sample_interaction["timestamp"],
            device_type=sample_interaction["device_type"],
            location=sample_interaction["location"],
            time_of_day=sample_interaction["time_of_day"],
            raw_input=sample_interaction["raw_input"],
            intent=sample_interaction["intent"],
            confidence=sample_interaction["confidence"],
            parameters=sample_interaction["parameters"],
            success=sample_interaction["success"],
            satisfaction_score=sample_interaction["satisfaction_score"],
            actual_action=sample_interaction["actual_action"],
            previous_intent=None,
            recent_commands=[],
            device_state={},
            user_preferences={},
        )

        result = json.loads(result_str)
        assert "success" in result
        assert "command_pattern_family" in result

    @pytest.mark.asyncio
    async def test_analyze_failure_handler(self, failed_interaction):
        """Test failure analysis handler"""
        registry = VoiceLearningToolRegistry()

        result_str = await registry.handlers["mia_analyze_failure"].handle(
            user_id=failed_interaction["user_id"],
            device_type=failed_interaction["device_type"],
            timestamp=failed_interaction["timestamp"],
            raw_input=failed_interaction["raw_input"],
            background_noise=None,
            speech_characteristics=None,
            interpreted_intent=failed_interaction["interpreted_intent"],
            extracted_parameters={},
            confidence_score=failed_interaction["confidence"],
            executed_action="",
            actual_intent=failed_interaction["actual_intent"],
            correct_parameters={},
            user_clarification="I meant playlist, not artist",
            frustration_level=failed_interaction["frustration_level"],
            recent_commands=[],
            device_state={},
            location=failed_interaction["location"],
            time_of_day=failed_interaction["time_of_day"],
            user_preferences={},
        )

        result = json.loads(result_str)
        assert "failure_classification" in result
        assert "preventable" in result

    @pytest.mark.asyncio
    async def test_synthesize_patterns_handler(self, interaction_batch):
        """Test pattern synthesis handler"""
        registry = VoiceLearningToolRegistry()

        result_str = await registry.handlers["mia_synthesize_patterns"].handle(
            interaction_count=len(interaction_batch),
            interactions=interaction_batch,
            success_rate=0.8,
            avg_confidence=0.85,
            satisfaction_avg=4.5,
            intent_count=2,
            user_count=1,
        )

        result = json.loads(result_str)
        assert "summary" in result
        assert "interaction_statistics" in result


# ============================================================================
# Server Tests
# ============================================================================

class TestVoiceLearningServer:
    """Test VoiceLearningServer functionality"""

    def test_server_initialization(self):
        """Test server initialization"""
        server = VoiceLearningServer()

        assert server.name == "voice-learning"
        assert server.version == "1.0.0"
        assert len(server.tools) == 5  # All 5 tools registered

    def test_tool_registration(self):
        """Test that all tools are properly registered"""
        server = VoiceLearningServer()

        tool_names = set(server.tools.keys())
        expected_names = {
            "mia_analyze_command_learning",
            "mia_analyze_failure",
            "mia_synthesize_patterns",
            "mia_analyze_context_effectiveness",
            "mia_synthesize_knowledge",
        }

        assert tool_names == expected_names

    def test_get_statistics(self):
        """Test server statistics"""
        server = VoiceLearningServer()
        stats = server.get_statistics()

        assert stats["name"] == "voice-learning"
        assert stats["tools_registered"] == 5
        assert stats["tools_called"] == 0
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_learning_cycle_basic(self, interaction_batch):
        """Test basic learning cycle execution"""
        server = VoiceLearningServer()

        results = await server.run_learning_cycle(
            interactions=interaction_batch,
            user_id="test_user",
            sample_size=5,
        )

        assert results["timestamp"] is not None
        assert results["interaction_count"] == len(interaction_batch)
        assert results["user_id"] == "test_user"


# ============================================================================
# Client Tests
# ============================================================================

class TestVoiceLearningClient:
    """Test VoiceLearningClient functionality"""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization"""
        client = VoiceLearningClient()

        assert client.server_url == "ws://voice-learning:8001"
        assert client.timeout == 30.0
        assert client.connected is False

    @pytest.mark.asyncio
    async def test_analyze_command_learning_method(self):
        """Test client method for command learning"""
        client = VoiceLearningClient()

        # Mock the websocket and _call_tool
        with patch.object(client, "_call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "success": True,
                "command_pattern_family": "control.lights.on",
            }

            result = await client.analyze_command_learning(
                user_id="user123",
                raw_input="turn on lights",
                intent="control.lights.on",
                success=True,
                confidence=0.95,
            )

            assert result["success"] is True
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_learning_cycle_workflow(self, interaction_batch):
        """Test full learning cycle workflow"""
        client = VoiceLearningClient()

        # Mock all tool calls
        with patch.object(client, "_call_tool", new_callable=AsyncMock) as mock_call:
            # Each tool call returns a result
            mock_call.side_effect = [
                {
                    "success": True,
                    "command_pattern_family": "test",
                },  # Learning
                {"summary": "patterns found"},  # Patterns
                {"context_impact_summary": "context helps"},  # Context
                {"executive_summary": "synthesis done"},  # Synthesis
            ]

            # Mock connect method
            with patch.object(client, "connect", new_callable=AsyncMock):
                client.connected = True

                results = await client.run_learning_cycle(
                    interactions=interaction_batch[:3],  # Small sample
                    user_id="test_user",
                )

                assert results["user_id"] == "test_user"
                assert len(results["learning_results"]) == 3


# ============================================================================
# End-to-End Integration Tests
# ============================================================================

class TestEndToEndIntegration:
    """Test complete system integration"""

    @pytest.mark.asyncio
    async def test_server_to_client_communication(self, sample_interaction):
        """Test server processes tool call and returns result"""
        server = VoiceLearningServer()

        # Get a tool and execute it directly
        tool = server.tools["mia_analyze_command_learning"]
        assert tool.handler is not None

        # Execute handler
        result_str = await tool.handler(
            user_id=sample_interaction["user_id"],
            timestamp=sample_interaction["timestamp"],
            device_type=sample_interaction["device_type"],
            location=sample_interaction["location"],
            time_of_day=sample_interaction["time_of_day"],
            raw_input=sample_interaction["raw_input"],
            intent=sample_interaction["intent"],
            confidence=sample_interaction["confidence"],
            parameters=sample_interaction["parameters"],
            success=sample_interaction["success"],
            satisfaction_score=sample_interaction["satisfaction_score"],
            actual_action=sample_interaction["actual_action"],
            previous_intent=None,
            recent_commands=[],
            device_state={},
            user_preferences={},
        )

        result = json.loads(result_str)
        assert "success" in result
        assert "command_pattern_family" in result

    @pytest.mark.asyncio
    async def test_batch_processing_pipeline(self, interaction_batch):
        """Test processing batch of interactions through pipeline"""
        server = VoiceLearningServer()

        # Run learning cycle
        results = await server.run_learning_cycle(
            interactions=interaction_batch,
            user_id="batch_test",
            sample_size=10,
        )

        # Verify results structure
        assert "timestamp" in results
        assert "interaction_count" in results
        assert "learning_results" in results
        assert "pattern_results" in results
        assert "context_results" in results
        assert "synthesis_results" in results


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test system performance characteristics"""

    @pytest.mark.asyncio
    async def test_tool_execution_time(self):
        """Test tool execution completes within timeout"""
        registry = VoiceLearningToolRegistry()

        import time

        start = time.time()
        await registry.call_tool(
            "mia_analyze_command_learning",
            user_id="perf_test",
            raw_input="test",
            intent="test",
            success=True,
            timestamp="2025-01-28T00:00:00",
            device_type="test",
            location="test",
            time_of_day="test",
            confidence=0.5,
            parameters={},
            satisfaction_score=None,
            actual_action="",
            previous_intent=None,
            recent_commands=[],
            device_state={},
            user_preferences={},
        )
        elapsed = time.time() - start

        # Tool should complete in reasonable time (< 5 seconds for no-LLM case)
        assert elapsed < 5.0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
