# Voice Command Knowledge System - MIA Integration Guide

## Overview

This document describes how the Voice Command Knowledge Storage and Retrieval System integrates with existing MIA Universal components, specifically the MCP Framework, Core Orchestrator, and car assistant configuration.

## Integration Points

### 1. MCP Framework Integration

The knowledge system extends the existing `MCPServer` and `MCPClient` classes to provide knowledge capabilities:

```python
# In modules/core-orchestrator/main.py or new modules/knowledge-store/main.py

from mcp_framework import MCPServer, create_tool
from knowledge_store import VoiceKnowledgeService

class VoiceKnowledgeServer(MCPServer):
    """MCP Server for voice command knowledge operations"""

    def __init__(self):
        super().__init__("voice-knowledge-service", "1.0.0")
        self.knowledge_service = VoiceKnowledgeService()
        self.setup_tools()

    def setup_tools(self):
        """Register knowledge tools with MCP"""

        # Store interaction event
        store_tool = create_tool(
            name="store_interaction_event",
            description="Store a voice command interaction with context and outcome",
            schema={
                "type": "object",
                "properties": {
                    "event": {
                        "type": "object",
                        "description": "Voice interaction event data"
                    }
                },
                "required": ["event"]
            },
            handler=self.knowledge_service.store_interaction_event
        )
        self.add_tool(store_tool)

        # Find similar commands
        similar_tool = create_tool(
            name="find_similar_commands",
            description="Find past commands similar to a new voice input",
            schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "intent": {"type": "string"},
                    "context": {"type": "object"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["text"]
            },
            handler=self.knowledge_service.find_similar_commands
        )
        self.add_tool(similar_tool)

        # Get patterns for intent
        patterns_tool = create_tool(
            name="get_patterns_for_intent",
            description="Get successful command patterns for an intent",
            schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "min_success_rate": {"type": "number", "default": 0.0},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["intent"]
            },
            handler=self.knowledge_service.get_patterns_for_intent
        )
        self.add_tool(patterns_tool)

        # Sync patterns with peers
        sync_tool = create_tool(
            name="sync_patterns_to_peers",
            description="Synchronize discovered patterns to other devices",
            schema={
                "type": "object",
                "properties": {
                    "patterns": {
                        "type": "array",
                        "items": {"type": "object"}
                    },
                    "target_devices": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["patterns"]
            },
            handler=self.knowledge_service.sync_patterns
        )
        self.add_tool(sync_tool)
```

### 2. Core Orchestrator Integration

The knowledge system integrates with the `CoreOrchestrator` to enhance command interpretation:

```python
# In modules/core-orchestrator/main.py

from knowledge_store import VoiceKnowledgeService

class CoreOrchestrator(MCPServer):
    """Enhanced Core Orchestrator with voice knowledge integration"""

    def __init__(self):
        super().__init__("ai-servis-core", "1.0.0")
        self.knowledge_service = VoiceKnowledgeService()
        self.nlp_processor = EnhancedNLPProcessor()
        # ... rest of init

    async def handle_voice_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Enhanced command handling with knowledge integration"""

        logger.info(f"Processing voice command: {text}")

        try:
            # Step 1: Find similar past commands for context
            similar_events = await self.knowledge_service.find_similar_commands(
                text=text,
                intent_filter=None,
                limit=5
            )

            # Step 2: Get patterns that might apply
            if similar_events:
                primary_intent = similar_events[0]['interpreted_command']['intent']
                patterns = await self.knowledge_service.get_patterns_for_intent(
                    intent=primary_intent,
                    min_success_rate=0.7,
                    limit=5
                )
            else:
                patterns = []

            # Step 3: Parse command with context from similar events
            parsed = await self.nlp_processor.parse_command(
                text=text,
                context_events=similar_events,
                suggested_patterns=patterns
            )

            logger.info(f"Parsed command: {parsed}")

            # Step 4: Route to service
            result = await self._route_command(parsed, context)

            # Step 5: Store interaction for future learning
            event = {
                'id': str(uuid.uuid4()),
                'timestamp': int(time.time() * 1000),
                'device_id': os.getenv('DEVICE_ID', 'unknown'),
                'user_id': context.get('user_id') if context else 'anonymous',
                'session_id': context.get('session_id') if context else str(uuid.uuid4()),
                'voice_input': {
                    'raw_text': text,
                    'confidence_score': parsed.get('confidence', 0.8)
                },
                'interpreted_command': {
                    'intent': parsed.get('intent'),
                    'confidence': parsed.get('confidence', 0.8),
                    'parameters': parsed.get('parameters', {})
                },
                'execution_outcome': {
                    'status': 'success' if result else 'failed',
                    'result_summary': str(result)
                },
                'metadata': {
                    'version': '1.0',
                    'storage_tier': 'warm'
                }
            }

            await self.knowledge_service.store_interaction_event(event)

            return f"Command processed successfully: {result}"

        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            return f"Error processing command: {str(e)}"
```

### 3. Car Assistant Configuration Integration

The knowledge system integrates with the car assistant configuration:

```python
# In modules/core-orchestrator/car_assistant_config.py

from knowledge_store import VoiceKnowledgeService

CAR_ASSISTANT_CONFIG = {
    "name": "Mobile Intelligent Assistant",
    "mcp_servers": {
        "hardware": "mia-hardware",
        "prompts": "mcp-prompts-memory",
        "orchestrator": "mia-orchestrator",
        "voice_knowledge": "voice-knowledge-service"  # NEW
    },
    "capabilities": {
        "gpio_control": True,
        "obd_diagnostics": True,
        "rf_communication": True,
        "audio_control": True,
        "climate_control": True,
        "voice_command_learning": True  # NEW
    },
    "safety": {
        "distracted_driving_protection": True,
        "emergency_detection": True,
        "diagnostic_monitoring": True,
        "voice_command_safety": True  # NEW
    },
    "knowledge_system": {
        "enabled": True,
        "storage_path": "~/.mia/knowledge",
        "hot_cache_size_mb": 128,
        "warm_tier_days": 7,
        "cold_tier_days": 365,
        "privacy_mode": "high",  # high, medium, low
        "sync_enabled": True,
        "sync_interval_hours": 6
    }
}

# Knowledge system initialization
async def initialize_voice_knowledge_service():
    """Initialize the voice knowledge service for car assistant"""

    knowledge_config = CAR_ASSISTANT_CONFIG.get('knowledge_system', {})

    service = VoiceKnowledgeService(
        storage_path=knowledge_config.get('storage_path', '~/.mia/knowledge'),
        hot_cache_size_mb=knowledge_config.get('hot_cache_size_mb', 128),
        warm_tier_days=knowledge_config.get('warm_tier_days', 7),
        cold_tier_days=knowledge_config.get('cold_tier_days', 365),
        privacy_mode=knowledge_config.get('privacy_mode', 'high'),
        sync_enabled=knowledge_config.get('sync_enabled', True)
    )

    await service.initialize()

    return service
```

### 4. Enhanced NLP Processor Integration

The knowledge system enhances the existing `EnhancedNLPProcessor`:

```python
# In modules/core-orchestrator/enhanced_orchestrator.py

from knowledge_store import VoiceKnowledgeService

class EnhancedNLPProcessor:
    """Enhanced NLP with knowledge-augmented interpretation"""

    def __init__(self, knowledge_service: VoiceKnowledgeService):
        self.knowledge_service = knowledge_service
        self.intent_patterns = self._initialize_patterns()
        # ... rest of init

    async def parse_command(
        self,
        text: str,
        context_events: List[Dict] = None,
        suggested_patterns: List[Dict] = None
    ) -> Dict[str, Any]:
        """Parse command with knowledge-augmented context"""

        # Traditional parsing
        base_result = await self._traditional_parse(text)

        # Enhance with similar past events
        if context_events:
            base_result = self._apply_context_boost(base_result, context_events)

        # Refine with patterns
        if suggested_patterns:
            base_result = self._apply_pattern_suggestions(base_result, suggested_patterns)

        return base_result

    def _apply_context_boost(
        self,
        result: Dict,
        context_events: List[Dict]
    ) -> Dict:
        """Boost confidence based on similar past events"""

        if not context_events:
            return result

        # If similar events had same intent, increase confidence
        similar_intents = [e['interpreted_command']['intent'] for e in context_events]
        primary_intent = result.get('intent')

        if primary_intent in similar_intents:
            intent_count = similar_intents.count(primary_intent)
            boost = min(0.2, intent_count * 0.05)  # Max 20% boost
            result['confidence'] = min(1.0, result['confidence'] + boost)
            result['confidence_rationale'] = f"Boosted by {intent_count} similar past events"

        # Extract likely parameters from similar events
        if similar_intents:
            common_params = self._extract_common_parameters(context_events)
            result['suggested_parameters'] = common_params

        return result

    def _apply_pattern_suggestions(
        self,
        result: Dict,
        patterns: List[Dict]
    ) -> Dict:
        """Apply suggestions from learned patterns"""

        if not patterns:
            return result

        # Use most successful pattern as template
        best_pattern = max(patterns, key=lambda p: p.get('success_rate', 0))

        if best_pattern['success_rate'] > 0.8:
            result['parameter_template'] = best_pattern['parameter_variations'][0]
            result['pattern_suggestion'] = best_pattern['pattern_id']

        return result

    def _extract_common_parameters(self, events: List[Dict]) -> Dict:
        """Extract most common parameter values from events"""

        from collections import Counter

        params_by_key = {}

        for event in events:
            params = event.get('interpreted_command', {}).get('parameters', {})
            for key, value in params.items():
                if key not in params_by_key:
                    params_by_key[key] = []
                params_by_key[key].append(value)

        # Get most common value for each parameter
        common = {}
        for key, values in params_by_key.items():
            counter = Counter(values)
            if counter:
                most_common, count = counter.most_common(1)[0]
                frequency = count / len(values)
                if frequency > 0.5:  # At least 50% frequency
                    common[key] = most_common

        return common
```

## Data Flow Diagram

```
User Voice Input
      |
      v
[Voice-to-Text Transcription]
      |
      v
[Core Orchestrator] ---> [Knowledge Service: find_similar_commands()]
      |                        |
      |                        v
      |                   [Hot Cache + Warm DB Query]
      |                        |
      |                        v
      |                   [Return similar events]
      |
      v
[Enhanced NLP Processor] <--- (receives similar events)
      |
      +----> [get_patterns_for_intent()]
      |            |
      |            v
      |       [Pattern Store Query]
      |            |
      |            v
      |       [Return successful patterns]
      |
      v
[Intent + Parameters] (confidence boosted by knowledge)
      |
      v
[Service Routing]
      |
      v
[Action Execution]
      |
      v
[Store Interaction Event]
      |
      +----> [store_interaction_event()]
      |            |
      |            v
      |       [Hot Cache + Warm DB]
      |       [Background: Archive detection]
      |
      v
[Pattern Detection (async)]
      |
      v
[Sync Patterns to Peers (async)]
      |
      v
[Distributed Knowledge Update]
```

## Usage Examples

### Example 1: Playing Music with Context Enhancement

```python
# User says: "Play music"

# Step 1: Query knowledge for similar commands
similar = await knowledge_service.find_similar_commands(
    text="Play music",
    intent=None,
    limit=5
)
# Returns: [
#   {intent: 'play_music', parameters: {artist: 'The Beatles'}, success_rate: 0.95},
#   {intent: 'play_music', parameters: {genre: 'jazz'}, success_rate: 0.87},
#   ...
# ]

# Step 2: Get patterns for play_music intent
patterns = await knowledge_service.get_patterns_for_intent(
    intent='play_music',
    min_success_rate=0.8,
    limit=5
)
# Returns: [
#   {pattern_id: 'pat_123', parameter_variations: [
#       {parameters: {artist: 'The Beatles'}, frequency: 45, success_rate: 0.98},
#       {parameters: {genre: 'jazz'}, frequency: 23, success_rate: 0.91},
#   ]}
# ]

# Step 3: Orchestrator uses this to suggest:
# "Based on your history, shall I play The Beatles?"
# Or if user said "Play music", default to most common successful pattern

# Step 4: After execution, store event
await knowledge_service.store_interaction_event({
    'intent': 'play_music',
    'parameters': {'artist': 'The Beatles'},
    'execution_status': 'success',
    'user_satisfaction': 5
})

# Step 5: Pattern detector runs async and finds pattern
# -> "User prefers The Beatles when saying 'Play music'"
# -> Syncs this pattern to other devices
```

### Example 2: Temperature Control with Safety Context

```python
# In car, user says: "Set temperature to 25"

# Step 1: Check if vehicle is moving (from context)
# If vehicle is moving, knowledge system considers:
# - Did similar commands work while driving?
# - Is this intent marked as safety-sensitive?

patterns = await knowledge_service.get_context_specific_patterns(
    intent='control_climate',
    location_hash='vehicle',
    user_activity='driving',
    limit=5
)

# Step 2: If no successful patterns while driving, system might:
# - Suggest: "Would you like me to set this temperature now or wait until you've parked?"
# - Or apply safety rules from config

# Step 3: After execution, store with full context
event = {
    'intent': 'control_climate',
    'parameters': {'temperature': 25},
    'context_snapshot': {
        'vehicle_state': {
            'speed_kmh': 80,
            'engine_state': 'running'
        },
        'user_activity': 'driving'
    },
    'execution_outcome': {
        'status': 'success',
        'execution_time_ms': 245
    }
}

await knowledge_service.store_interaction_event(event)

# Step 4: Knowledge system learns:
# "Temperature commands take ~250ms to execute"
# "These work fine while driving at any speed"
```

## Testing the Integration

```python
# Test script: tests/integration/test_voice_knowledge_integration.py

import pytest
import asyncio
from core_orchestrator import CoreOrchestrator
from knowledge_store import VoiceKnowledgeService

@pytest.fixture
async def orchestrator():
    """Create orchestrator with knowledge service"""
    orch = CoreOrchestrator()
    await orch.knowledge_service.initialize()
    yield orch
    await orch.knowledge_service.cleanup()

@pytest.mark.asyncio
async def test_voice_command_with_knowledge(orchestrator):
    """Test voice command processing with knowledge enhancement"""

    # Store some past commands
    for i in range(5):
        event = {
            'id': f'test_event_{i}',
            'timestamp': int(time.time() * 1000),
            'device_id': 'test_device',
            'user_id': 'test_user',
            'voice_input': {'raw_text': 'play music', 'confidence_score': 0.95},
            'interpreted_command': {
                'intent': 'play_music',
                'confidence': 0.95,
                'parameters': {'artist': 'The Beatles'}
            },
            'execution_outcome': {'status': 'success'}
        }
        await orchestrator.knowledge_service.store_interaction_event(event)

    # Process new command
    result = await orchestrator.handle_voice_command('play music')

    # Verify knowledge was used
    assert 'Command processed successfully' in result

    # Verify event was stored
    similar = await orchestrator.knowledge_service.find_similar_commands(
        'play music', limit=5
    )
    assert len(similar) > 0

@pytest.mark.asyncio
async def test_pattern_detection_and_sync(orchestrator):
    """Test pattern detection and cross-device sync"""

    # ... test pattern detection
    # ... test sync protocol
    pass
```

## File Structure

```
modules/
├── knowledge_store/
│   ├── __init__.py
│   ├── main.py                 # VoiceKnowledgeService main class
│   ├── hot_cache.py            # In-memory cache implementation
│   ├── warm_database.py        # SQLite storage layer
│   ├── retrieval.py            # Query and similarity search
│   ├── patterns.py             # Pattern detection engine
│   ├── sync.py                 # Synchronization protocol
│   ├── privacy.py              # Privacy enforcement
│   └── lifecycle.py            # Data retention management
├── core-orchestrator/
│   ├── main.py                 # Updated with knowledge integration
│   ├── enhanced_orchestrator.py # Enhanced NLP with knowledge
│   └── car_assistant_config.py # Updated config
│
docs/
├── architecture/
│   ├── voice-command-knowledge-storage-spec.json
│   ├── voice-knowledge-system-implementation-guide.md
│   └── voice-knowledge-mia-integration.md (this file)
│
tests/
├── unit/
│   ├── test_hot_cache.py
│   ├── test_warm_database.py
│   ├── test_retrieval.py
│   ├── test_patterns.py
│   └── test_privacy.py
└── integration/
    ├── test_voice_knowledge_integration.py
    └── test_knowledge_orchestrator.py
```

## Performance Targets in MIA Context

- **Hot path (in-drive command)**: < 50ms latency for similar command retrieval
- **Pattern matching**: < 30ms for intent-specific pattern suggestions
- **Sync overhead**: < 500ms for pattern sync during WiFi connection
- **Storage footprint**: < 1GB for 1 year of driving history per device
- **Memory footprint**: < 128MB for hot cache during active driving

## Privacy Considerations for Car Context

1. **Location data**: Delete precise coordinates after 7 days, keep semantic location (home vs highway) for patterns
2. **Voice transcripts**: Delete raw audio immediately, keep anonymized transcripts for learning
3. **Route history**: Don't store complete routes, only destination frequency and patterns
4. **Vehicle state**: Keep only relevant states (stationary vs driving), not VIN or sensor data
5. **User preferences**: Learn patterns (artist preferences), forget user identity after 90 days

## Next Steps

1. Review integration architecture with team
2. Prioritize which features to implement first
3. Set up development environment
4. Begin Phase 1 implementation with hot cache
5. Integrate with existing voice processing pipeline
6. Test with real driving scenarios
