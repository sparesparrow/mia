"""Tests for the MIA claudepy bridge.

The bridge directory is hyphenated, so tests load it by path just like the
existing core-orchestrator harness.
"""

import importlib.util
import os
import sys
from dataclasses import dataclass

import pytest

_BRIDGE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "claudepy-bridge",
    "mia_claudepy_bridge.py",
)
_spec = importlib.util.spec_from_file_location("mia_claudepy_bridge", _BRIDGE_PATH)
_bridge_module = importlib.util.module_from_spec(_spec)
sys.modules["mia_claudepy_bridge"] = _bridge_module
assert _spec.loader is not None
_spec.loader.exec_module(_bridge_module)

ClaudepyBridge = _bridge_module.ClaudepyBridge
InMemoryVoiceRAG = _bridge_module.InMemoryVoiceRAG
VoiceCommandResult = _bridge_module.VoiceCommandResult


class FakePromptClient:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"content": "Use concise MIA voice responses."}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


@dataclass
class FakeUsage:
    total_tokens: int = 42


@dataclass
class FakeResponse:
    content: str
    usage: FakeUsage


class FakeOrchestrator:
    def __init__(self):
        self.tasks = []

    async def run(self, task, provider_type=None):
        self.tasks.append(task)
        return FakeResponse(content="Turning on the office lights.", usage=FakeUsage())


class FakeExecuteOrchestrator:
    """Mirrors the real ``claudepy.agents.Orchestrator`` surface: ``execute(task)``.

    ``FakeOrchestrator`` above exercises a ``run(...)`` method that the real
    claudepy Orchestrator does not expose. This fake guards against the bridge
    only ever working against an imagined API and silently falling back once it
    is wired to the real orchestrator in production.
    """

    def __init__(self):
        self.tasks = []

    async def execute(self, task, sub_tasks=None):
        self.tasks.append(task)
        return FakeResponse(content="Navigating to the office.", usage=FakeUsage(total_tokens=7))


@pytest.mark.unit
class TestInMemoryVoiceRAG:
    @pytest.mark.asyncio
    async def test_retrieves_similar_interactions(self):
        rag = InMemoryVoiceRAG()
        await rag.add_interaction("turn on office lights", "Office lights are on.")
        await rag.add_interaction("play music", "Playing music.")

        context = await rag.retrieve("office lights please")

        assert len(context) == 1
        assert "office lights" in context[0]


@pytest.mark.unit
class TestClaudepyBridge:
    @pytest.mark.asyncio
    async def test_bridge_construction_defaults_to_uninitialized(self):
        bridge = ClaudepyBridge()

        assert bridge.default_provider == "kimi"
        assert bridge.initialized is False

    @pytest.mark.asyncio
    async def test_voice_command_round_trip_with_injected_orchestrator(self):
        orchestrator = FakeOrchestrator()
        prompt_client = FakePromptClient()
        rag = InMemoryVoiceRAG()
        await rag.add_interaction("turn on kitchen lights", "Kitchen lights are on.")
        bridge = ClaudepyBridge(
            orchestrator=orchestrator,
            mcp_prompts=prompt_client,
            rag=rag,
        )

        result = await bridge.process_voice_command(
            "turn on office lights",
            {"session_id": "s1", "location": "office"},
        )

        assert isinstance(result, VoiceCommandResult)
        assert result.response == "Turning on the office lights."
        assert result.provider_used == "kimi"
        assert result.tokens_used == 42
        assert result.intent == "smart_home"
        assert prompt_client.calls == [("get_prompt", {"id": "voice-command-design-principles"})]
        assert "Voice command: turn on office lights" in orchestrator.tasks[0]
        assert "Runtime context" in orchestrator.tasks[0]

    @pytest.mark.asyncio
    async def test_fallback_when_claudepy_is_unavailable(self):
        bridge = ClaudepyBridge()

        result = await bridge.process_voice_command("send a telegram message", use_prompts=False)

        assert result.provider_used == "fallback"
        assert result.intent == "communication"
        assert "message" in result.response.lower()

    @pytest.mark.asyncio
    async def test_voice_command_routes_through_real_execute_interface(self):
        # Regression guard: the real claudepy Orchestrator exposes execute(),
        # not run()/generate(). If the bridge cannot drive execute(), it silently
        # falls back and never actually reaches claudepy in production.
        orchestrator = FakeExecuteOrchestrator()
        bridge = ClaudepyBridge(orchestrator=orchestrator, mcp_prompts=FakePromptClient())

        result = await bridge.process_voice_command("navigate to the office")

        assert result.provider_used == "kimi"  # not "fallback"
        assert result.response == "Navigating to the office."
        assert result.tokens_used == 7
        assert orchestrator.tasks, "orchestrator.execute() was never called"
        assert "Voice command: navigate to the office" in orchestrator.tasks[0]

    def test_real_claudepy_orchestrator_exposes_execute(self):
        # Ties the FakeExecuteOrchestrator contract to the real API. Skips when
        # claudepy is not installed in this environment.
        pytest.importorskip("claudepy.agents")
        from claudepy.agents import Orchestrator

        assert hasattr(Orchestrator, "execute")
