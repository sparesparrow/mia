"""Test harness for core-orchestrator: EnhancedNLPProcessor, SessionContext, IntentResult.

Covers NLP intent parsing for 10 known command patterns, SessionContext.is_active()
timeout logic, and IntentResult construction.
"""

import importlib
import importlib.util
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Module loading — hyphenated directory requires importlib.util
# ---------------------------------------------------------------------------
_MCP_FW_PATH = os.path.join(
    os.path.dirname(__file__), "..", "orchestration", "mcp", "modules", "shared", "mcp_framework.py"
)
_fw_spec = importlib.util.spec_from_file_location("shared.mcp_framework", _MCP_FW_PATH)
_fw_module = importlib.util.module_from_spec(_fw_spec)
_fw_module.__package__ = "shared"
sys.modules.setdefault("shared", MagicMock())
sys.modules["shared.mcp_framework"] = _fw_module
_fw_spec.loader.exec_module(_fw_module)

_EO_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "core-orchestrator",
    "enhanced_orchestrator.py",
)
_eo_spec = importlib.util.spec_from_file_location("enhanced_orchestrator", _EO_PATH)
_eo_module = importlib.util.module_from_spec(_eo_spec)
_eo_module.__package__ = "modules.core_orchestrator"
sys.modules.setdefault("modules", MagicMock())
sys.modules.setdefault("modules.core_orchestrator", MagicMock())
sys.modules["modules.shared"] = MagicMock()
sys.modules["modules.shared.mcp_framework"] = _fw_module
_eo_spec.loader.exec_module(_eo_module)

EnhancedNLPProcessor = _eo_module.EnhancedNLPProcessor
SessionContext = _eo_module.SessionContext
IntentResult = _eo_module.IntentResult


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestIntentResult:
    """IntentResult dataclass construction and defaults."""

    def test_basic_construction(self):
        result = IntentResult(
            intent="play_music",
            confidence=0.9,
            parameters={"artist": "Bach"},
            original_text="play Bach",
        )
        assert result.intent == "play_music"
        assert result.confidence == 0.9
        assert result.parameters == {"artist": "Bach"}
        assert result.original_text == "play Bach"

    def test_alternatives_default_to_empty_list(self):
        result = IntentResult(intent="unknown", confidence=0.0, parameters={}, original_text="")
        assert result.alternatives == []

    def test_context_used_defaults_false(self):
        result = IntentResult(intent="navigation", confidence=0.5, parameters={}, original_text="navigate home")
        assert result.context_used is False


@pytest.mark.unit
class TestSessionContextIsActive:
    """SessionContext.is_active() respects the 30-minute window."""

    def _make_session(self, minutes_ago: float) -> SessionContext:
        ts = datetime.now() - timedelta(minutes=minutes_ago)
        return SessionContext(
            session_id="s1",
            user_id="u1",
            interface_type="voice",
            created_at=ts,
            last_accessed=ts,
        )

    def test_recent_session_is_active(self):
        session = self._make_session(minutes_ago=5)
        assert session.is_active() is True

    def test_session_at_boundary_is_active(self):
        session = self._make_session(minutes_ago=29)
        assert session.is_active() is True

    def test_expired_session_is_not_active(self):
        session = self._make_session(minutes_ago=31)
        assert session.is_active() is False

    def test_command_history_defaults_to_empty_list(self):
        session = self._make_session(minutes_ago=1)
        assert session.command_history == []


@pytest.mark.unit
class TestEnhancedNLPProcessorIntents:
    """EnhancedNLPProcessor.parse_command() maps commands to expected intents."""

    def setup_method(self):
        self.processor = EnhancedNLPProcessor()

    @pytest.mark.asyncio
    async def test_play_music_intent(self):
        result = await self.processor.parse_command("play some music on spotify")
        assert result.intent == "play_music"
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_control_volume_intent(self):
        result = await self.processor.parse_command("turn the volume up louder")
        assert result.intent == "control_volume"

    @pytest.mark.asyncio
    async def test_switch_audio_intent(self):
        result = await self.processor.parse_command("switch audio output to bluetooth speakers")
        assert result.intent == "switch_audio"

    @pytest.mark.asyncio
    async def test_system_control_intent(self):
        result = await self.processor.parse_command("open the application")
        assert result.intent == "system_control"

    @pytest.mark.asyncio
    async def test_smart_home_intent(self):
        result = await self.processor.parse_command("dim the lights at home")
        assert result.intent == "smart_home"

    @pytest.mark.asyncio
    async def test_communication_intent(self):
        result = await self.processor.parse_command("send a message on telegram")
        assert result.intent == "communication"

    @pytest.mark.asyncio
    async def test_navigation_intent(self):
        result = await self.processor.parse_command("navigate to the nearest gas station")
        assert result.intent == "navigation"

    @pytest.mark.asyncio
    async def test_hardware_control_intent(self):
        result = await self.processor.parse_command("set gpio pin high")
        assert result.intent == "hardware_control"

    @pytest.mark.asyncio
    async def test_question_answer_intent(self):
        result = await self.processor.parse_command("what is the current temperature")
        assert result.intent == "question_answer"

    @pytest.mark.asyncio
    async def test_unknown_returns_result(self):
        result = await self.processor.parse_command("xyzzy frobulate blarg")
        # May resolve to unknown or low-confidence; either is valid — just ensure no crash
        assert isinstance(result, IntentResult)
        assert isinstance(result.intent, str)

    @pytest.mark.asyncio
    async def test_empty_command_returns_unknown(self):
        result = await self.processor.parse_command("")
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_result_has_alternatives_list(self):
        result = await self.processor.parse_command("play loud music on spotify")
        assert isinstance(result.alternatives, list)
