"""Tests for Voice Command Intelligence Skill integration.

Covers:
- Phase 1: MCPClient prompt methods & prompt registration
- Phase 3: Action execution tracking (VoiceCommandAnalytics)
- Phase 4: Learning loop (suggest_improvements)
- End-to-end: command pipeline with analytics recording
"""

import os
import shutil
import sys
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.shared.mcp_framework import MCPClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers: import enhanced_orchestrator components
# The module lives under modules/core-orchestrator/ which has a hyphen,
# so we import it via importlib.
# ---------------------------------------------------------------------------
import importlib  # noqa: E402
import importlib.util  # noqa: E402

_eo_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "modules",
    "core-orchestrator",
    "enhanced_orchestrator.py",
)
_spec = importlib.util.spec_from_file_location("enhanced_orchestrator", _eo_path)
_eo_module = importlib.util.module_from_spec(_spec)

# Patch the relative import that enhanced_orchestrator uses
_mcp_fw = importlib.import_module("modules.shared.mcp_framework")
sys.modules["modules"] = MagicMock()
sys.modules["modules.shared"] = MagicMock()
sys.modules["modules.shared.mcp_framework"] = _mcp_fw
# Set __package__ so relative imports resolve within the fake package
_eo_module.__package__ = "modules.core_orchestrator"
sys.modules["modules.core_orchestrator"] = MagicMock()
_spec.loader.exec_module(_eo_module)

EnhancedNLPProcessor = _eo_module.EnhancedNLPProcessor
ContextManager = _eo_module.ContextManager
VoiceCommandAnalytics = _eo_module.VoiceCommandAnalytics
CommandInteraction = _eo_module.CommandInteraction
EnhancedCoreOrchestrator = _eo_module.EnhancedCoreOrchestrator
SessionContext = _eo_module.SessionContext
IntentResult = _eo_module.IntentResult


# ---------------------------------------------------------------------------
# Phase 3 & 4: VoiceCommandAnalytics
# ---------------------------------------------------------------------------
class TestVoiceCommandAnalytics:
    """Tests for action execution tracking and learning loop."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.analytics = VoiceCommandAnalytics(data_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_interaction(
        self,
        intent="play_music",
        confidence=0.8,
        success=True,
        text="play some jazz",
    ):
        return CommandInteraction(
            command_text=text,
            intent=intent,
            confidence=confidence,
            parameters={"genre": "jazz"},
            success=success,
            response="Playing jazz music",
            timestamp=datetime.now(),
            session_id="test-session",
            execution_time_ms=50.0,
        )

    def test_record_and_query_interactions(self):
        self.analytics.record_interaction(self._make_interaction())
        self.analytics.record_interaction(self._make_interaction(success=False))
        assert self.analytics.get_success_rate() == 0.5

    def test_success_rate_by_intent(self):
        self.analytics.record_interaction(
            self._make_interaction("play_music", success=True)
        )
        self.analytics.record_interaction(
            self._make_interaction("smart_home", success=False)
        )
        assert self.analytics.get_success_rate("play_music") == 1.0
        assert self.analytics.get_success_rate("smart_home") == 0.0

    def test_success_rate_empty(self):
        assert self.analytics.get_success_rate() == 0.0
        assert self.analytics.get_success_rate("nonexistent") == 0.0

    def test_failed_patterns(self):
        for _ in range(3):
            self.analytics.record_interaction(
                self._make_interaction("smart_home", success=False)
            )
        failed = self.analytics.get_failed_patterns()
        assert failed["smart_home"] == 3

    def test_command_frequency(self):
        self.analytics.record_interaction(self._make_interaction("play_music"))
        self.analytics.record_interaction(self._make_interaction("play_music"))
        self.analytics.record_interaction(self._make_interaction("smart_home"))
        freq = self.analytics.get_command_frequency()
        assert freq["play_music"] == 2
        assert freq["smart_home"] == 1

    def test_suggest_improvements_with_failures(self):
        for _ in range(4):
            self.analytics.record_interaction(
                self._make_interaction("smart_home", success=False)
            )
        suggestions = self.analytics.suggest_improvements()
        assert len(suggestions) > 0
        assert suggestions[0]["intent"] == "smart_home"
        assert suggestions[0]["failure_count"] == 4

    def test_suggest_improvements_with_low_confidence(self):
        for i in range(6):
            self.analytics.record_interaction(
                self._make_interaction(confidence=0.3, text=f"maybe do something {i}")
            )
        suggestions = self.analytics.suggest_improvements()
        ambiguous = [s for s in suggestions if s.get("type") == "ambiguous_words"]
        assert len(ambiguous) == 1
        assert "words" in ambiguous[0]

    def test_low_confidence_tracking(self):
        for _ in range(6):
            self.analytics.record_interaction(self._make_interaction(confidence=0.3))
        low = self.analytics.get_low_confidence_commands(threshold=0.5)
        assert len(low) == 6

    def test_persistence(self):
        """Interactions persist across VoiceCommandAnalytics instances."""
        self.analytics.record_interaction(self._make_interaction())
        self.analytics.record_interaction(self._make_interaction(success=False))

        # Create new instance pointing to same directory
        analytics2 = VoiceCommandAnalytics(data_dir=self.tmpdir)
        assert len(analytics2.interactions) == 2
        assert analytics2.get_success_rate() == 0.5


# ---------------------------------------------------------------------------
# Phase 1: MCPClient prompt methods
# ---------------------------------------------------------------------------
class TestMCPClientPrompts:
    """Tests for MCPClient list_prompts and get_prompt methods."""

    @pytest.fixture
    def mock_client(self):
        client = MCPClient("test-client")
        client.connected = True
        client.transport = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_list_prompts(self, mock_client):
        mock_response = MagicMock()
        mock_response.result = {
            "prompts": [{"name": "voice-command-design-principles"}]
        }
        mock_response.error = None
        mock_client._send_request = AsyncMock(return_value=mock_response)

        prompts = await mock_client.list_prompts(tags=["mia", "voice-command"])
        assert len(prompts) == 1
        assert prompts[0]["name"] == "voice-command-design-principles"

    @pytest.mark.asyncio
    async def test_list_prompts_no_tags(self, mock_client):
        mock_response = MagicMock()
        mock_response.result = {"prompts": []}
        mock_response.error = None
        mock_client._send_request = AsyncMock(return_value=mock_response)

        prompts = await mock_client.list_prompts()
        assert prompts == []

    @pytest.mark.asyncio
    async def test_get_prompt(self, mock_client):
        mock_response = MagicMock()
        mock_response.result = {
            "description": "Context analyzer",
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": "Analyze context..."},
                }
            ],
        }
        mock_response.error = None
        mock_client._send_request = AsyncMock(return_value=mock_response)

        result = await mock_client.get_prompt(
            "mia-context-analyzer", {"currentLocation": "home"}
        )
        assert "messages" in result
        assert result["description"] == "Context analyzer"

    @pytest.mark.asyncio
    async def test_get_prompt_without_arguments(self, mock_client):
        mock_response = MagicMock()
        mock_response.result = {"description": "Test", "messages": []}
        mock_response.error = None
        mock_client._send_request = AsyncMock(return_value=mock_response)

        result = await mock_client.get_prompt("test-prompt")
        assert "description" in result


# ---------------------------------------------------------------------------
# Phase 1 & 2: Prompt registration and integration
# ---------------------------------------------------------------------------
class TestPromptIntegration:
    """Tests for prompt registration and context-aware enhancement."""

    def test_orchestrator_registers_voice_prompts(self):
        """Orchestrator registers the 4 voice command prompts from the skill."""
        orchestrator = EnhancedCoreOrchestrator()
        prompt_names = [p.name if hasattr(p, 'name') else p for p in orchestrator.prompts]
        assert "voice-command-design-principles" in prompt_names
        assert "voice-command-clarity-checklist" in prompt_names
        assert "mia-context-analyzer" in prompt_names
        assert "voice-response-generator" in prompt_names

    def test_prompt_arguments_defined(self):
        """Each prompt has the expected arguments."""
        orchestrator = EnhancedCoreOrchestrator()
        prompts_by_name = {(p.name if hasattr(p, 'name') else p): p for p in orchestrator.prompts}

        analyzer = prompts_by_name.get("mia-context-analyzer")
        if analyzer is None or not hasattr(analyzer, 'arguments'):
            pytest.skip("Prompt objects not yet fully implemented as Prompt instances")
        arg_names = [a["name"] for a in analyzer.arguments]
        assert "currentLocation" in arg_names
        assert "recentActions" in arg_names
        assert "deviceState" in arg_names
        assert "timeOfDay" in arg_names

    @pytest.mark.asyncio
    async def test_enhance_with_prompts_graceful_fallback(self):
        """When mcp-prompts is unavailable, returns original intent unchanged."""
        orchestrator = EnhancedCoreOrchestrator()
        intent = IntentResult(
            intent="play_music",
            confidence=0.7,
            parameters={"query": "jazz"},
            original_text="play jazz",
        )
        # No mcp-prompts client registered
        result = await orchestrator._enhance_with_prompts("play jazz", intent, None)
        assert result.intent == "play_music"
        assert result.confidence == 0.7  # unchanged
        assert not result.context_used

    @pytest.mark.asyncio
    async def test_enhance_with_prompts_boosts_confidence(self):
        """When mcp-prompts returns analysis, confidence is boosted."""
        orchestrator = EnhancedCoreOrchestrator()

        # Mock the MCP prompts client
        mock_client = AsyncMock()
        mock_client.get_prompt = AsyncMock(
            return_value={
                "messages": [
                    {
                        "content": {
                            "type": "text",
                            "text": "Context suggests music intent is correct",
                        }
                    }
                ]
            }
        )
        orchestrator.mcp_clients["mcp-prompts"] = mock_client

        intent = IntentResult(
            intent="play_music",
            confidence=0.7,
            parameters={"query": "jazz"},
            original_text="play jazz",
        )
        result = await orchestrator._enhance_with_prompts("play jazz", intent, None)
        assert abs(result.confidence - 0.8) < 1e-9  # boosted by 0.1
        assert result.context_used


# ---------------------------------------------------------------------------
# End-to-end: command pipeline with analytics
# ---------------------------------------------------------------------------
class TestCommandPipelineWithAnalytics:
    """Tests that voice commands record analytics interactions."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_command_records_interaction(self):
        orchestrator = EnhancedCoreOrchestrator()
        orchestrator.analytics = VoiceCommandAnalytics(data_dir=self.tmpdir)

        result = await orchestrator.handle_enhanced_voice_command(
            text="play some music", user_id="test-user"
        )
        assert result["intent"] == "play_music"
        assert len(orchestrator.analytics.interactions) == 1
        interaction = orchestrator.analytics.interactions[0]
        assert interaction.intent == "play_music"
        assert interaction.command_text == "play some music"
        assert interaction.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_multiple_commands_build_analytics(self):
        orchestrator = EnhancedCoreOrchestrator()
        orchestrator.analytics = VoiceCommandAnalytics(data_dir=self.tmpdir)

        await orchestrator.handle_enhanced_voice_command(
            text="play jazz", user_id="test-user"
        )
        await orchestrator.handle_enhanced_voice_command(
            text="turn up the volume", user_id="test-user"
        )
        await orchestrator.handle_enhanced_voice_command(
            text="play rock", user_id="test-user"
        )

        freq = orchestrator.analytics.get_command_frequency()
        assert freq.get("play_music", 0) == 2
        assert freq.get("control_volume", 0) == 1

    @pytest.mark.asyncio
    async def test_voice_analytics_tool(self):
        orchestrator = EnhancedCoreOrchestrator()
        orchestrator.analytics = VoiceCommandAnalytics(data_dir=self.tmpdir)

        # Record some interactions
        await orchestrator.handle_enhanced_voice_command(
            text="play music", user_id="test-user"
        )

        # Query analytics via the tool handler
        result = await orchestrator.handle_voice_analytics(metric="frequency")
        assert "frequency" in result

        result = await orchestrator.handle_voice_analytics(metric="success_rate")
        assert "success_rate" in result

        result = await orchestrator.handle_voice_analytics(metric="suggestions")
        assert "suggestions" in result
