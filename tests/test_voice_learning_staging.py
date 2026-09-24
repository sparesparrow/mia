"""Tests for MIA voice-learning staged prompt publication."""

import importlib.util
import json
import os
import sys

import pytest

_VOICE_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "orchestration",
    "mcp",
    "modules",
    "voice-learning",
)
_MODULES_DIR = os.path.dirname(_VOICE_DIR)
sys.path.insert(0, _VOICE_DIR)
sys.path.insert(0, _MODULES_DIR)

_SERVER_PATH = os.path.join(_VOICE_DIR, "voice_learning_server.py")
_spec = importlib.util.spec_from_file_location("voice_learning_server", _SERVER_PATH)
_voice_learning_module = importlib.util.module_from_spec(_spec)
sys.modules["voice_learning_server"] = _voice_learning_module
assert _spec.loader is not None
_spec.loader.exec_module(_voice_learning_module)

VoiceLearningServer = _voice_learning_module.VoiceLearningServer


class FakeMcpPromptsClient:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"ok": True, "id": "fake-created-prompt"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_learned_prompt_writes_staging_file_and_calls_create_prompt(tmp_path):
    client = FakeMcpPromptsClient()
    server = VoiceLearningServer(
        schemas_path=os.path.join(_VOICE_DIR, "schemas.json"),
        mcp_prompts_client=client,
        mcp_prompts_dir=str(tmp_path),
    )

    result = await server.publish_learned_prompt(
        {
            "name": "Prefer office lamp for implicit brightness commands",
            "pattern": "When the user says 'make it brighter' within 90 seconds of touching the office lamp, resolve 'it' to office lamp.",
            "intent": "implicit-reference",
        },
        metadata={"intent": "implicit-reference", "tags": ["office", "brightness"]},
    )

    staged_path = tmp_path / "staging" / f"{result['prompt_id']}.json"
    log_path = tmp_path / "staging" / "review-log.jsonl"

    assert staged_path.exists()
    staged_prompt = json.loads(staged_path.read_text())
    assert staged_prompt["category"] == "staging"
    assert "auto-generated" in staged_prompt["tags"]
    assert "staged" in staged_prompt["tags"]
    assert "#learned" in staged_prompt["tags"]
    assert staged_prompt["metadata"]["reviewStatus"] == "staged"
    assert "office lamp" in staged_prompt["content"]

    assert client.calls == [
        (
            "create_prompt",
            {
                "name": staged_prompt["name"],
                "content": staged_prompt["content"],
                "category": "staging",
                "tags": staged_prompt["tags"],
                "isTemplate": False,
                "variables": [],
            },
        )
    ]
    assert log_path.exists()
    assert json.loads(log_path.read_text().splitlines()[0])["mcp_create_prompt"] == "ok"
    assert server.get_statistics()["published_prompts"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_learned_prompt_keeps_file_when_create_prompt_fails(tmp_path):
    class FailingClient:
        async def call_tool(self, name, arguments):
            raise RuntimeError("stdio unavailable")

    server = VoiceLearningServer(
        schemas_path=os.path.join(_VOICE_DIR, "schemas.json"),
        mcp_prompts_client=FailingClient(),
        mcp_prompts_dir=str(tmp_path),
    )

    result = await server.publish_learned_prompt(
        {"summary": "Ask a clarification question when confidence falls below 0.40."},
        metadata={"intent": "fallback-escalation"},
    )

    staged_path = tmp_path / "staging" / f"{result['prompt_id']}.json"
    assert staged_path.exists()
    assert result["mcp_create_prompt"] == "failed"
    assert "stdio unavailable" in result["mcp_error"]
