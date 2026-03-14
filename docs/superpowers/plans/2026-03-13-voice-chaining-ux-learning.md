# Voice Command Chaining, Automotive UX & Learning Loop — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add compound command chaining, structured voice dialog templates with bilingual support, and wire the existing learning infrastructure to real Redis/Postgres data.

**Architecture:** Layered pipeline — `ChainParser` splits compound text post-STT, `DialogRenderer` selects bilingual response templates per driving context, `LearningStreamConsumer` taps Redis Streams to feed `InteractionStore` (Postgres) and triggers learning cycles via `LearningTriggerManager`.

**Tech Stack:** Python 3.12, FastAPI, asyncio, redis-py (Streams), asyncpg (Postgres), pytest

**Spec:** `docs/superpowers/specs/2026-03-13-voice-command-chaining-ux-learning-design.md`

---

## Chunk 1: Feature C — Command Chain Parser

### Task 1: ChainParser data structures and splitting logic

**Files:**
- Create: `orchestration/mcp/modules/command-chaining/__init__.py`
- Create: `orchestration/mcp/modules/command-chaining/chain_parser.py`
- Create: `tests/unit/test_chain_parser.py`

- [ ] **Step 1: Create test file with failing tests for splitting logic**

```python
# tests/unit/test_chain_parser.py
import pytest
from orchestration.mcp.modules.command_chaining.chain_parser import ChainParser, ChainedCommand

class TestChainParserSplitting:
    def setup_method(self):
        self.parser = ChainParser()

    def test_single_command_passthrough(self):
        result = self.parser.parse("play jazz", user_id="u1")
        assert len(result.sub_commands) == 1
        assert result.sub_commands[0] == "play jazz"

    def test_english_and_connector(self):
        result = self.parser.parse("play jazz and set temp to 22", user_id="u1")
        assert result.sub_commands == ["play jazz", "set temp to 22"]
        assert result.language == "en"

    def test_english_then_connector(self):
        result = self.parser.parse("play jazz then turn on lights", user_id="u1")
        assert result.sub_commands == ["play jazz", "turn on lights"]

    def test_czech_a_connector(self):
        result = self.parser.parse("přehraj jazz a nastav teplotu na 22", user_id="u1")
        assert result.sub_commands == ["přehraj jazz", "nastav teplotu na 22"]
        assert result.language == "cs"

    def test_czech_potom_connector(self):
        result = self.parser.parse("přehraj jazz potom nastav teplotu", user_id="u1")
        assert result.sub_commands == ["přehraj jazz", "nastav teplotu"]

    def test_quoted_string_not_split(self):
        result = self.parser.parse('play "rock and roll"', user_id="u1")
        assert len(result.sub_commands) == 1
        assert result.sub_commands[0] == 'play "rock and roll"'

    def test_skip_list_entities(self):
        result = self.parser.parse("play rock and roll and set volume to 50", user_id="u1")
        assert result.sub_commands == ["play rock and roll", "set volume to 50"]

    def test_chain_id_is_uuid(self):
        import uuid
        result = self.parser.parse("play jazz", user_id="u1")
        uuid.UUID(result.chain_id)  # Raises if not valid UUID

    def test_timestamp_is_iso(self):
        from datetime import datetime
        result = self.parser.parse("play jazz", user_id="u1")
        datetime.fromisoformat(result.timestamp)

    def test_case_insensitive_connectors(self):
        result = self.parser.parse("play jazz AND set temp to 22", user_id="u1")
        assert len(result.sub_commands) == 2

    def test_multiple_connectors(self):
        result = self.parser.parse("play jazz and set temp to 22 then turn on lights", user_id="u1")
        assert len(result.sub_commands) == 3

    def test_empty_segments_stripped(self):
        result = self.parser.parse("and play jazz and", user_id="u1")
        assert all(cmd.strip() for cmd in result.sub_commands)

    def test_language_override(self):
        result = self.parser.parse("play jazz and set temp", user_id="u1", language="cs")
        assert result.language == "cs"

    def test_multiple_skip_list_entities(self):
        """Regression: skip-list replacement must handle multiple entities in one input."""
        result = self.parser.parse("play rock and roll and rhythm and blues", user_id="u1")
        assert result.sub_commands == ["play rock and roll", "rhythm and blues"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_chain_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orchestration.mcp.modules.command_chaining'`

- [ ] **Step 3: Implement ChainParser**

```python
# orchestration/mcp/modules/command-chaining/__init__.py
from .chain_parser import ChainParser, ChainedCommand, SubCommandResult, ChainResult

# orchestration/mcp/modules/command-chaining/chain_parser.py
"""Command Chain Parser — splits compound voice commands into sub-commands."""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

CONNECTORS: Dict[str, List[str]] = {
    "en": ["and", "then", "also", "plus"],
    "cs": ["a", "potom", "pak", "také"],
}

# Multi-word entities that should not be split on "and"
SKIP_LIST = [
    "rock and roll",
    "rhythm and blues",
    "salt and pepper",
    "bread and butter",
    "search and rescue",
]


@dataclass
class ChainedCommand:
    chain_id: str
    original: str
    sub_commands: List[str]
    language: str
    timestamp: str


@dataclass
class SubCommandResult:
    index: int
    sub_command: str
    intent: str
    confidence: float
    success: bool
    error: Optional[str]
    duration_ms: float


@dataclass
class ChainResult:
    chain_id: str
    original: str
    results: List[SubCommandResult]
    total_duration_ms: float
    partial_failure: bool
    all_failed: bool


class ChainParser:
    """Splits compound voice commands into independent sub-commands."""

    def __init__(self, skip_list: Optional[List[str]] = None):
        self.skip_list = [s.lower() for s in (skip_list or SKIP_LIST)]

    def parse(self, text: str, user_id: str, language: Optional[str] = None) -> ChainedCommand:
        lang = language or self._detect_language(text)
        sub_commands = self._split(text, lang)
        return ChainedCommand(
            chain_id=str(uuid.uuid4()),
            original=text,
            sub_commands=sub_commands,
            language=lang,
            timestamp=datetime.now().isoformat(),
        )

    def _detect_language(self, text: str) -> str:
        czech_chars = set("áčďéěíňóřšťúůýž")
        if any(c in czech_chars for c in text.lower()):
            return "cs"
        return "en"

    def _split(self, text: str, language: str) -> List[str]:
        # Protect quoted strings
        protected = {}
        counter = 0

        def protect_quoted(match):
            nonlocal counter
            key = f"__QUOTED_{counter}__"
            protected[key] = match.group(0)
            counter += 1
            return key

        working = re.sub(r'"[^"]*"', protect_quoted, text)

        # Protect skip-list entities (use re.sub to avoid position-fragile slicing)
        for entity in self.skip_list:
            entity_pattern = re.compile(re.escape(entity), re.IGNORECASE)
            def protect_entity(match):
                nonlocal counter
                key = f"__QUOTED_{counter}__"
                protected[key] = match.group(0)
                counter += 1
                return key
            working = entity_pattern.sub(protect_entity, working)

        # Split on connectors
        connectors = CONNECTORS.get(language, CONNECTORS["en"])
        # Build pattern: word boundary + connector + word boundary
        connector_pattern = r'\b(?:' + '|'.join(re.escape(c) for c in connectors) + r')\b'
        parts = re.split(connector_pattern, working, flags=re.IGNORECASE)

        # Restore protected strings and strip
        result = []
        for part in parts:
            restored = part
            for key, value in protected.items():
                restored = restored.replace(key, value)
            restored = restored.strip()
            if restored:
                result.append(restored)

        return result if result else [text.strip()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_chain_parser.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/mcp/modules/command-chaining/ tests/unit/test_chain_parser.py
git commit -m "feat: add ChainParser with bilingual splitting logic and skip-list protection"
```

---

### Task 2: Chain execution and result aggregation

**Files:**
- Create: `orchestration/mcp/modules/command-chaining/chain_executor.py`
- Create: `tests/unit/test_chain_executor.py`

- [ ] **Step 1: Write failing tests for chain execution**

```python
# tests/unit/test_chain_executor.py
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from orchestration.mcp.modules.command_chaining.chain_parser import (
    ChainedCommand, SubCommandResult, ChainResult,
)
from orchestration.mcp.modules.command_chaining.chain_executor import ChainExecutor


class TestChainExecutor:
    def setup_method(self):
        self.mock_agent = AsyncMock()
        self.executor = ChainExecutor(voice_agent=self.mock_agent)

    @pytest.mark.asyncio
    async def test_single_command_execution(self):
        self.mock_agent.process_voice_command.return_value = json.dumps({
            "command_id": "cmd1", "intent": "play_music",
            "confidence": 0.9, "status": "completed",
            "analysis_metadata": {"duration_ms": 50},
        })
        chain = ChainedCommand(
            chain_id="chain1", original="play jazz",
            sub_commands=["play jazz"], language="en",
            timestamp="2026-03-13T00:00:00",
        )
        result = await self.executor.execute(chain, user_id="u1")
        assert len(result.results) == 1
        assert result.results[0].success is True
        assert result.partial_failure is False
        assert result.all_failed is False

    @pytest.mark.asyncio
    async def test_multi_command_best_effort(self):
        # First succeeds, second fails
        self.mock_agent.process_voice_command.side_effect = [
            json.dumps({
                "command_id": "cmd1", "intent": "play_music",
                "confidence": 0.9, "status": "completed",
                "analysis_metadata": {"duration_ms": 50},
            }),
            json.dumps({
                "command_id": "cmd2", "intent": "climate",
                "confidence": 0.8, "status": "failed",
                "error": "HVAC offline",
                "analysis_metadata": {"duration_ms": 30},
            }),
        ]
        chain = ChainedCommand(
            chain_id="chain2", original="play jazz and set temp to 22",
            sub_commands=["play jazz", "set temp to 22"], language="en",
            timestamp="2026-03-13T00:00:00",
        )
        result = await self.executor.execute(chain, user_id="u1")
        assert len(result.results) == 2
        assert result.partial_failure is True
        assert result.all_failed is False

    @pytest.mark.asyncio
    async def test_all_failed(self):
        self.mock_agent.process_voice_command.return_value = json.dumps({
            "command_id": "cmd1", "intent": "unknown",
            "confidence": 0.0, "status": "failed",
            "error": "not recognized",
            "analysis_metadata": {"duration_ms": 10},
        })
        chain = ChainedCommand(
            chain_id="chain3", original="foo and bar",
            sub_commands=["foo", "bar"], language="en",
            timestamp="2026-03-13T00:00:00",
        )
        result = await self.executor.execute(chain, user_id="u1")
        assert result.all_failed is True

    @pytest.mark.asyncio
    async def test_chain_id_passed_to_agent(self):
        self.mock_agent.process_voice_command.return_value = json.dumps({
            "command_id": "cmd1", "intent": "play_music",
            "confidence": 0.9, "status": "completed",
            "analysis_metadata": {"duration_ms": 50},
        })
        chain = ChainedCommand(
            chain_id="chain4", original="play jazz",
            sub_commands=["play jazz"], language="en",
            timestamp="2026-03-13T00:00:00",
        )
        await self.executor.execute(chain, user_id="u1")
        assert self.mock_agent.process_voice_command.call_args.kwargs["chain_id"] == "chain4"

    @pytest.mark.asyncio
    async def test_exception_in_sub_command_handled(self):
        """Best-effort: exceptions become failed SubCommandResults, not propagated."""
        self.mock_agent.process_voice_command.side_effect = RuntimeError("boom")
        chain = ChainedCommand(
            chain_id="chain5", original="play jazz",
            sub_commands=["play jazz"], language="en",
            timestamp="2026-03-13T00:00:00",
        )
        result = await self.executor.execute(chain, user_id="u1")
        assert result.results[0].success is False
        assert "boom" in result.results[0].error
        assert result.all_failed is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_chain_executor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement ChainExecutor**

```python
# orchestration/mcp/modules/command-chaining/chain_executor.py
"""Executes chained commands with best-effort concurrency."""

import asyncio
import json
import time
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

from .chain_parser import ChainedCommand, SubCommandResult, ChainResult

logger = logging.getLogger(__name__)


class ChainExecutor:
    """Executes sub-commands concurrently with best-effort semantics."""

    def __init__(self, voice_agent: Any, redis_client: Any = None):
        self.voice_agent = voice_agent
        self.redis = redis_client

    async def execute(
        self,
        chain: ChainedCommand,
        user_id: str,
        device_type: str = "unknown",
        context: Optional[dict] = None,
    ) -> ChainResult:
        start = time.monotonic()
        tasks = [
            self._execute_one(i, cmd, chain.chain_id, user_id, device_type, context)
            for i, cmd in enumerate(chain.sub_commands)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        sub_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                sub_results.append(SubCommandResult(
                    index=i,
                    sub_command=chain.sub_commands[i],
                    intent="unknown",
                    confidence=0.0,
                    success=False,
                    error=str(r),
                    duration_ms=0.0,
                ))
            else:
                sub_results.append(r)

        total_ms = (time.monotonic() - start) * 1000
        successes = [r for r in sub_results if r.success]
        chain_result = ChainResult(
            chain_id=chain.chain_id,
            original=chain.original,
            results=sub_results,
            total_duration_ms=total_ms,
            partial_failure=0 < len(successes) < len(sub_results),
            all_failed=len(successes) == 0,
        )

        # Publish stream:chain_completed event (spec requirement)
        if self.redis and len(chain.sub_commands) > 1:
            try:
                await self.redis.xadd("stream:chain_completed", {
                    "chain_id": chain_result.chain_id,
                    "original": chain_result.original,
                    "user_id": user_id,
                    "sub_command_count": str(len(chain_result.results)),
                    "results": json.dumps([asdict(r) for r in chain_result.results]),
                    "total_duration_ms": str(chain_result.total_duration_ms),
                    "partial_failure": str(chain_result.partial_failure),
                    "all_failed": str(chain_result.all_failed),
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.error(f"Failed to publish chain_completed: {e}")

        return chain_result

    async def _execute_one(
        self, index: int, text: str, chain_id: str,
        user_id: str, device_type: str, context: Optional[dict],
    ) -> SubCommandResult:
        start = time.monotonic()
        raw = await self.voice_agent.process_voice_command(
            voice_text=text,
            user_id=user_id,
            device_type=device_type,
            context=context,
            chain_id=chain_id,
        )
        data = json.loads(raw)
        duration = (time.monotonic() - start) * 1000
        is_success = data.get("status") == "completed"
        return SubCommandResult(
            index=index,
            sub_command=text,
            intent=data.get("intent", "unknown"),
            confidence=data.get("confidence", 0.0),
            success=is_success,
            error=data.get("error"),
            duration_ms=duration,
        )
```

Also update `__init__.py`:

```python
# orchestration/mcp/modules/command-chaining/__init__.py
from .chain_parser import ChainParser, ChainedCommand, SubCommandResult, ChainResult
from .chain_executor import ChainExecutor
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_chain_executor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/mcp/modules/command-chaining/ tests/unit/test_chain_executor.py
git commit -m "feat: add ChainExecutor with best-effort concurrent execution"
```

---

### Task 3: Modify VoiceCommandIntelligenceAgent for chain_id support

**Files:**
- Modify: `orchestration/mcp/modules/agents/voice_command_intelligence.py:210-216` (process_voice_command signature)
- Modify: `orchestration/mcp/modules/agents/voice_command_intelligence.py:662-694` (_publish_command_event)
- Modify: `orchestration/mcp/modules/agents/voice_command_intelligence.py:696-720` (_publish_failure_event)

**Important:** This file is human-written. Only add the `chain_id` parameter and propagate it. Do not refactor or change existing logic. Ask the user before making any changes beyond what is specified here.

- [ ] **Step 1: Add chain_id to process_voice_command signature (line 210)**

Change line 210-216 from:
```python
    async def process_voice_command(
        self,
        voice_text: str,
        user_id: str,
        device_type: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
```
To:
```python
    async def process_voice_command(
        self,
        voice_text: str,
        user_id: str,
        device_type: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
        chain_id: Optional[str] = None,
    ) -> str:
```

- [ ] **Step 2: Pass chain_id to analysis_metadata (both success and failure paths)**

In the `analysis_metadata` dict inside the `VoiceCommandAnalysis` construction (success path, around line 316), add:
```python
"chain_id": chain_id,
```

Also add `"chain_id": chain_id` to the `analysis_metadata` in the failure/except path (around line 350) so chain_id is present regardless of outcome.

- [ ] **Step 3: Pass chain_id and device_type to _publish_command_event and _publish_failure_event**

Update `_publish_command_event` call (around line 302) to pass `chain_id`:
```python
await self._publish_command_event(
    command_id, voice_text, user_id, intent, confidence,
    parameters, success, duration_ms, chain_id
)
```

Update `_publish_command_event` method signature (line 662) to accept `chain_id`:
```python
async def _publish_command_event(
    self, command_id, voice_text, user_id, intent, confidence,
    parameters, success, duration_ms, chain_id=None,
) -> None:
```

Add `"chain_id": chain_id` to the event dict (around line 688).

Update `_publish_failure_event` call (around line 339) to pass `chain_id` and `device_type`:
```python
await self._publish_failure_event(
    command_id, voice_text, user_id, str(e), chain_id, device_type
)
```

Update `_publish_failure_event` method signature (line 696) to accept both:
```python
async def _publish_failure_event(
    self, command_id, voice_text, user_id, error, chain_id=None, device_type="unknown",
) -> None:
```

Add `"chain_id": chain_id, "device_type": device_type` to the failure event dict (around line 712).

- [ ] **Step 4: Run existing tests to verify nothing is broken**

Run: `pytest tests/ -k "voice" -v --ignore=tests/integration`
Expected: All existing tests PASS (new param is optional with default None)

- [ ] **Step 5: Commit**

```bash
git add orchestration/mcp/modules/agents/voice_command_intelligence.py
git commit -m "feat: add chain_id propagation to VoiceCommandIntelligenceAgent"
```

---

## Chunk 2: Feature D — Automotive Voice UX Patterns

### Task 4: Voice dialog data structures and dialog registry

**Files:**
- Create: `orchestration/mcp/modules/voice-ux/__init__.py`
- Create: `orchestration/mcp/modules/voice-ux/automotive_dialogs.py`
- Create: `tests/unit/test_dialog_renderer.py`

- [ ] **Step 1: Write failing tests for dialog registry and rendering**

```python
# tests/unit/test_dialog_renderer.py
import pytest
from orchestration.mcp.modules.voice_ux.automotive_dialogs import (
    DIALOGS, CONTEXT_RULES, Priority, VoiceDialog,
)
from orchestration.mcp.modules.voice_ux.dialog_renderer import (
    DialogRenderer, RenderedDialog,
)


class TestDialogRegistry:
    def test_all_dialogs_have_en_and_cs(self):
        for dialog_id, dialog in DIALOGS.items():
            assert "en" in dialog.templates, f"{dialog_id} missing 'en' template"
            assert "cs" in dialog.templates, f"{dialog_id} missing 'cs' template"

    def test_all_dialogs_have_test_fixture(self):
        for dialog_id, dialog in DIALOGS.items():
            assert dialog.test_fixture, f"{dialog_id} missing test_fixture"
            assert "input" in dialog.test_fixture
            assert "expected_tts" in dialog.test_fixture

    def test_all_dialogs_have_valid_priority(self):
        for dialog_id, dialog in DIALOGS.items():
            assert isinstance(dialog.priority, Priority)

    def test_context_rules_format(self):
        valid_contexts = {"driving", "parked", "workshop", "road_trip"}
        valid_behaviors = {"short", "verbose", "always", "block"}
        for dialog_id, dialog in DIALOGS.items():
            for rule in dialog.context_rules:
                parts = rule.split(":")
                assert len(parts) == 2, f"Invalid rule format in {dialog_id}: {rule}"
                assert parts[0] in valid_contexts, f"Invalid context in {dialog_id}: {parts[0]}"
                assert parts[1] in valid_behaviors, f"Invalid behavior in {dialog_id}: {parts[1]}"


class TestDialogRenderer:
    def setup_method(self):
        self.renderer = DialogRenderer()

    def test_render_simple_confirmation(self):
        result = self.renderer.render(
            "confirm.play_music",
            params={"target": "jazz"},
            language="en",
            context="parked",
        )
        assert isinstance(result, RenderedDialog)
        assert result.tts_text == "Playing jazz."
        assert result.priority == Priority.NORMAL

    def test_render_czech(self):
        result = self.renderer.render(
            "confirm.play_music",
            params={"target": "jazz"},
            language="cs",
            context="parked",
        )
        assert "Přehrávám jazz" in result.tts_text

    def test_driving_context_truncation(self):
        result = self.renderer.render(
            "status.engine",
            params={"details": "a " * 50},  # 50 words
            language="en",
            context="driving",
        )
        word_count = len(result.tts_text.split())
        assert word_count <= CONTEXT_RULES["driving"]["max_response_words"]
        assert result.truncated is True

    def test_driving_context_tts_speed(self):
        result = self.renderer.render(
            "confirm.play_music",
            params={"target": "jazz"},
            language="en",
            context="driving",
        )
        assert result.tts_params.get("speed") == CONTEXT_RULES["driving"]["tts_speed"]

    def test_safety_block_in_driving(self):
        result = self.renderer.render(
            "safety.driving_blocked",
            params={"action": "send a message"},
            language="en",
            context="driving",
        )
        assert result.priority == Priority.CRITICAL
        assert "driving" in result.tts_text.lower()

    def test_unknown_dialog_id_raises(self):
        with pytest.raises(KeyError):
            self.renderer.render("nonexistent.dialog", {}, "en", "parked")

    def test_parked_context_no_truncation(self):
        result = self.renderer.render(
            "confirm.play_music",
            params={"target": "jazz"},
            language="en",
            context="parked",
        )
        assert result.truncated is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_dialog_renderer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement automotive_dialogs.py with dialog registry**

```python
# orchestration/mcp/modules/voice-ux/__init__.py
from .automotive_dialogs import DIALOGS, CONTEXT_RULES, Priority, VoiceDialog
from .dialog_renderer import DialogRenderer, RenderedDialog

# orchestration/mcp/modules/voice-ux/automotive_dialogs.py
"""Automotive voice dialog templates — bilingual, context-aware, with test fixtures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VoiceDialog:
    dialog_id: str
    category: str
    templates: Dict[str, str]
    priority: Priority
    context_rules: List[str]
    tts_params: Dict[str, Any] = field(default_factory=dict)
    test_fixture: Dict[str, Any] = field(default_factory=dict)


CONTEXT_RULES: Dict[str, Dict[str, Any]] = {
    "driving": {
        "max_response_words": 15,
        "max_clarification_turns": 1,
        "safety_blocks": ["message", "video", "browse"],
        "tts_speed": 1.1,
    },
    "parked": {
        "max_response_words": 50,
        "max_clarification_turns": 3,
        "safety_blocks": [],
        "tts_speed": 1.0,
    },
    "workshop": {
        "max_response_words": 100,
        "max_clarification_turns": 5,
        "safety_blocks": [],
        "tts_speed": 0.9,
    },
    "road_trip": {
        "max_response_words": 25,
        "max_clarification_turns": 2,
        "safety_blocks": ["message", "video", "browse"],
        "tts_speed": 1.0,
    },
}

DIALOGS: Dict[str, VoiceDialog] = {
    # --- Confirmations ---
    "confirm.play_music": VoiceDialog(
        dialog_id="confirm.play_music",
        category="confirmation",
        templates={"en": "Playing {target}.", "cs": "Přehrávám {target}."},
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"intent": "play_music", "params": {"target": "jazz"}, "lang": "en"},
            "expected_tts": "Playing jazz.",
            "expected_priority": "normal",
        },
    ),
    "confirm.stop": VoiceDialog(
        dialog_id="confirm.stop",
        category="confirmation",
        templates={"en": "Stopped.", "cs": "Zastaveno."},
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"intent": "stop", "params": {}, "lang": "en"},
            "expected_tts": "Stopped.",
            "expected_priority": "normal",
        },
    ),
    "confirm.volume": VoiceDialog(
        dialog_id="confirm.volume",
        category="confirmation",
        templates={"en": "Volume set to {level}.", "cs": "Hlasitost nastavena na {level}."},
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"intent": "volume", "params": {"level": "50%"}, "lang": "en"},
            "expected_tts": "Volume set to 50%.",
            "expected_priority": "normal",
        },
    ),
    "confirm.climate": VoiceDialog(
        dialog_id="confirm.climate",
        category="confirmation",
        templates={
            "en": "Temperature set to {temperature} degrees.",
            "cs": "Teplota nastavena na {temperature} stupňů.",
        },
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"intent": "climate", "params": {"temperature": "22"}, "lang": "en"},
            "expected_tts": "Temperature set to 22 degrees.",
            "expected_priority": "normal",
        },
    ),
    "confirm.navigation": VoiceDialog(
        dialog_id="confirm.navigation",
        category="confirmation",
        templates={
            "en": "Navigating to {destination}.",
            "cs": "Navigace do {destination}.",
        },
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"intent": "navigation", "params": {"destination": "Prague"}, "lang": "en"},
            "expected_tts": "Navigating to Prague.",
            "expected_priority": "normal",
        },
    ),
    # --- Chain results ---
    "chain.success": VoiceDialog(
        dialog_id="chain.success",
        category="chain_result",
        templates={"en": "Done. {summary}.", "cs": "Hotovo. {summary}."},
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"params": {"summary": "All commands completed"}, "lang": "en"},
            "expected_tts": "Done. All commands completed.",
            "expected_priority": "normal",
        },
    ),
    "chain.partial": VoiceDialog(
        dialog_id="chain.partial",
        category="chain_result",
        templates={
            "en": "Done. {successes}. But {failures}.",
            "cs": "Hotovo. {successes}. Ale {failures}.",
        },
        priority=Priority.HIGH,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {
                "params": {
                    "successes": "Jazz is playing",
                    "failures": "I couldn't set the temperature — HVAC offline",
                },
                "lang": "en",
            },
            "expected_tts": "Done. Jazz is playing. But I couldn't set the temperature — HVAC offline.",
            "expected_priority": "high",
        },
    ),
    "chain.failed": VoiceDialog(
        dialog_id="chain.failed",
        category="chain_result",
        templates={
            "en": "Sorry, none of that worked. {details}",
            "cs": "Omlouvám se, nic z toho nefungovalo. {details}",
        },
        priority=Priority.HIGH,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"params": {"details": "Try again later"}, "lang": "en"},
            "expected_tts": "Sorry, none of that worked. Try again later",
            "expected_priority": "high",
        },
    ),
    # --- Safety ---
    "safety.driving_blocked": VoiceDialog(
        dialog_id="safety.driving_blocked",
        category="safety_alert",
        templates={
            "en": "Can't {action} while driving.",
            "cs": "Nelze {action} za jízdy.",
        },
        priority=Priority.CRITICAL,
        context_rules=["driving:always"],
        tts_params={"speed": 1.0},
        test_fixture={
            "input": {"params": {"action": "send a message"}, "context": "driving", "lang": "en"},
            "expected_tts": "Can't send a message while driving.",
            "expected_priority": "critical",
        },
    ),
    # --- Errors ---
    "error.not_understood": VoiceDialog(
        dialog_id="error.not_understood",
        category="error",
        templates={
            "en": "I didn't understand that. Try again?",
            "cs": "Nerozuměl jsem. Zkuste to znovu?",
        },
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"intent": "unknown", "lang": "en"},
            "expected_tts": "I didn't understand that. Try again?",
            "expected_priority": "normal",
        },
    ),
    "error.command_failed": VoiceDialog(
        dialog_id="error.command_failed",
        category="error",
        templates={
            "en": "{action} failed. {reason}",
            "cs": "{action} selhalo. {reason}",
        },
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"params": {"action": "Navigation", "reason": "No GPS signal"}, "lang": "en"},
            "expected_tts": "Navigation failed. No GPS signal",
            "expected_priority": "normal",
        },
    ),
    # --- Clarification ---
    "clarify.ambiguous": VoiceDialog(
        dialog_id="clarify.ambiguous",
        category="ambiguity",
        templates={
            "en": "Did you mean {option_a} or {option_b}?",
            "cs": "Mysleli jste {option_a} nebo {option_b}?",
        },
        priority=Priority.HIGH,
        context_rules=["driving:short", "parked:verbose", "workshop:verbose"],
        test_fixture={
            "input": {"params": {"option_a": "cabin lights", "option_b": "headlights"}, "lang": "en"},
            "expected_tts": "Did you mean cabin lights or headlights?",
            "expected_priority": "high",
        },
    ),
    # --- System status ---
    "status.engine": VoiceDialog(
        dialog_id="status.engine",
        category="system_status",
        templates={
            "en": "Engine: {details}",
            "cs": "Motor: {details}",
        },
        priority=Priority.NORMAL,
        context_rules=["driving:short", "workshop:verbose", "parked:verbose"],
        test_fixture={
            "input": {"params": {"details": "92°C, oil pressure normal"}, "lang": "en"},
            "expected_tts": "Engine: 92°C, oil pressure normal",
            "expected_priority": "normal",
        },
    ),
    "status.sensors": VoiceDialog(
        dialog_id="status.sensors",
        category="system_status",
        templates={
            "en": "Sensors: {details}",
            "cs": "Senzory: {details}",
        },
        priority=Priority.NORMAL,
        context_rules=["driving:short", "workshop:verbose", "parked:verbose"],
        test_fixture={
            "input": {"params": {"details": "temperature 23°C, humidity 45%"}, "lang": "en"},
            "expected_tts": "Sensors: temperature 23°C, humidity 45%",
            "expected_priority": "normal",
        },
    ),
    # --- Notifications ---
    "notify.low_fuel": VoiceDialog(
        dialog_id="notify.low_fuel",
        category="notification",
        templates={
            "en": "Low fuel. {distance} kilometers remaining.",
            "cs": "Málo paliva. Zbývá {distance} kilometrů.",
        },
        priority=Priority.HIGH,
        context_rules=["driving:always", "parked:verbose"],
        test_fixture={
            "input": {"params": {"distance": "50"}, "lang": "en"},
            "expected_tts": "Low fuel. 50 kilometers remaining.",
            "expected_priority": "high",
        },
    ),
    "notify.system_ready": VoiceDialog(
        dialog_id="notify.system_ready",
        category="notification",
        templates={
            "en": "MIA is ready.",
            "cs": "MIA je připravena.",
        },
        priority=Priority.LOW,
        context_rules=["driving:short", "parked:verbose"],
        test_fixture={
            "input": {"params": {}, "lang": "en"},
            "expected_tts": "MIA is ready.",
            "expected_priority": "low",
        },
    ),
}
```

- [ ] **Step 4: Implement DialogRenderer**

```python
# orchestration/mcp/modules/voice-ux/dialog_renderer.py
"""Renders voice dialogs with context rules and bilingual template filling."""

from dataclasses import dataclass, field
from typing import Any, Dict
from .automotive_dialogs import DIALOGS, CONTEXT_RULES, Priority


@dataclass
class RenderedDialog:
    dialog_id: str
    tts_text: str
    display_text: str
    priority: Priority
    tts_params: Dict[str, Any]
    language: str
    context: str
    truncated: bool


class DialogRenderer:
    """Fills dialog templates, applies context rules, returns RenderedDialog."""

    def render(
        self,
        dialog_id: str,
        params: Dict[str, Any],
        language: str,
        context: str,
    ) -> RenderedDialog:
        dialog = DIALOGS[dialog_id]  # Raises KeyError if missing
        template = dialog.templates.get(language, dialog.templates.get("en", ""))

        # Fill template variables
        tts_text = template.format_map(_SafeFormatDict(params))
        display_text = tts_text

        # Apply context rules
        ctx_config = CONTEXT_RULES.get(context, CONTEXT_RULES["parked"])
        tts_params = dict(dialog.tts_params)
        tts_params["speed"] = ctx_config.get("tts_speed", 1.0)

        # Truncate if context requires short responses
        truncated = False
        applies_short = any(
            rule == f"{context}:short" for rule in dialog.context_rules
        )
        if applies_short:
            max_words = ctx_config.get("max_response_words", 50)
            words = tts_text.split()
            if len(words) > max_words:
                tts_text = " ".join(words[:max_words])
                truncated = True

        return RenderedDialog(
            dialog_id=dialog_id,
            tts_text=tts_text,
            display_text=display_text,
            priority=dialog.priority,
            tts_params=tts_params,
            language=language,
            context=context,
            truncated=truncated,
        )


class _SafeFormatDict(dict):
    """Dict subclass that returns '{key}' for missing keys instead of raising."""
    def __missing__(self, key):
        return f"{{{key}}}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_dialog_renderer.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add orchestration/mcp/modules/voice-ux/ tests/unit/test_dialog_renderer.py
git commit -m "feat: add automotive voice dialog registry with bilingual templates and context-aware renderer"
```

---

### Task 5: Integration test suite for voice dialogs

**Files:**
- Create: `tests/integration/test_voice_dialogs.py`

- [ ] **Step 1: Write integration tests auto-collected from dialog fixtures**

```python
# tests/integration/test_voice_dialogs.py
"""Auto-generated integration tests from VoiceDialog.test_fixture fields."""
import pytest
from orchestration.mcp.modules.voice_ux.automotive_dialogs import DIALOGS, CONTEXT_RULES, Priority
from orchestration.mcp.modules.voice_ux.dialog_renderer import DialogRenderer

pytestmark = pytest.mark.integration

renderer = DialogRenderer()


class TestDialogFixtures:
    """Test every dialog renders correctly using its embedded fixture."""

    @pytest.mark.parametrize("dialog_id,dialog", list(DIALOGS.items()))
    def test_fixture_renders_en(self, dialog_id, dialog):
        fixture = dialog.test_fixture
        lang = fixture["input"].get("lang", "en")
        ctx = fixture["input"].get("context", "parked")
        params = fixture["input"].get("params", {})
        result = renderer.render(dialog_id, params, lang, ctx)
        assert result.priority.value == fixture["expected_priority"]
        if params:  # Only validate expected_tts when params are provided
            assert result.tts_text == fixture["expected_tts"]

    @pytest.mark.parametrize("dialog_id,dialog", list(DIALOGS.items()))
    def test_renders_in_czech(self, dialog_id, dialog):
        params = dialog.test_fixture["input"].get("params", {})
        result = renderer.render(dialog_id, params, "cs", "parked")
        assert result.language == "cs"
        assert len(result.tts_text) > 0

    @pytest.mark.parametrize("dialog_id,dialog", list(DIALOGS.items()))
    def test_renders_in_english(self, dialog_id, dialog):
        params = dialog.test_fixture["input"].get("params", {})
        result = renderer.render(dialog_id, params, "en", "parked")
        assert result.language == "en"
        assert len(result.tts_text) > 0


class TestSafetyBlocks:
    """Test safety dialogs fire correctly in driving context."""

    def test_safety_block_critical_priority(self):
        result = renderer.render(
            "safety.driving_blocked",
            {"action": "send a message"},
            "en", "driving",
        )
        assert result.priority == Priority.CRITICAL

    @pytest.mark.parametrize("context", ["driving", "road_trip"])
    def test_safety_blocks_enforce_in_driving_contexts(self, context):
        blocked = CONTEXT_RULES[context]["safety_blocks"]
        assert "message" in blocked
        assert "video" in blocked


class TestContextRules:
    @pytest.mark.parametrize("context,max_words", [
        ("driving", 15), ("parked", 50), ("workshop", 100), ("road_trip", 25),
    ])
    def test_max_response_words(self, context, max_words):
        assert CONTEXT_RULES[context]["max_response_words"] == max_words
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/integration/test_voice_dialogs.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_voice_dialogs.py
git commit -m "test: add integration test suite for voice dialog fixtures"
```

---

## Chunk 3: Feature E — Learning Loop Wiring

### Task 6: Postgres migration and InteractionStore

**Files:**
- Create: `infra/migrations/001_voice_learning_tables.sql`
- Create: `orchestration/mcp/modules/voice-learning/interaction_store.py`
- Create: `tests/unit/test_interaction_store.py`

- [ ] **Step 1: Write migration SQL**

```sql
-- infra/migrations/001_voice_learning_tables.sql
CREATE TABLE IF NOT EXISTS interaction_log (
    id SERIAL PRIMARY KEY,
    chain_id UUID,
    command_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    raw_input TEXT NOT NULL,
    intent TEXT,
    confidence FLOAT,
    parameters JSONB DEFAULT '{}',
    success BOOLEAN NOT NULL,
    duration_ms FLOAT,
    device_type TEXT DEFAULT 'unknown',
    context JSONB DEFAULT '{}',
    language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interaction_log_created ON interaction_log (created_at);
CREATE INDEX IF NOT EXISTS idx_interaction_log_user ON interaction_log (user_id);
CREATE INDEX IF NOT EXISTS idx_interaction_log_intent ON interaction_log (intent);

CREATE TABLE IF NOT EXISTS learned_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    pattern_data JSONB NOT NULL,
    source_cycle_id UUID,
    interaction_count INT DEFAULT 0,
    accuracy_impact FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

- [ ] **Step 2: Write failing tests for InteractionStore**

```python
# tests/unit/test_interaction_store.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from orchestration.mcp.modules.voice_learning.interaction_store import (
    InteractionStore, InteractionEvent,
)


class TestInteractionEvent:
    def test_create_from_analyzed_stream(self):
        event = InteractionEvent(
            command_id="cmd1", user_id="u1", raw_input="play jazz",
            intent="play_music", confidence=0.9, parameters={"target": "jazz"},
            success=True, duration_ms=50.0, device_type="car",
            language="en", chain_id="chain1",
        )
        assert event.success is True
        assert event.chain_id == "chain1"

    def test_create_from_failed_stream(self):
        event = InteractionEvent(
            command_id="cmd2", user_id="u1", raw_input="blah",
            intent=None, confidence=None, parameters={},
            success=False, duration_ms=10.0,
        )
        assert event.success is False
        assert event.intent is None
        assert event.device_type == "unknown"


class TestInteractionStore:
    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        conn.fetchval = AsyncMock(return_value=1)
        conn.fetch = AsyncMock(return_value=[])
        return pool, conn

    @pytest.mark.asyncio
    async def test_log_interaction(self, mock_pool):
        pool, conn = mock_pool
        store = InteractionStore(pool=pool)
        event = InteractionEvent(
            command_id="cmd1", user_id="u1", raw_input="play jazz",
            intent="play_music", confidence=0.9, parameters={},
            success=True, duration_ms=50.0,
        )
        result = await store.log_interaction(event)
        assert result == 1
        conn.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = [
            {"success": True}, {"success": True}, {"success": False},
        ]
        store = InteractionStore(pool=pool)
        metrics = await store.get_metrics(window_size=3)
        assert "success_rate" in metrics
        assert "consecutive_failures" in metrics
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_interaction_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement InteractionStore**

```python
# orchestration/mcp/modules/voice-learning/interaction_store.py
"""Postgres interface for voice interaction logs and learned patterns."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class InteractionEvent:
    command_id: str
    user_id: str
    raw_input: str
    intent: Optional[str]
    confidence: Optional[float]
    parameters: Dict[str, Any]
    success: bool
    duration_ms: Optional[float]
    device_type: str = "unknown"
    context: Dict[str, Any] = field(default_factory=dict)
    language: str = "en"
    chain_id: Optional[str] = None


class InteractionStore:
    """Postgres CRUD for interaction_log and learned_patterns tables."""

    def __init__(self, pool):
        self.pool = pool

    async def log_interaction(self, event: InteractionEvent) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO interaction_log
                    (chain_id, command_id, user_id, raw_input, intent,
                     confidence, parameters, success, duration_ms,
                     device_type, context, language)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
                """,
                event.chain_id, event.command_id, event.user_id,
                event.raw_input, event.intent, event.confidence,
                json.dumps(event.parameters), event.success,
                event.duration_ms, event.device_type,
                json.dumps(event.context), event.language,
            )

    async def get_interactions(
        self,
        since: Any,  # datetime or ISO string
        until: Any,  # datetime or ISO string
        user_id: Optional[str] = None,
        intent: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        # Ensure datetime objects for asyncpg TIMESTAMPTZ compatibility
        if isinstance(since, str):
            since = datetime.fromisoformat(since)
        if isinstance(until, str):
            until = datetime.fromisoformat(until)
        query = "SELECT * FROM interaction_log WHERE created_at >= $1 AND created_at <= $2"
        params = [since, until]
        idx = 3
        if user_id:
            query += f" AND user_id = ${idx}"
            params.append(user_id)
            idx += 1
        if intent:
            query += f" AND intent = ${idx}"
            params.append(intent)
            idx += 1
        query += f" ORDER BY created_at DESC LIMIT ${idx}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def store_pattern(
        self, pattern_type: str, data: Dict, cycle_id: str,
    ) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO learned_patterns
                    (pattern_type, pattern_data, source_cycle_id, interaction_count)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                pattern_type, json.dumps(data), cycle_id,
                data.get("interaction_count", 0),
            )

    async def get_patterns(
        self, pattern_type: Optional[str] = None, limit: int = 20,
    ) -> List[Dict]:
        if pattern_type:
            query = "SELECT * FROM learned_patterns WHERE pattern_type = $1 ORDER BY created_at DESC LIMIT $2"
            params = [pattern_type, limit]
        else:
            query = "SELECT * FROM learned_patterns ORDER BY created_at DESC LIMIT $1"
            params = [limit]
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_metrics(self, window_size: int = 20) -> Dict:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT success, confidence FROM interaction_log ORDER BY created_at DESC LIMIT $1",
                window_size,
            )
            total_count = await conn.fetchval("SELECT count(*) FROM interaction_log")
        if not rows:
            return {
                "success_rate": 0.0, "avg_confidence": 0.0,
                "failure_count": 0, "consecutive_failures": 0,
                "total_interactions": 0,
            }

        successes = sum(1 for r in rows if r["success"])
        confidences = [r["confidence"] for r in rows if r["confidence"] is not None]
        consecutive = 0
        for r in rows:
            if not r["success"]:
                consecutive += 1
            else:
                break

        return {
            "success_rate": successes / len(rows),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "failure_count": len(rows) - successes,
            "consecutive_failures": consecutive,
            "total_interactions": total_count or 0,
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_interaction_store.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add infra/migrations/001_voice_learning_tables.sql orchestration/mcp/modules/voice-learning/interaction_store.py tests/unit/test_interaction_store.py
git commit -m "feat: add InteractionStore with Postgres schema and InteractionEvent dataclass"
```

---

### Task 7: LearningStreamConsumer

**Files:**
- Create: `orchestration/mcp/modules/voice-learning/stream_consumer.py`
- Create: `tests/unit/test_stream_consumer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_stream_consumer.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from orchestration.mcp.modules.voice_learning.stream_consumer import LearningStreamConsumer
from orchestration.mcp.modules.voice_learning.interaction_store import InteractionEvent


class TestStreamConsumer:
    @pytest.fixture
    def consumer(self):
        redis = AsyncMock()
        store = AsyncMock()
        trigger_manager = AsyncMock()
        return LearningStreamConsumer(
            redis_client=redis,
            interaction_store=store,
            trigger_manager=trigger_manager,
        )

    @pytest.mark.asyncio
    async def test_parse_command_analyzed_event(self, consumer):
        stream_data = {
            b"command_id": b"cmd1",
            b"voice_text": b"play jazz",
            b"user_id": b"u1",
            b"intent": b"play_music",
            b"confidence": b"0.9",
            b"parameters": b'{"target": "jazz"}',
            b"success": b"True",
            b"duration_ms": b"50.0",
            b"chain_id": b"chain1",
            b"device_type": b"car",
            b"timestamp": b"2026-03-13T00:00:00",
        }
        event = consumer._parse_event("stream:command_analyzed", stream_data)
        assert isinstance(event, InteractionEvent)
        assert event.intent == "play_music"
        assert event.chain_id == "chain1"
        assert event.success is True

    @pytest.mark.asyncio
    async def test_parse_command_failed_event(self, consumer):
        stream_data = {
            b"command_id": b"cmd2",
            b"voice_text": b"blah",
            b"user_id": b"u1",
            b"error": b"not recognized",
            b"chain_id": b"",
            b"device_type": b"unknown",
            b"timestamp": b"2026-03-13T00:00:00",
        }
        event = consumer._parse_event("stream:command_failed", stream_data)
        assert event.success is False
        assert event.intent is None

    @pytest.mark.asyncio
    async def test_process_event_writes_to_store(self, consumer):
        event = InteractionEvent(
            command_id="cmd1", user_id="u1", raw_input="play jazz",
            intent="play_music", confidence=0.9, parameters={},
            success=True, duration_ms=50.0,
        )
        await consumer._process_event(event)
        consumer.interaction_store.log_interaction.assert_called_once_with(event)
        consumer.trigger_manager.check_event_triggers.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chain_event_expands_results(self, consumer):
        data = {
            b"chain_id": b"chain1",
            b"results": json.dumps([
                {"sub_command": "play jazz", "intent": "play_music", "confidence": 0.9,
                 "success": True, "duration_ms": 50},
                {"sub_command": "set temp", "intent": "climate", "confidence": 0.8,
                 "success": False, "duration_ms": 30},
            ]).encode(),
            b"user_id": b"u1",
        }
        await consumer._process_chain_event(data)
        assert consumer.interaction_store.log_interaction.call_count == 2
        assert consumer.trigger_manager.check_event_triggers.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_stream_consumer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement LearningStreamConsumer**

```python
# orchestration/mcp/modules/voice-learning/stream_consumer.py
"""Redis Streams consumer for voice learning events."""

import asyncio
import json
import logging
from typing import Any, Optional

from .interaction_store import InteractionEvent, InteractionStore

logger = logging.getLogger(__name__)

STREAMS = [
    "stream:command_analyzed",
    "stream:command_failed",
    "stream:chain_completed",
]
GROUP_NAME = "voice-learning"
CONSUMER_NAME = "consumer-1"
RECLAIM_TIMEOUT_MS = 300_000  # 5 minutes


class LearningStreamConsumer:
    """Consumes Redis Streams events and feeds InteractionStore + triggers."""

    def __init__(
        self,
        redis_client: Any,
        interaction_store: InteractionStore,
        trigger_manager: Any,
    ):
        self.redis = redis_client
        self.interaction_store = interaction_store
        self.trigger_manager = trigger_manager
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Initialize consumer groups and start consuming."""
        for stream in STREAMS:
            try:
                await self.redis.xgroup_create(stream, GROUP_NAME, id="0", mkstream=True)
            except Exception:
                pass  # Group already exists

        # Reclaim pending entries on startup
        await self._reclaim_pending()
        logger.info(f"LearningStreamConsumer started on {STREAMS}")

        while not self._stop_event.is_set():
            try:
                entries = await self.redis.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME,
                    {s: ">" for s in STREAMS},
                    count=10, block=1000,
                )
                if not entries:
                    continue

                for stream_name, messages in entries:
                    stream_str = stream_name.decode() if isinstance(stream_name, bytes) else stream_name
                    for msg_id, data in messages:
                        try:
                            if stream_str == "stream:chain_completed":
                                await self._process_chain_event(data)
                            else:
                                event = self._parse_event(stream_str, data)
                                await self._process_event(event)
                            await self.redis.xack(stream_str, GROUP_NAME, msg_id)
                        except Exception as e:
                            logger.error(f"Failed to process {stream_str}:{msg_id}: {e}")
                            # Do not XACK — will be re-delivered

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream consumer error: {e}")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        self._stop_event.set()

    def _parse_event(self, stream: str, data: dict) -> InteractionEvent:
        def _get(key: str, default: str = "") -> str:
            val = data.get(key.encode(), data.get(key, default))
            return val.decode() if isinstance(val, bytes) else str(val)

        is_failure = stream == "stream:command_failed"

        return InteractionEvent(
            command_id=_get("command_id"),
            user_id=_get("user_id"),
            raw_input=_get("voice_text"),
            intent=None if is_failure else _get("intent"),
            confidence=None if is_failure else float(_get("confidence", "0")),
            parameters=json.loads(_get("parameters", "{}")) if not is_failure else {},
            success=not is_failure and _get("success", "False").lower() == "true",
            duration_ms=float(_get("duration_ms", "0")),
            device_type=_get("device_type", "unknown"),
            language=_get("language", "en"),
            chain_id=_get("chain_id") or None,
        )

    async def _process_chain_event(self, data: dict) -> None:
        """Process chain_completed — expand into individual InteractionEvents."""
        import uuid as _uuid

        def _get(key, default=""):
            val = data.get(key.encode(), data.get(key, default))
            return val.decode() if isinstance(val, bytes) else str(val)

        chain_id = _get("chain_id")
        user_id = _get("user_id", "unknown")
        results_json = _get("results", "[]")
        results = json.loads(results_json)

        for r in results:
            event = InteractionEvent(
                command_id=str(_uuid.uuid4()),  # Generate UUID — SubCommandResult has no command_id
                user_id=user_id,
                raw_input=r.get("sub_command", ""),
                intent=r.get("intent"),
                confidence=r.get("confidence"),
                parameters={},
                success=r.get("success", False),
                duration_ms=r.get("duration_ms", 0),
                chain_id=chain_id,
            )
            await self._process_event(event)

    async def _process_event(self, event: InteractionEvent) -> None:
        await self.interaction_store.log_interaction(event)
        await self.trigger_manager.check_event_triggers(event)

    async def _reclaim_pending(self) -> None:
        for stream in STREAMS:
            try:
                pending = await self.redis.xpending_range(
                    stream, GROUP_NAME, "-", "+", count=100,
                )
                for entry in pending:
                    idle = entry.get("time_since_delivered", 0)
                    if idle > RECLAIM_TIMEOUT_MS:
                        msg_id = entry["message_id"]
                        await self.redis.xclaim(
                            stream, GROUP_NAME, CONSUMER_NAME, RECLAIM_TIMEOUT_MS, [msg_id],
                        )
                        logger.info(f"Reclaimed pending message {msg_id} from {stream}")
            except Exception as e:
                logger.warning(f"Could not reclaim pending for {stream}: {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_stream_consumer.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/mcp/modules/voice-learning/stream_consumer.py tests/unit/test_stream_consumer.py
git commit -m "feat: add LearningStreamConsumer with Redis Streams consumer group and XACK strategy"
```

---

### Task 8: LearningTriggerManager

**Files:**
- Create: `orchestration/mcp/modules/voice-learning/trigger_manager.py`
- Create: `tests/unit/test_trigger_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_trigger_manager.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from orchestration.mcp.modules.voice_learning.trigger_manager import LearningTriggerManager
from orchestration.mcp.modules.voice_learning.interaction_store import InteractionEvent


class TestLearningTriggerManager:
    @pytest.fixture
    def manager(self):
        store = AsyncMock()
        learning_server = AsyncMock()
        store.get_metrics.return_value = {
            "success_rate": 0.9, "avg_confidence": 0.8,
            "failure_count": 2, "consecutive_failures": 0,
        }
        store.get_interactions.return_value = []
        learning_server.run_learning_cycle.return_value = {
            "timestamp": "2026-03-13T00:00:00",
            "interaction_count": 10,
            "stored_patterns": 2,
            "errors": [],
        }
        return LearningTriggerManager(
            interaction_store=store,
            learning_server=learning_server,
            consecutive_failure_threshold=3,
            success_rate_threshold=0.80,
            interaction_count_threshold=100,
        )

    @pytest.mark.asyncio
    async def test_no_trigger_on_success(self, manager):
        event = InteractionEvent(
            command_id="cmd1", user_id="u1", raw_input="play jazz",
            intent="play_music", confidence=0.9, parameters={},
            success=True, duration_ms=50.0,
        )
        await manager.check_event_triggers(event)
        manager.learning_server.run_learning_cycle.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_on_consecutive_failures(self, manager):
        manager.interaction_store.get_metrics.return_value = {
            "success_rate": 0.7, "avg_confidence": 0.3,
            "failure_count": 5, "consecutive_failures": 3,
        }
        event = InteractionEvent(
            command_id="cmd1", user_id="u1", raw_input="blah",
            intent=None, confidence=None, parameters={},
            success=False, duration_ms=10.0,
        )
        await manager.check_event_triggers(event)
        manager.learning_server.run_learning_cycle.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_on_low_success_rate(self, manager):
        manager.interaction_store.get_metrics.return_value = {
            "success_rate": 0.75, "avg_confidence": 0.5,
            "failure_count": 5, "consecutive_failures": 1,
        }
        event = InteractionEvent(
            command_id="cmd1", user_id="u1", raw_input="blah",
            intent=None, confidence=None, parameters={},
            success=False, duration_ms=10.0,
        )
        await manager.check_event_triggers(event)
        manager.learning_server.run_learning_cycle.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_trigger(self, manager):
        result = await manager.trigger_manual_cycle()
        assert "cycle_id" in result
        manager.learning_server.run_learning_cycle.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_resets_consecutive_counter(self, manager):
        manager._consecutive_failures = 2
        event = InteractionEvent(
            command_id="cmd1", user_id="u1", raw_input="play jazz",
            intent="play_music", confidence=0.9, parameters={},
            success=True, duration_ms=50.0,
        )
        await manager.check_event_triggers(event)
        assert manager._consecutive_failures == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_trigger_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement LearningTriggerManager**

```python
# orchestration/mcp/modules/voice-learning/trigger_manager.py
"""Manages scheduled, event-driven, and manual learning cycle triggers."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .interaction_store import InteractionEvent, InteractionStore

logger = logging.getLogger(__name__)


class LearningTriggerManager:
    """Triggers learning cycles based on schedule, events, or manual request."""

    def __init__(
        self,
        interaction_store: InteractionStore,
        learning_server: Any,
        redis_client: Any = None,
        consecutive_failure_threshold: int = 3,
        success_rate_threshold: float = 0.80,
        interaction_count_threshold: int = 100,
        scheduled_interval_hours: int = 24,
    ):
        self.interaction_store = interaction_store
        self.learning_server = learning_server
        self.redis = redis_client
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.success_rate_threshold = success_rate_threshold
        self.interaction_count_threshold = interaction_count_threshold
        self.scheduled_interval = timedelta(hours=scheduled_interval_hours)

        self._consecutive_failures = 0
        self._interaction_count_since_cycle = 0
        self._last_cycle_time = datetime.now()
        self._running = False

    async def check_event_triggers(self, event: InteractionEvent) -> None:
        """Check if event-driven trigger conditions are met."""
        self._interaction_count_since_cycle += 1

        if event.success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

        # Check thresholds
        should_trigger = False

        if self._consecutive_failures >= self.consecutive_failure_threshold:
            logger.info(f"Event trigger: {self._consecutive_failures} consecutive failures")
            should_trigger = True

        metrics = await self.interaction_store.get_metrics(window_size=20)
        if metrics["success_rate"] < self.success_rate_threshold:
            logger.info(f"Event trigger: success_rate {metrics['success_rate']:.2f} < {self.success_rate_threshold}")
            should_trigger = True

        if should_trigger:
            await self._run_cycle(trigger="event-driven")

    async def start_scheduled(self) -> None:
        """Start the scheduled trigger loop."""
        self._running = True
        while self._running:
            await asyncio.sleep(60)  # Check every minute
            now = datetime.now()
            time_trigger = (now - self._last_cycle_time) >= self.scheduled_interval
            count_trigger = self._interaction_count_since_cycle >= self.interaction_count_threshold

            if time_trigger or count_trigger:
                reason = "time" if time_trigger else "count"
                logger.info(f"Scheduled trigger: {reason}")
                await self._run_cycle(trigger=f"scheduled-{reason}")

    async def stop_scheduled(self) -> None:
        self._running = False

    async def trigger_manual_cycle(
        self,
        user_id: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger a manual learning cycle with optional filters."""
        return await self._run_cycle(
            trigger="manual",
            user_id=user_id,
            since=since,
            until=until,
            intent=intent,
        )

    async def _run_cycle(
        self,
        trigger: str,
        user_id: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        cycle_id = str(uuid.uuid4())
        since = since or self._last_cycle_time.isoformat()
        until = until or datetime.now().isoformat()

        logger.info(f"Running learning cycle {cycle_id} (trigger: {trigger})")

        interactions = await self.interaction_store.get_interactions(
            since=since, until=until, user_id=user_id, intent=intent,
        )

        if not interactions:
            logger.info("No interactions to process")
            return {"cycle_id": cycle_id, "status": "empty", "interaction_count": 0}

        results = await self.learning_server.run_learning_cycle(
            interactions=interactions, user_id=user_id,
        )

        # Store patterns
        if results.get("pattern_results"):
            await self.interaction_store.store_pattern(
                "synthesis", results["pattern_results"], cycle_id,
            )
        if results.get("context_results"):
            await self.interaction_store.store_pattern(
                "context", results["context_results"], cycle_id,
            )
        if results.get("synthesis_results"):
            await self.interaction_store.store_pattern(
                "knowledge", results["synthesis_results"], cycle_id,
            )

        # Push high-confidence patterns to mcp-prompts (self-improvement loop)
        for ptype in ["pattern_results", "context_results", "synthesis_results"]:
            if results.get(ptype):
                try:
                    from orchestration.mcp.modules.shared.mcp_framework import create_prompt
                    await create_prompt(
                        name=f"voice-learned-{ptype.replace('_results', '')}-{cycle_id[:8]}",
                        description=f"Learned {ptype} from cycle {cycle_id}",
                        content=json.dumps(results[ptype]),
                        tags=["mia", "voice-command", "learned", ptype.replace("_results", "")],
                    )
                except Exception as e:
                    logger.warning(f"Could not push pattern to mcp-prompts: {e}")

        # Publish completion event
        if self.redis:
            try:
                await self.redis.xadd("stream:learning_cycle_completed", {
                    "cycle_id": cycle_id,
                    "trigger": trigger,
                    "interaction_count": str(len(interactions)),
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.error(f"Failed to publish cycle completion: {e}")

        # Reset counters
        self._last_cycle_time = datetime.now()
        self._interaction_count_since_cycle = 0
        self._consecutive_failures = 0

        return {
            "cycle_id": cycle_id,
            "status": "completed",
            "interaction_count": len(interactions),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_trigger_manager.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/mcp/modules/voice-learning/trigger_manager.py tests/unit/test_trigger_manager.py
git commit -m "feat: add LearningTriggerManager with scheduled, event-driven, and manual triggers"
```

---

### Task 9: FastAPI endpoint wiring (/api/voice + /api/learning/*)

**Files:**
- Modify: `apps/rpi-backend/py-api/api/main.py` — add new endpoints and lifespan hooks

**Important:** This file is human-written. Only add new endpoints and lifespan hooks. Do not modify existing endpoints or logic. Ask the user before changing existing code.

- [ ] **Step 1: Write failing integration test for /api/voice endpoint**

```python
# tests/integration/test_learning_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
class TestVoiceEndpoint:
    """Tests for /api/voice endpoint — requires running FastAPI test client."""

    @pytest.mark.asyncio
    async def test_voice_text_endpoint_exists(self):
        """Verify the /api/voice endpoint is registered."""
        # Import via sys.path — hyphenated dirs aren't valid Python identifiers
        import sys, importlib
        sys.path.insert(0, "apps/rpi-backend/py-api")
        app = importlib.import_module("api.main").app
        routes = [r.path for r in app.routes]
        assert "/api/voice" in routes

    @pytest.mark.asyncio
    async def test_learning_cycle_endpoint_exists(self):
        import sys, importlib
        sys.path.insert(0, "apps/rpi-backend/py-api")
        app = importlib.import_module("api.main").app
        routes = [r.path for r in app.routes]
        assert "/api/learning/cycle" in routes

    @pytest.mark.asyncio
    async def test_learning_status_endpoint_exists(self):
        import sys, importlib
        sys.path.insert(0, "apps/rpi-backend/py-api")
        app = importlib.import_module("api.main").app
        routes = [r.path for r in app.routes]
        assert "/api/learning/status" in routes

    @pytest.mark.asyncio
    async def test_learning_patterns_endpoint_exists(self):
        import sys, importlib
        sys.path.insert(0, "apps/rpi-backend/py-api")
        app = importlib.import_module("api.main").app
        routes = [r.path for r in app.routes]
        assert "/api/learning/patterns" in routes
```

- [ ] **Step 2: Add endpoints to main.py**

Add to `apps/rpi-backend/py-api/api/main.py`. First, add the lifespan hook (modify the existing lifespan or add a new one if none exists):

```python
# --- Learning System Lifespan ---
import asyncio
import asyncpg
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from orchestration.mcp.modules.voice_learning.interaction_store import InteractionStore
from orchestration.mcp.modules.voice_learning.stream_consumer import LearningStreamConsumer
from orchestration.mcp.modules.voice_learning.trigger_manager import LearningTriggerManager

# Add to existing lifespan or wrap existing one:
_consumer_task = None
_scheduler_task = None

async def _start_learning_system(app):
    """Initialize learning subsystem — call from existing lifespan startup."""
    global _consumer_task, _scheduler_task
    pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL", "postgresql://mia:mia@localhost/mia"))
    redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    store = InteractionStore(pool=pool)
    # Import and create VoiceLearningServer (existing module)
    from orchestration.mcp.modules.voice_learning.voice_learning_server import VoiceLearningServer
    learning_server = VoiceLearningServer()
    await learning_server.initialize()
    trigger = LearningTriggerManager(interaction_store=store, learning_server=learning_server, redis_client=redis)
    consumer = LearningStreamConsumer(redis_client=redis, interaction_store=store, trigger_manager=trigger)
    app.state.interaction_store = store
    app.state.trigger_manager = trigger
    app.state.learning_consumer = consumer
    app.state.pg_pool = pool
    app.state.redis = redis
    _consumer_task = asyncio.create_task(consumer.start())
    _scheduler_task = asyncio.create_task(trigger.start_scheduled())

async def _stop_learning_system(app):
    """Shutdown learning subsystem — call from existing lifespan shutdown."""
    if hasattr(app.state, "learning_consumer"):
        await app.state.learning_consumer.stop()
    if hasattr(app.state, "trigger_manager"):
        await app.state.trigger_manager.stop_scheduled()
    if _consumer_task:
        _consumer_task.cancel()
    if _scheduler_task:
        _scheduler_task.cancel()
    if hasattr(app.state, "pg_pool"):
        await app.state.pg_pool.close()
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
```

Then append the endpoints after existing endpoints:

```python
# --- Voice Command Chaining Endpoint ---

class VoiceCommandRequest(BaseModel):
    text: str
    user_id: str
    device_type: str = "unknown"
    language: str = "en"

@app.post("/api/voice")
async def process_voice_command(request: VoiceCommandRequest):
    """Process voice command with chain parsing support."""
    from orchestration.mcp.modules.command_chaining.chain_parser import ChainParser
    from orchestration.mcp.modules.command_chaining.chain_executor import ChainExecutor
    from orchestration.mcp.modules.voice_ux.dialog_renderer import DialogRenderer

    # Use app.state for agent (initialized once at startup) and redis
    agent = app.state.voice_agent if hasattr(app.state, "voice_agent") else None
    if not agent:
        from orchestration.mcp.modules.agents.voice_command_intelligence import VoiceCommandIntelligenceAgent
        agent = VoiceCommandIntelligenceAgent()
        app.state.voice_agent = agent

    redis = app.state.redis if hasattr(app.state, "redis") else None
    parser = ChainParser()
    executor = ChainExecutor(voice_agent=agent, redis_client=redis)
    renderer = DialogRenderer()

    chain = parser.parse(request.text, user_id=request.user_id, language=request.language)
    context = request.context if hasattr(request, "context") else "parked"
    result = await executor.execute(chain, user_id=request.user_id, device_type=request.device_type)

    # Select dialog and build params based on result
    params = {}
    if result.all_failed:
        dialog_id = "chain.failed"
        errors = [r.error or "unknown" for r in result.results if not r.success]
        params = {"details": "; ".join(errors)}
    elif result.partial_failure:
        dialog_id = "chain.partial"
        params = {
            "successes": ", ".join(r.intent for r in result.results if r.success),
            "failures": ", ".join(f"{r.intent}: {r.error}" for r in result.results if not r.success),
        }
    elif len(result.results) > 1:
        dialog_id = "chain.success"
        params = {"summary": "All commands completed"}
    else:
        # Single command — select confirm dialog by intent
        r = result.results[0] if result.results else None
        intent = r.intent if r else "unknown"
        dialog_id = f"confirm.{intent}"

    try:
        rendered = renderer.render(dialog_id, params, request.language, context)
        response_text = rendered.tts_text
    except KeyError:
        response_text = "Command processed."

    return {
        "chain_id": result.chain_id,
        "results": [
            {
                "sub_command": r.sub_command,
                "intent": r.intent,
                "success": r.success,
                "error": r.error,
            }
            for r in result.results
        ],
        "partial_failure": result.partial_failure,
        "all_failed": result.all_failed,
        "response_text": response_text,
        "total_duration_ms": result.total_duration_ms,
    }


# --- Learning Endpoints ---

class LearningCycleRequest(BaseModel):
    user_id: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    intent: Optional[str] = None

@app.post("/api/learning/cycle")
async def trigger_learning_cycle(request: LearningCycleRequest):
    """Trigger a manual voice learning cycle."""
    # LearningTriggerManager will be initialized in lifespan
    trigger_manager = app.state.trigger_manager if hasattr(app.state, "trigger_manager") else None
    if not trigger_manager:
        raise HTTPException(status_code=503, detail="Learning system not initialized")
    result = await trigger_manager.trigger_manual_cycle(
        user_id=request.user_id, since=request.since,
        until=request.until, intent=request.intent,
    )
    return result

@app.get("/api/learning/status")
async def get_learning_status():
    """Get current voice learning metrics."""
    store = app.state.interaction_store if hasattr(app.state, "interaction_store") else None
    trigger = app.state.trigger_manager if hasattr(app.state, "trigger_manager") else None
    if not store or not trigger:
        raise HTTPException(status_code=503, detail="Learning system not initialized")
    metrics = await store.get_metrics()
    return {
        "success_rate": metrics["success_rate"],
        "avg_confidence": metrics["avg_confidence"],
        "total_interactions": metrics["total_interactions"],
        "last_cycle": trigger._last_cycle_time.isoformat(),
        "next_scheduled": (trigger._last_cycle_time + trigger.scheduled_interval).isoformat(),
    }

@app.get("/api/learning/patterns")
async def get_learning_patterns(type: Optional[str] = None, limit: int = 20):
    """List discovered voice command patterns."""
    store = app.state.interaction_store if hasattr(app.state, "interaction_store") else None
    if not store:
        raise HTTPException(status_code=503, detail="Learning system not initialized")
    patterns = await store.get_patterns(pattern_type=type, limit=limit)
    return {"patterns": patterns}
```

- [ ] **Step 3: Run integration tests**

Run: `pytest tests/integration/test_learning_pipeline.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add apps/rpi-backend/py-api/api/main.py tests/integration/test_learning_pipeline.py
git commit -m "feat: add /api/voice and /api/learning/* endpoints to FastAPI"
```

---

### Task 10: Update VoiceLearningServer return value

**Files:**
- Modify: `orchestration/mcp/modules/voice-learning/voice_learning_server.py:316-318`

**Important:** This file is human-written. Only add `cycle_id` to the return dict. Do not change existing logic.

- [ ] **Step 1: Add cycle_id to run_learning_cycle results dict**

In `voice_learning_server.py` line 316, add `"cycle_id"` to the results dict:

```python
results = {
    "cycle_id": str(uuid.uuid4()),  # NEW — add this line
    "timestamp": datetime.now().isoformat(),
    "interaction_count": len(interactions),
```

Also add `import uuid` at the top if not already present.

- [ ] **Step 2: Run existing tests to verify nothing is broken**

Run: `pytest tests/ -k "voice_learning" -v --ignore=tests/integration`
Expected: All existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add orchestration/mcp/modules/voice-learning/voice_learning_server.py
git commit -m "feat: add cycle_id to VoiceLearningServer.run_learning_cycle return value"
```
