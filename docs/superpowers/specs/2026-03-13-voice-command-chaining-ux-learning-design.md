# Voice Command Chaining, Automotive UX, and Learning Loop

**Date:** 2026-03-13
**Status:** Reviewed
**Scope:** Features C (command chaining), D (automotive voice UX patterns), E (learning loop wiring)

## Context

MIA has a mature voice command pipeline: STT (Whisper/ElevenLabs) -> intent extraction (VoiceCommandIntelligenceAgent) -> execution -> event publishing. Three gaps remain: compound commands aren't supported, voice dialogs lack structured UX patterns, and the learning infrastructure (VoiceLearningServer, 5 MCP tools) isn't connected to real data.

### Constraints

- **Triggers:** HTTP REST, buttons, LAN API calls (no wake word)
- **Entry points:** Android sends transcribed text; other clients may send raw audio. Parser sits post-STT.
- **Languages:** English and Czech
- **Chain failures:** Best-effort (independent execution, report per-command results)
- **Driving contexts:** Commute, road trip, workshop, parked — all supported
- **Testability:** Every dialog and notification designed with integration test fixtures
- **Data pipeline:** Redis Streams (real-time) + PostgreSQL (batch), 3-tier storage
- **Learning triggers:** Scheduled, event-driven, and manual REST

## Architecture

```
Client (Android text / other audio)
  |
  v
FastAPI /api/voice (NEW endpoint)
  |
  v
STT (if audio)
  |
  v
ChainParser.parse()  ← NEW
  |
  v
[SubCmd₁, SubCmd₂, ...]
  |
  v (parallel best-effort)
VoiceCommandIntelligenceAgent.process_voice_command() (existing)
  |
  v
ChainResult aggregation  ← NEW
  |
  v
VoiceDialog template selection  ← NEW
  |
  v
TTS response + Android display
  |
  v (side effect)
Redis Streams: stream:command_analyzed, stream:command_failed
  |
  v
LearningStreamConsumer  ← NEW
  |
  v
InteractionStore (Postgres)  ← NEW
  |
  v (triggered)
VoiceLearningServer.run_learning_cycle() (existing)
  |
  v
learned_patterns table + mcp-prompts feedback
```

## Feature C: Command Chain Parser

### Module

`orchestration/mcp/modules/command-chaining/chain_parser.py`

### Data Structures

```python
@dataclass
class ChainedCommand:
    chain_id: str           # UUID
    original: str           # Full original text
    sub_commands: List[str] # Split commands
    language: str           # Detected language ("en" or "cs")
    timestamp: str          # ISO 8601

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
    partial_failure: bool   # True if any sub-command failed
    all_failed: bool        # True if every sub-command failed
```

### Splitting Logic

Connector words per locale:

```python
CONNECTORS = {
    "en": ["and", "then", "also", "plus"],
    "cs": ["a", "potom", "pak", "také"],
}
```

Splitting rules:
1. Tokenize on connector words (case-insensitive, word-boundary matching)
2. Protect quoted strings — `"rock and roll"` is not split
3. Protect known multi-word entities — music genres, place names (via a skip-list)
4. Single commands pass through as chains of length 1 (zero overhead path)
5. Language detection: try Czech connectors first if input contains Czech characters (diacritics), otherwise English

### chain_id Propagation

`process_voice_command()` gains an optional keyword argument `chain_id: Optional[str] = None`. When present, it is:
1. Included in the `analysis_metadata` of the `VoiceCommandAnalysis` response
2. Published in `_publish_command_event()` and `_publish_failure_event()` payloads as a top-level field
3. Used by `LearningStreamConsumer` to correlate sub-commands to their parent chain

Updated signature:
```python
async def process_voice_command(
    self,
    voice_text: str,
    user_id: str,
    device_type: str = "unknown",
    context: Optional[Dict[str, Any]] = None,
    chain_id: Optional[str] = None,  # NEW
) -> str:
```

### Execution

Each sub-command is dispatched independently to `VoiceCommandIntelligenceAgent.process_voice_command()` with the parent `chain_id`. Execution is concurrent (asyncio.gather with return_exceptions=True). Results are collected into `ChainResult`.

### Integration

New endpoint: `POST /api/voice` is added to `apps/rpi-backend/py-api/api/main.py` (this endpoint does not currently exist). It accepts `{"text": str, "user_id": str, "device_type": str, "language": str}` for pre-transcribed text, or raw audio bytes with content-type `audio/*` for STT processing. All requests go through `ChainParser.parse()` before intent processing. Single commands are chains of length 1.

### Chain Event Publishing

Each chain publishes a single `stream:chain_completed` event to Redis, in addition to per-command events from the existing agent. The event payload is a flat JSON object:

```python
{
    "chain_id": str,          # UUID
    "original": str,          # Full original text
    "sub_command_count": int,  # Number of sub-commands
    "results": str,           # JSON-serialized List[SubCommandResult]
    "total_duration_ms": float,
    "partial_failure": bool,
    "all_failed": bool,
    "timestamp": str,         # ISO 8601
}
```

Note: `results` is JSON-serialized because Redis Streams require flat key-value pairs. The consumer deserializes it with `json.loads()`.

## Feature D: Automotive Voice UX Patterns

### Module

`orchestration/mcp/modules/voice-ux/automotive_dialogs.py`

### Dialog Structure

```python
class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class VoiceDialog:
    dialog_id: str
    category: str
    templates: Dict[str, str]  # {"en": "...", "cs": "..."}
    priority: Priority
    context_rules: List[str]
    tts_params: Dict[str, Any]  # speed, pitch overrides per context
    test_fixture: Dict[str, Any]
```

### Dialog Categories

| Category | dialog_id prefix | Priority | Description |
|----------|-----------------|----------|-------------|
| Confirmation | `confirm.*` | NORMAL | Single command success |
| Chain result | `chain.success` | NORMAL | All sub-commands succeeded |
| Partial failure | `chain.partial` | HIGH | Some sub-commands failed |
| Total failure | `chain.failed` | HIGH | All sub-commands failed |
| Safety alert | `safety.*` | CRITICAL | Blocked action while driving |
| Ambiguity | `clarify.*` | HIGH | Disambiguation needed |
| System status | `status.*` | NORMAL | OBD-II, sensor, system info |
| Error | `error.*` | NORMAL | Unrecognized or failed command |
| Notification | `notify.*` | varies | Alerts, reminders, system events |

### Context Adaptation Rules

```python
CONTEXT_RULES = {
    "driving": {
        "max_response_words": 15,
        "max_clarification_turns": 1,
        "safety_blocks": ["message", "video", "browse"],
        "tts_speed": 1.1,  # Slightly faster
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
        "tts_speed": 0.9,  # Slower for technical info
    },
    "road_trip": {
        "max_response_words": 25,
        "max_clarification_turns": 2,
        "safety_blocks": ["message", "video", "browse"],  # Only enforced for driver, not passengers
        "tts_speed": 1.0,
    },
}
```

### Bilingual Templates

Every dialog has `en` and `cs` variants. Examples:

```python
DIALOGS = {
    "confirm.play_music": VoiceDialog(
        dialog_id="confirm.play_music",
        category="confirmation",
        templates={
            "en": "Playing {target}.",
            "cs": "Přehrávám {target}.",
        },
        priority=Priority.NORMAL,
        context_rules=["driving:short", "parked:verbose"],
        tts_params={},
        test_fixture={
            "input": {"intent": "play_music", "params": {"target": "jazz"}, "lang": "en"},
            "expected_tts": "Playing jazz.",
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
        context_rules=["driving:short"],
        tts_params={},
        test_fixture={
            "input": {
                "chain_result": {
                    "results": [
                        {"intent": "play_music", "success": True},
                        {"intent": "climate", "success": False, "error": "HVAC offline"},
                    ]
                },
                "lang": "en",
            },
            "expected_tts": "Done. Jazz is playing. But I couldn't set the temperature — HVAC offline.",
            "expected_priority": "high",
        },
    ),
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
            "input": {"intent": "message", "context": "driving", "lang": "en"},
            "expected_tts": "Can't send a message while driving.",
            "expected_priority": "critical",
        },
    ),
}
```

### RenderedDialog

```python
@dataclass
class RenderedDialog:
    dialog_id: str
    tts_text: str           # Text to speak via TTS
    display_text: str       # Text to show on Android (may differ from tts_text)
    priority: Priority
    tts_params: Dict[str, Any]  # {"speed": 1.1, "pitch": 1.0, ...}
    language: str
    context: str            # Which context was applied
    truncated: bool         # True if response was shortened by context rules
```

### Context Rule Format

`context_rules` entries follow the format `"{context}:{behavior}"` where:
- `context` is one of: `driving`, `parked`, `workshop`, `road_trip`
- `behavior` is one of: `short` (apply max_response_words), `verbose` (allow full response), `always` (always apply this dialog regardless of context), `block` (prevent this dialog in this context)

Examples: `"driving:short"`, `"parked:verbose"`, `"driving:always"`, `"workshop:verbose"`

### Dialog Renderer

```python
class DialogRenderer:
    def render(self, dialog_id: str, params: Dict, language: str, context: str) -> RenderedDialog
```

Takes a dialog ID, fills template variables, applies context rules (word limit, speed), returns a `RenderedDialog`.

### Integration Test Suite

`tests/integration/test_voice_dialogs.py` — auto-generated from test fixtures embedded in each `VoiceDialog`. Tests:
1. Every dialog renders in both languages without template errors
2. Context rules produce correct word-count limits
3. Priority levels are correct
4. Safety blocks fire in driving context
5. Chain result dialogs correctly aggregate sub-command results

## Feature E: Learning Loop Wiring

### New Components

| Component | Path | Purpose |
|-----------|------|---------|
| `LearningStreamConsumer` | `orchestration/mcp/modules/voice-learning/stream_consumer.py` | Redis Streams consumer group |
| `InteractionStore` | `orchestration/mcp/modules/voice-learning/interaction_store.py` | Postgres CRUD for interactions + patterns |
| `LearningTriggerManager` | `orchestration/mcp/modules/voice-learning/trigger_manager.py` | Scheduled, event-driven, manual triggers |

### LearningStreamConsumer

Joins Redis consumer group `"voice-learning"` on streams:
- `stream:command_analyzed` — successful commands
- `stream:command_failed` — failed commands
- `stream:chain_completed` — chain-level results (new from Feature C)

**Lifecycle:** Runs as a long-lived asyncio task started by the FastAPI `lifespan` handler (same process as the API). Graceful shutdown via `asyncio.Event`. If it crashes, the FastAPI process supervisor (systemd) restarts the whole service.

**Redis acknowledgment strategy:**
- Uses `XREADGROUP` with `GROUP voice-learning consumer-1`
- On successful processing (Postgres write + learning call): `XACK`
- On transient failure (Postgres timeout, Redis error): do NOT ack — message stays in pending list and is re-delivered on next `XREADGROUP` call
- Pending entries older than 5 minutes are reclaimed via `XCLAIM` on startup
- No dead-letter queue — all events are retried until processed (at-least-once delivery)

For each event:
1. Write to Postgres `interaction_log` via `InteractionStore`
2. Call `mia_analyze_command_learning` for real-time learning signal
3. Update sliding window metrics (success rate as boolean success count / window size)
4. Check event-driven trigger conditions
5. `XACK` on success

### InteractionStore

Postgres interface with two tables:

```sql
CREATE TABLE interaction_log (
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

CREATE INDEX idx_interaction_log_created ON interaction_log (created_at);
CREATE INDEX idx_interaction_log_user ON interaction_log (user_id);
CREATE INDEX idx_interaction_log_intent ON interaction_log (intent);

CREATE TABLE learned_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    pattern_data JSONB NOT NULL,
    source_cycle_id UUID,
    interaction_count INT DEFAULT 0,
    accuracy_impact FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**InteractionEvent dataclass** (typed input for `log_interaction`):

```python
@dataclass
class InteractionEvent:
    command_id: str          # From stream event
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
    chain_id: Optional[str] = None  # Present for chained commands
```

**Field mapping from Redis stream payloads:**
- `stream:command_analyzed` → all fields present, map directly
- `stream:command_failed` → `intent=None`, `confidence=None`, `success=False`. Note: `_publish_failure_event()` must be updated to include `device_type` and `chain_id` in its payload (currently missing from the existing code)
- `stream:chain_completed` → one `InteractionEvent` per sub-command in `results`, all sharing the same `chain_id`

Methods:
- `log_interaction(event: InteractionEvent) -> int`
- `get_interactions(since: str, until: str, user_id: Optional[str], intent: Optional[str], limit: int = 100) -> List[Dict]`
- `store_pattern(pattern_type: str, data: Dict, cycle_id: str) -> int`
- `get_patterns(pattern_type: Optional[str], limit: int = 20) -> List[Dict]`
- `get_metrics(window_size: int = 20) -> Dict` — returns `{success_rate: float, avg_confidence: float, failure_count: int, consecutive_failures: int}`

### LearningTriggerManager

Three trigger types running concurrently:

| Trigger | Condition | Action |
|---------|-----------|--------|
| Scheduled | Every 24h OR every 100 interactions (whichever first) | Full `run_learning_cycle()` on batch from `InteractionStore` |
| Event-driven | 3 consecutive global failures (chain sub-commands count individually) OR success_rate < 0.80 in sliding window of 20 | Immediate `mia_analyze_failure` + `mia_synthesize_patterns` |
| Manual | `POST /api/learning/cycle` with optional `{user_id, since, until, intent}` | Full cycle with filters |

**Clarifications:**
- "Consecutive failures" = global counter (not per-user), reset on any success. Each chain sub-command failure increments independently.
- "success_rate < 0.80" = `InteractionStore.get_metrics(window_size=20).success_rate` (boolean success count / 20)
- `interaction_count` in the POST response = number of interactions actually processed in this cycle (bounded by batch)

**Wiring:** `LearningTriggerManager` holds an `InteractionStore` reference. When a trigger fires:
1. `LearningTriggerManager` queries `InteractionStore.get_interactions(since=last_cycle_time)` to build the interaction list
2. Passes the list to `VoiceLearningServer.run_learning_cycle(interactions=interaction_list)`
3. `VoiceLearningServer` does NOT gain a direct `InteractionStore` dependency — it remains a pure processor

After each cycle:
1. `LearningTriggerManager` stores results via `InteractionStore.store_pattern()`
2. Push successful patterns to mcp-prompts via `create_prompt()`
3. Publish `stream:learning_cycle_completed` event

### REST Endpoints

Added to existing FastAPI app in `apps/rpi-backend/py-api/api/main.py`:

- `POST /api/learning/cycle` — trigger manual learning cycle
  - Body: `{user_id?: string, since?: string, until?: string, intent?: string}`
  - Returns: `{cycle_id, status, interaction_count}`
- `GET /api/learning/status` — current metrics
  - Returns: `{success_rate, avg_confidence, total_interactions, last_cycle, next_scheduled}`
- `GET /api/learning/patterns` — list discovered patterns
  - Query: `?type=&limit=20`
  - Returns: `{patterns: [{pattern_type, pattern_data, created_at, accuracy_impact}]}`

### Self-Improvement Loop Closure

After each learning cycle, `LearningTriggerManager` calls `create_prompt()` to store high-confidence patterns in mcp-prompts. These prompts are tagged `["mia", "voice-command", "learned", pattern_type]` and become available for future `VoiceCommandIntelligenceAgent` sessions to query, closing the loop:

```
commands → events → learning → patterns → mcp-prompts → improved interpretation → commands
```

## File Inventory

New files:
- `orchestration/mcp/modules/command-chaining/__init__.py`
- `orchestration/mcp/modules/command-chaining/chain_parser.py`
- `orchestration/mcp/modules/voice-ux/__init__.py`
- `orchestration/mcp/modules/voice-ux/automotive_dialogs.py`
- `orchestration/mcp/modules/voice-ux/dialog_renderer.py`
- `orchestration/mcp/modules/voice-learning/stream_consumer.py`
- `orchestration/mcp/modules/voice-learning/interaction_store.py`
- `orchestration/mcp/modules/voice-learning/trigger_manager.py`
- `tests/unit/test_chain_parser.py` — pure logic, no I/O
- `tests/unit/test_dialog_renderer.py` — template filling, no I/O
- `tests/integration/test_voice_dialogs.py` — full dialog pipeline with context
- `tests/integration/test_learning_pipeline.py` — Redis + Postgres integration
- `infra/migrations/001_voice_learning_tables.sql` — both tables in single migration

**Migration runner:** Applied via the existing `infra/docker/containers/postgres/init.sql` pattern. The migration SQL file is sourced by the Postgres container on first boot. For existing deployments, apply manually with `psql -f infra/migrations/001_voice_learning_tables.sql`.

Modified files:
- `apps/rpi-backend/py-api/api/main.py` — add `/api/voice` endpoint (new), add learning endpoints, start LearningStreamConsumer in lifespan
- `orchestration/mcp/modules/agents/voice_command_intelligence.py` — accept `chain_id` in `process_voice_command`, add `device_type` and `chain_id` to `_publish_failure_event()` payload
- `orchestration/mcp/modules/voice-learning/voice_learning_server.py` — ensure `run_learning_cycle()` return value includes `cycle_id` field for downstream pattern storage and event publishing

## Testing Strategy

- **Unit tests** (`tests/unit/`): ChainParser splitting logic (both languages, edge cases, quoted strings, skip-list), DialogRenderer template filling and context rule application, InteractionEvent field mapping
- **Integration tests** (`tests/integration/`): Full chain parse -> execute -> dialog render pipeline; Redis consumer -> Postgres write; learning cycle trigger -> pattern storage; dialog fixture validation in both en/cs
- **Dialog test fixtures:** Auto-collected from `VoiceDialog.test_fixture` fields, validated in both en/cs
- **Markers:** `@pytest.mark.integration` for Redis/Postgres tests, `@pytest.mark.unit` for pure logic, `@pytest.mark.slow` for full learning cycle tests
