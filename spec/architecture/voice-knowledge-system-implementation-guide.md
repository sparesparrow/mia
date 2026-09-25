# Voice Command Knowledge Storage and Retrieval System
## Implementation Guide for MIA Universal

## Overview

This guide details the implementation of a comprehensive knowledge storage and retrieval system for voice command interactions in the MIA Universal platform. The system enables fast pattern matching, device synchronization, and continuous learning while maintaining privacy and consistent performance.

### Key Metrics Target
- Retrieval latency: < 47ms average (< 50ms p95)
- Cache hit rate: 89%
- Data consistency: 100%
- System availability: > 99.9%
- Storage efficiency: 43% reduction through intelligent tiering

---

## Architecture Overview

### Multi-Tier Storage Architecture

The system uses four distinct storage tiers, each optimized for specific access patterns and latency requirements:

#### 1. Hot Cache (In-Memory)
- **Purpose**: Ultra-fast retrieval of recent patterns
- **Storage**: Python dictionaries/Redis
- **TTL**: 1 hour
- **Size**: ~128MB typical
- **Latency Target**: < 10ms
- **Content**: Last 100 commands, 5 most successful patterns per intent, recent user feedback

#### 2. Warm Index (SQLite Database)
- **Purpose**: Fast indexed search over last 7 days
- **Storage**: Local SQLite with B-tree indices
- **TTL**: 7 days
- **Size**: ~512MB typical
- **Latency Target**: 30-75ms
- **Content**: Full command records with metadata, pattern definitions, user feedback
- **Indices**: intent+device, timestamp, user_location, success_rate, full-text search

#### 3. Cold Archive (Compressed Append-Only Log)
- **Purpose**: Historical analysis and long-term pattern learning
- **Storage**: Zstd-compressed monthly logs
- **TTL**: 10 years (configurable)
- **Compression Ratio**: 4:1 (75% space reduction)
- **Size**: ~5GB per year
- **Content**: Anonymized events for analytics and pattern evolution

#### 4. Distributed Knowledge (Peer-to-Peer)
- **Purpose**: Pattern synchronization across devices
- **Protocol**: CRDT with vector clocks
- **Consistency**: Eventual (5-minute convergence)
- **Replication**: 3 devices minimum
- **Transport**: Mesh topology with automatic peer discovery

---

## Phase 1: Foundation Implementation

### 1.1 SQLite Schema Design

```sql
-- Main command events table
CREATE TABLE voice_events (
    id TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    device_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT,

    -- Voice input
    raw_text TEXT NOT NULL,
    stt_confidence REAL,
    duration_ms INTEGER,
    language TEXT DEFAULT 'en',
    mfcc_hash TEXT,

    -- Interpreted command
    intent TEXT NOT NULL,
    intent_confidence REAL,
    parameters JSON,
    alternative_intents JSON,

    -- Context snapshot
    location_hash TEXT,
    time_of_day TEXT,
    day_of_week INTEGER,
    vehicle_speed REAL,
    engine_state TEXT,

    -- Execution outcome
    execution_status TEXT,
    service_name TEXT,
    tool_name TEXT,
    execution_time_ms INTEGER,

    -- Metadata
    storage_tier TEXT DEFAULT 'warm',
    compressed INTEGER DEFAULT 0,
    access_count INTEGER DEFAULT 0,
    last_accessed_ts INTEGER,
    retention_policy TEXT DEFAULT 'anonymize_after_1y',

    created_ts INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Indices for hot paths
CREATE INDEX idx_timestamp ON voice_events(timestamp DESC);
CREATE INDEX idx_intent_device ON voice_events(intent, device_id);
CREATE INDEX idx_user_location ON voice_events(user_id, location_hash);
CREATE INDEX idx_success ON voice_events(execution_status);
CREATE INDEX idx_user_intent ON voice_events(user_id, intent);

-- Full-text search
CREATE VIRTUAL TABLE voice_events_fts USING fts5(
    raw_text,
    intent,
    content=voice_events,
    content_rowid=rowid
);

-- Command patterns table
CREATE TABLE command_patterns (
    pattern_id TEXT PRIMARY KEY,
    pattern_type TEXT,
    intent_class TEXT NOT NULL,
    signature TEXT UNIQUE NOT NULL,

    occurrences INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    unique_devices INTEGER DEFAULT 0,
    success_rate REAL,

    parameter_variations JSON,
    sample_event_ids JSON,

    first_occurrence_ts INTEGER,
    last_occurrence_ts INTEGER,
    created_ts INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

CREATE INDEX idx_pattern_intent ON command_patterns(intent_class);
CREATE INDEX idx_pattern_signature ON command_patterns(signature);
CREATE INDEX idx_pattern_success ON command_patterns(success_rate DESC);

-- User feedback table
CREATE TABLE user_feedback (
    feedback_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES voice_events(id),
    satisfaction INTEGER CHECK(satisfaction >= 1 AND satisfaction <= 5),
    was_correct INTEGER,
    correction TEXT,
    timestamp INTEGER,

    FOREIGN KEY(event_id) REFERENCES voice_events(id)
);

CREATE INDEX idx_feedback_event ON user_feedback(event_id);
CREATE INDEX idx_feedback_satisfaction ON user_feedback(satisfaction);

-- Knowledge indices
CREATE TABLE knowledge_indices (
    index_key TEXT PRIMARY KEY,
    matching_events JSON,
    matching_patterns JSON,
    bloom_filter TEXT,
    last_updated_ts INTEGER
);

-- Synchronization tracking
CREATE TABLE sync_events (
    sync_id TEXT PRIMARY KEY,
    source_device TEXT,
    target_devices JSON,
    patterns_synced JSON,
    sync_status TEXT,
    bytes_transferred INTEGER,
    timestamp INTEGER
);
```

### 1.2 Hot Cache Implementation

```python
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from time import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached item with TTL"""
    value: any
    created_at: float
    accessed_at: float
    access_count: int = 0

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry has exceeded TTL"""
        return (time() - self.created_at) > ttl_seconds

    def update_access(self):
        """Update access metadata"""
        self.accessed_at = time()
        self.access_count += 1

class HotCache:
    """In-memory cache for recent patterns and commands"""

    def __init__(self, max_size_mb: int = 128, ttl_seconds: int = 3600):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size_mb = max_size_mb
        self.ttl_seconds = ttl_seconds
        self.lock = asyncio.Lock()

        # Separate indices for fast lookup
        self.intent_index: Dict[str, List[str]] = {}  # intent -> event_ids
        self.device_index: Dict[str, List[str]] = {}  # device_id -> event_ids
        self.pattern_index: Dict[str, str] = {}  # pattern_sig -> pattern_id

    async def get(self, key: str) -> Optional[any]:
        """Retrieve value from cache"""
        async with self.lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]
            if entry.is_expired(self.ttl_seconds):
                del self.cache[key]
                return None

            entry.update_access()
            return entry.value

    async def set(self, key: str, value: any) -> bool:
        """Store value in cache with TTL"""
        async with self.lock:
            # Check size before adding
            current_size = self._estimate_size()
            if current_size >= self.max_size_mb:
                # Evict least recently used
                self._evict_lru()

            self.cache[key] = CacheEntry(
                value=value,
                created_at=time(),
                accessed_at=time()
            )
            return True

    async def index_event(self, intent: str, device_id: str, event_id: str):
        """Add event to fast lookup indices"""
        async with self.lock:
            if intent not in self.intent_index:
                self.intent_index[intent] = []
            self.intent_index[intent].append(event_id)

            if device_id not in self.device_index:
                self.device_index[device_id] = []
            self.device_index[device_id].append(event_id)

    async def get_by_intent(self, intent: str) -> List[str]:
        """Get recent events by intent"""
        async with self.lock:
            return self.intent_index.get(intent, [])[:10]

    async def get_by_device(self, device_id: str) -> List[str]:
        """Get recent events by device"""
        async with self.lock:
            return self.device_index.get(device_id, [])[:10]

    def _estimate_size(self) -> int:
        """Rough estimate of cache size in MB"""
        # Real implementation would use more accurate sizing
        return len(self.cache) // 1000

    def _evict_lru(self):
        """Evict least recently used entries"""
        if not self.cache:
            return

        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].accessed_at
        )
        del self.cache[lru_key]
        logger.info(f"Evicted LRU entry: {lru_key}")

    async def clear(self):
        """Clear entire cache"""
        async with self.lock:
            self.cache.clear()
            self.intent_index.clear()
            self.device_index.clear()
            self.pattern_index.clear()

```

### 1.3 Warm Tier Database Layer

```python
import sqlite3
from typing import List, Dict, Optional, Tuple
from dataclasses import asdict
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class WarmDatabaseLayer:
    """SQLite-based warm tier storage with efficient indexing"""

    def __init__(self, db_path: str = "~/.mia/knowledge/warm_index/commands.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Create database and indices if needed"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        # Enable optimizations
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
        self.conn.execute("PRAGMA temp_store = MEMORY")

        # Create tables and indices (full schema from 1.1)
        self._create_schema()

    def store_event(self, event: 'VoiceInteractionEvent') -> str:
        """Store voice interaction event"""
        event_dict = asdict(event)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO voice_events (
                id, timestamp, device_id, user_id, session_id,
                raw_text, stt_confidence, duration_ms, language, mfcc_hash,
                intent, intent_confidence, parameters, alternative_intents,
                location_hash, time_of_day, day_of_week, vehicle_speed, engine_state,
                execution_status, service_name, tool_name, execution_time_ms,
                storage_tier, retention_policy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.id, event.timestamp, event.device_id, event.user_id, event.session_id,
            event.voice_input.raw_text, event.voice_input.confidence_score,
            event.voice_input.duration_ms, event.voice_input.language_detected,
            event.voice_input.acoustic_features.get('mfcc_hash') if event.voice_input.acoustic_features else None,
            event.interpreted_command.intent, event.interpreted_command.confidence,
            json.dumps(event.interpreted_command.parameters),
            json.dumps([
                {'intent': alt[0], 'confidence': alt[1]}
                for alt in event.interpreted_command.alternative_intents
            ]),
            event.context_snapshot.get('location_hash') if event.context_snapshot else None,
            event.context_snapshot.get('time_of_day') if event.context_snapshot else None,
            event.context_snapshot.get('day_of_week') if event.context_snapshot else None,
            event.context_snapshot.get('vehicle_state', {}).get('speed_kmh') if event.context_snapshot else None,
            event.context_snapshot.get('vehicle_state', {}).get('engine_state') if event.context_snapshot else None,
            event.execution_outcome.get('status'),
            event.execution_outcome.get('executed_action', {}).get('service_name'),
            event.execution_outcome.get('executed_action', {}).get('tool_name'),
            event.execution_outcome.get('execution_time_ms'),
            'warm',
            'anonymize_after_1y'
        ))

        self.conn.commit()
        logger.info(f"Stored event: {event.id}")
        return event.id

    def find_similar_by_intent(self, intent: str, limit: int = 10) -> List[Dict]:
        """Fast retrieval of commands by intent"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM voice_events
            WHERE intent = ?
            AND timestamp > datetime('now', '-7 days')
            ORDER BY intent_confidence DESC, timestamp DESC
            LIMIT ?
        """, (intent, limit))

        return [dict(row) for row in cursor.fetchall()]

    def find_contextual_patterns(
        self,
        intent: str,
        location_hash: Optional[str],
        time_of_day: Optional[str],
        limit: int = 5
    ) -> List[Dict]:
        """Find patterns effective in specific context"""
        cursor = self.conn.cursor()

        where_clauses = ["intent = ?"]
        params = [intent]

        if location_hash:
            where_clauses.append("location_hash = ?")
            params.append(location_hash)

        if time_of_day:
            where_clauses.append("time_of_day = ?")
            params.append(time_of_day)

        where_clause = " AND ".join(where_clauses)

        cursor.execute(f"""
            SELECT * FROM voice_events
            WHERE {where_clause}
            AND execution_status = 'success'
            AND timestamp > datetime('now', '-7 days')
            ORDER BY intent_confidence DESC
            LIMIT ?
        """, params + [limit])

        return [dict(row) for row in cursor.fetchall()]

    def full_text_search(
        self,
        query: str,
        intent_filter: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Full-text search over voice commands"""
        cursor = self.conn.cursor()

        if intent_filter:
            cursor.execute("""
                SELECT ve.* FROM voice_events ve
                WHERE ve.rowid IN (
                    SELECT rowid FROM voice_events_fts WHERE raw_text MATCH ?
                )
                AND ve.intent = ?
                ORDER BY ve.timestamp DESC
                LIMIT ?
            """, (query, intent_filter, limit))
        else:
            cursor.execute("""
                SELECT ve.* FROM voice_events ve
                WHERE ve.rowid IN (
                    SELECT rowid FROM voice_events_fts WHERE raw_text MATCH ?
                )
                ORDER BY ve.timestamp DESC
                LIMIT ?
            """, (query, limit))

        return [dict(row) for row in cursor.fetchall()]

    def store_pattern(self, pattern: 'CommandPattern') -> str:
        """Store detected pattern"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO command_patterns (
                pattern_id, pattern_type, intent_class, signature,
                occurrences, unique_users, unique_devices, success_rate,
                parameter_variations, sample_event_ids,
                first_occurrence_ts, last_occurrence_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.pattern_id, pattern.pattern_type, pattern.intent_class,
            pattern.signature, pattern.frequency.get('occurrences'),
            pattern.frequency.get('unique_users'), pattern.frequency.get('unique_devices'),
            pattern.success_rate,
            json.dumps(pattern.parameters_variations),
            json.dumps(pattern.matching_events),
            pattern.frequency.get('first_occurrence_ts'),
            pattern.frequency.get('last_occurrence_ts')
        ))

        self.conn.commit()
        return pattern.pattern_id

    def get_patterns_for_intent(
        self,
        intent: str,
        min_success_rate: float = 0.0,
        limit: int = 10
    ) -> List[Dict]:
        """Get all patterns for an intent"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM command_patterns
            WHERE intent_class = ?
            AND success_rate >= ?
            ORDER BY success_rate DESC, occurrences DESC
            LIMIT ?
        """, (intent, min_success_rate, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_success_metrics(
        self,
        intent_filter: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """Get success statistics"""
        cursor = self.conn.cursor()

        if intent_filter:
            cursor.execute("""
                SELECT
                    intent,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN execution_status = 'success' THEN 1 ELSE 0 END) as success_count,
                    AVG(intent_confidence) as avg_confidence
                FROM voice_events
                WHERE intent = ?
                AND timestamp > datetime('now', ? || ' days')
                GROUP BY intent
            """, (intent_filter, -days))
        else:
            cursor.execute("""
                SELECT
                    intent,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN execution_status = 'success' THEN 1 ELSE 0 END) as success_count,
                    AVG(intent_confidence) as avg_confidence
                FROM voice_events
                WHERE timestamp > datetime('now', ? || ' days')
                GROUP BY intent
                ORDER BY success_count DESC
            """, (-days,))

        rows = cursor.fetchall()
        return {
            row['intent']: {
                'total': row['total_count'],
                'success': row['success_count'],
                'success_rate': row['success_count'] / row['total_count'] if row['total_count'] > 0 else 0,
                'avg_confidence': row['avg_confidence']
            }
            for row in rows
        }
```

---

## Phase 2: Retrieval and Similarity Matching

### 2.1 Semantic Similarity Search

```python
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class SemanticSimilarityEngine:
    """Find commands semantically similar to a new voice input"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with pre-trained sentence transformer"""
        self.model = SentenceTransformer(model_name)
        self.embedding_cache = {}

    def get_embedding(self, text: str) -> np.ndarray:
        """Get semantic embedding for text"""
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        embedding = self.model.encode(text, convert_to_numpy=True)
        self.embedding_cache[text] = embedding
        return embedding

    async def find_similar_commands(
        self,
        query_text: str,
        candidate_events: List[Dict],
        top_k: int = 5,
        threshold: float = 0.75
    ) -> List[Tuple[Dict, float]]:
        """Find top-k similar commands from candidates"""

        # Get query embedding
        query_embedding = self.get_embedding(query_text)

        # Score all candidates
        scores = []
        for event in candidate_events:
            candidate_embedding = self.get_embedding(event['raw_text'])

            # Cosine similarity
            similarity = np.dot(query_embedding, candidate_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(candidate_embedding)
            )

            if similarity >= threshold:
                scores.append((event, similarity))

        # Return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

```

### 2.2 Acoustic Feature Matching

```python
import hashlib
from typing import Dict, Optional, List

class AcousticMatcher:
    """Find commands with similar acoustic properties (prosody, accent)"""

    def extract_mfcc_hash(self, audio_features: Dict) -> str:
        """Extract or compute MFCC hash from audio features"""
        if 'mfcc_hash' in audio_features:
            return audio_features['mfcc_hash']

        # In real implementation, would extract MFCC from raw audio
        # and compute hash for fast matching
        return ""

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """Compute Hamming distance between two hashes"""
        if not hash1 or not hash2:
            return float('inf')

        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    async def find_acoustic_matches(
        self,
        query_features: Dict,
        candidate_events: List[Dict],
        max_distance: int = 8,
        top_k: int = 3
    ) -> List[Tuple[Dict, int]]:
        """Find commands with similar acoustic characteristics"""

        query_hash = self.extract_mfcc_hash(query_features)
        matches = []

        for event in candidate_events:
            candidate_hash = event.get('mfcc_hash', '')
            distance = self.hamming_distance(query_hash, candidate_hash)

            if distance <= max_distance:
                matches.append((event, distance))

        # Sort by distance (lower is better)
        matches.sort(key=lambda x: x[1])
        return matches[:top_k]

```

---

## Phase 3: Pattern Detection and Clustering

### 3.1 Pattern Detection Algorithm

```python
from typing import List, Set, Dict
from dataclasses import dataclass
import hashlib
import json
from collections import defaultdict

@dataclass
class PatternDetectionResult:
    """Result of pattern detection"""
    pattern_id: str
    intent: str
    signature: str
    matching_events: List[str]
    parameter_variations: List[Dict]
    success_rate: float
    occurrence_count: int

class PatternDetector:
    """Detect recurring command patterns from events"""

    def __init__(self, min_occurrences: int = 5, min_success_rate: float = 0.7):
        self.min_occurrences = min_occurrences
        self.min_success_rate = min_success_rate

    def compute_pattern_signature(
        self,
        intent: str,
        parameter_keys: Set[str]
    ) -> str:
        """Compute compact signature for pattern"""
        data = {
            'intent': intent,
            'params': sorted(parameter_keys)
        }

        hash_input = json.dumps(data, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    async def detect_patterns(
        self,
        events: List[Dict]
    ) -> List[PatternDetectionResult]:
        """Detect patterns from events"""

        patterns = defaultdict(lambda: {
            'events': [],
            'parameters': defaultdict(int),
            'successes': 0
        })

        # Group events by intent
        by_intent = defaultdict(list)
        for event in events:
            by_intent[event['intent']].append(event)

        # Detect patterns within each intent
        results = []
        for intent, intent_events in by_intent.items():
            # Group by parameter combination
            param_groups = defaultdict(list)

            for event in intent_events:
                params = event.get('parameters', {})
                param_keys = tuple(sorted(params.keys()))
                param_groups[param_keys].append(event)

            # Find frequent patterns
            for param_keys, group_events in param_groups.items():
                if len(group_events) >= self.min_occurrences:
                    # Compute pattern signature
                    signature = self.compute_pattern_signature(intent, set(param_keys))

                    # Calculate success rate
                    successful = sum(
                        1 for e in group_events
                        if e.get('execution_status') == 'success'
                    )
                    success_rate = successful / len(group_events)

                    if success_rate >= self.min_success_rate:
                        results.append(PatternDetectionResult(
                            pattern_id=self._generate_pattern_id(),
                            intent=intent,
                            signature=signature,
                            matching_events=[e['id'] for e in group_events],
                            parameter_variations=self._extract_param_variations(group_events),
                            success_rate=success_rate,
                            occurrence_count=len(group_events)
                        ))

        return results

    def _extract_param_variations(self, events: List[Dict]) -> List[Dict]:
        """Extract parameter variations from events"""
        variations = defaultdict(lambda: {'count': 0, 'success_count': 0})

        for event in events:
            params = event.get('parameters', {})
            param_tuple = tuple(sorted((k, v) for k, v in params.items()))

            variations[param_tuple]['count'] += 1
            if event.get('execution_status') == 'success':
                variations[param_tuple]['success_count'] += 1

        return [
            {
                'parameters': dict(param_tuple),
                'frequency': var['count'],
                'success_rate': var['success_count'] / var['count']
            }
            for param_tuple, var in variations.items()
        ]

    def _generate_pattern_id(self) -> str:
        """Generate unique pattern ID"""
        import uuid
        return str(uuid.uuid4())

```

---

## Phase 4: Distributed Synchronization

### 4.1 CRDT Pattern Store with Vector Clocks

```python
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class VectorClock:
    """Vector clock for causality tracking"""
    clocks: Dict[str, int] = field(default_factory=dict)

    def increment(self, device_id: str):
        """Increment clock for a device"""
        if device_id not in self.clocks:
            self.clocks[device_id] = 0
        self.clocks[device_id] += 1

    def happens_before(self, other: 'VectorClock') -> bool:
        """Check if this clock happens before another"""
        # self < other if all clocks <= and at least one is <
        if not self.clocks or not other.clocks:
            return False

        less_or_equal = all(
            self.clocks.get(k, 0) <= other.clocks.get(k, 0)
            for k in set(self.clocks.keys()) | set(other.clocks.keys())
        )

        strictly_less = any(
            self.clocks.get(k, 0) < other.clocks.get(k, 0)
            for k in set(self.clocks.keys()) | set(other.clocks.keys())
        )

        return less_or_equal and strictly_less

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        """Merge two vector clocks (elementwise max)"""
        merged = VectorClock()
        all_keys = set(self.clocks.keys()) | set(other.clocks.keys())

        for key in all_keys:
            merged.clocks[key] = max(
                self.clocks.get(key, 0),
                other.clocks.get(key, 0)
            )

        return merged

class CRDTPatternStore:
    """Conflict-free replicated pattern store"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.vector_clock = VectorClock()
        self.patterns: Dict[str, Dict] = {}
        self.tombstones: Dict[str, VectorClock] = {}  # Deleted patterns

    def add_pattern(self, pattern_id: str, pattern: Dict) -> None:
        """Add pattern with vector clock"""
        self.vector_clock.increment(self.device_id)

        pattern['vector_clock'] = self.vector_clock.clocks.copy()
        pattern['device_id'] = self.device_id
        pattern['timestamp'] = datetime.now().isoformat()

        self.patterns[pattern_id] = pattern

        # Remove from tombstones if it was deleted
        if pattern_id in self.tombstones:
            del self.tombstones[pattern_id]

        logger.info(f"Added pattern {pattern_id} with clock {self.vector_clock.clocks}")

    def merge_pattern(self, pattern_id: str, incoming: Dict) -> bool:
        """Merge incoming pattern with potential conflict"""

        # Check if this is a tombstone (deleted pattern)
        if pattern_id in self.tombstones:
            incoming_clock = VectorClock()
            incoming_clock.clocks = incoming.get('vector_clock', {})

            if incoming_clock.happens_before(self.tombstones[pattern_id]):
                # Incoming is older than deletion, ignore
                return False

        if pattern_id not in self.patterns:
            # New pattern
            self.patterns[pattern_id] = incoming
            self.vector_clock.merge(VectorClock())
            self.vector_clock.clocks.update(incoming.get('vector_clock', {}))
            return True

        # Conflict: both have pattern, resolve by:
        # 1. Higher confidence version wins
        # 2. If equal, lexicographic device_id wins

        existing_confidence = self.patterns[pattern_id].get('success_rate', 0)
        incoming_confidence = incoming.get('success_rate', 0)

        if incoming_confidence > existing_confidence:
            self.patterns[pattern_id] = incoming
            return True
        elif incoming_confidence == existing_confidence:
            existing_device = self.patterns[pattern_id].get('device_id', '')
            incoming_device = incoming.get('device_id', '')

            if incoming_device < existing_device:
                self.patterns[pattern_id] = incoming
                return True
            elif incoming_device == existing_device:
                # Merge parameter variations
                self._merge_parameter_variations(pattern_id, incoming)
                return True

        return False

    def _merge_parameter_variations(self, pattern_id: str, incoming: Dict):
        """Merge parameter variations from incoming pattern"""
        existing = self.patterns[pattern_id]

        existing_params = {
            tuple(sorted(v['parameters'].items())): v
            for v in existing.get('parameter_variations', [])
        }

        incoming_params = {
            tuple(sorted(v['parameters'].items())): v
            for v in incoming.get('parameter_variations', [])
        }

        # Merge: sum frequencies, take max success_rate
        merged = {}
        all_keys = set(existing_params.keys()) | set(incoming_params.keys())

        for key in all_keys:
            if key in existing_params and key in incoming_params:
                merged[key] = {
                    'parameters': dict(key),
                    'frequency': existing_params[key]['frequency'] + incoming_params[key]['frequency'],
                    'success_rate': max(
                        existing_params[key]['success_rate'],
                        incoming_params[key]['success_rate']
                    )
                }
            elif key in existing_params:
                merged[key] = existing_params[key]
            else:
                merged[key] = incoming_params[key]

        existing['parameter_variations'] = list(merged.values())
```

### 4.2 Synchronization Protocol

```python
import asyncio
from typing import List, Dict
import json
import logging

logger = logging.getLogger(__name__)

class SyncProtocol:
    """Gossip-based synchronization protocol for pattern knowledge"""

    def __init__(
        self,
        device_id: str,
        pattern_store: CRDTPatternStore,
        batch_size: int = 100,
        batch_timeout_seconds: int = 300
    ):
        self.device_id = device_id
        self.pattern_store = pattern_store
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.sync_queue: List[Dict] = []
        self.last_sync_ts: Dict[str, int] = {}  # device_id -> timestamp
        self.peers: List[str] = []  # Connected peer device IDs

    async def initiate_sync(self, peer_device_id: str) -> bool:
        """Initiate sync with a peer"""
        logger.info(f"Initiating sync with {peer_device_id}")

        # Get patterns newer than last sync
        new_patterns = self._get_patterns_since_last_sync(peer_device_id)

        if not new_patterns:
            logger.debug(f"No new patterns to sync with {peer_device_id}")
            return True

        # Batch patterns for transfer
        batches = [
            new_patterns[i:i + self.batch_size]
            for i in range(0, len(new_patterns), self.batch_size)
        ]

        # Send batches
        for batch in batches:
            payload = {
                'source_device': self.device_id,
                'patterns': batch,
                'vector_clock': self.pattern_store.vector_clock.clocks,
                'timestamp': datetime.now().isoformat()
            }

            # Compress payload
            compressed = self._compress_payload(payload)

            # Send to peer
            success = await self._send_sync_payload(peer_device_id, compressed)
            if not success:
                self.sync_queue.extend(batch)  # Queue for retry
                return False

            logger.info(f"Synced {len(batch)} patterns to {peer_device_id}")

        # Update last sync timestamp
        self.last_sync_ts[peer_device_id] = int(time.time() * 1000)
        return True

    async def receive_sync(self, payload: Dict) -> Dict:
        """Receive and merge patterns from peer"""
        logger.info(f"Receiving sync from {payload['source_device']}")

        patterns = payload.get('patterns', [])
        merged_count = 0
        conflict_count = 0

        for pattern in patterns:
            pattern_id = pattern.get('pattern_id')

            if self.pattern_store.merge_pattern(pattern_id, pattern):
                merged_count += 1
            else:
                conflict_count += 1

        return {
            'status': 'success',
            'merged_count': merged_count,
            'conflict_count': conflict_count,
            'total_processed': len(patterns)
        }

    def _get_patterns_since_last_sync(self, peer_device_id: str) -> List[Dict]:
        """Get patterns changed since last sync with peer"""
        last_sync = self.last_sync_ts.get(peer_device_id, 0)

        # Filter patterns by timestamp (would need to add timestamp to patterns)
        return [
            pattern for pattern in self.pattern_store.patterns.values()
            if pattern.get('timestamp_ms', 0) > last_sync
        ]

    def _compress_payload(self, payload: Dict) -> bytes:
        """Compress sync payload with zstd"""
        import zstd

        json_bytes = json.dumps(payload).encode('utf-8')
        compressed = zstd.ZstdCompressor(level=19).compress(json_bytes)

        logger.debug(f"Compressed payload: {len(json_bytes)} -> {len(compressed)} bytes")
        return compressed

    async def _send_sync_payload(self, peer_device_id: str, payload: bytes) -> bool:
        """Send compressed payload to peer (placeholder)"""
        # In real implementation, would use actual network transport
        # (WebSocket, HTTP, Bluetooth, etc.)
        logger.debug(f"Sending {len(payload)} bytes to {peer_device_id}")
        return True
```

---

## Phase 5: Privacy and Data Lifecycle Management

### 5.1 Privacy Enforcement

```python
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

class PrivacyEnforcer:
    """Enforce privacy policies on stored knowledge"""

    def __init__(self):
        self.pii_patterns = self._compile_pii_patterns()

    def _compile_pii_patterns(self):
        """Compile regex patterns for PII detection"""
        import re
        return {
            'email': re.compile(r'[\w\.-]+@[\w\.-]+\.\w+'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        }

    def anonymize_event(self, event: Dict) -> Dict:
        """Remove/hash PII from event"""
        anonymized = event.copy()

        # Remove raw transcript
        if 'raw_text' in anonymized:
            # Keep action words, remove entities
            anonymized['raw_text'] = self._remove_pii_from_text(
                anonymized['raw_text']
            )

        # Hash user_id
        if 'user_id' in anonymized:
            anonymized['user_id'] = self._hash_user_id(anonymized['user_id'])

        # Remove precise location
        if 'location_hash' in anonymized:
            # Keep semantic location (home, work) but remove coordinates
            pass

        # Mark as anonymized
        anonymized['anonymized'] = True
        anonymized['anonymization_ts'] = int(datetime.now().timestamp() * 1000)

        logger.info(f"Anonymized event {event.get('id')}")
        return anonymized

    def _remove_pii_from_text(self, text: str) -> str:
        """Remove PII from text while preserving intent"""
        anonymized = text

        for pii_type, pattern in self.pii_patterns.items():
            anonymized = pattern.sub(f'[{pii_type.upper()}]', anonymized)

        return anonymized

    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy"""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

class DataLifecycleManager:
    """Manage data retention and deletion"""

    RETENTION_POLICIES = {
        'successful_commands': {
            'duration_days': 365,
            'actions': ['move_to_cold_after_7d', 'anonymize_after_1y']
        },
        'failed_commands': {
            'duration_days': 90,
            'actions': ['extract_patterns_then_delete']
        },
        'raw_audio': {
            'duration_days': 7,
            'actions': ['delete_immediately']
        }
    }

    def __init__(self, db_layer, privacy_enforcer):
        self.db = db_layer
        self.privacy = privacy_enforcer

    async def execute_retention_policies(self):
        """Execute retention policies on stored data"""
        logger.info("Executing data retention policies")

        # Find events eligible for archival
        archive_events = self.db.query("""
            SELECT * FROM voice_events
            WHERE storage_tier = 'warm'
            AND created_ts < datetime('now', '-7 days')
        """)

        for event in archive_events:
            # Anonymize before cold storage
            anonymized = self.privacy.anonymize_event(dict(event))

            # Move to cold storage
            self._move_to_cold_archive(anonymized)

            logger.debug(f"Moved event {event['id']} to cold archive")

        # Find events eligible for deletion
        delete_events = self.db.query("""
            SELECT * FROM voice_events
            WHERE created_ts < datetime('now', '-1 year')
            AND retention_policy = 'delete_after_1y'
        """)

        for event in delete_events:
            self.db.delete_event(event['id'])
            logger.info(f"Deleted event {event['id']} per retention policy")

    def _move_to_cold_archive(self, event: Dict):
        """Move anonymized event to cold storage"""
        # Implementation would append to compressed log file
        # This is a placeholder
        pass
```

---

## Implementation Roadmap

### Week 1-2: Foundation
- [ ] Design and create SQLite schema
- [ ] Implement HotCache in-memory layer
- [ ] Basic event storage and retrieval
- [ ] Simple intent-based filtering

### Week 3-4: Retrieval Layer
- [ ] Integrate sentence-transformers for semantic search
- [ ] Implement acoustic feature matching
- [ ] Add full-text search with FTS5
- [ ] Performance benchmarking and optimization

### Week 5-6: Pattern Detection
- [ ] Implement pattern detection clustering
- [ ] Add pattern merging logic
- [ ] Parameter variation analysis
- [ ] Success rate computation

### Week 7-8: Synchronization
- [ ] CRDT implementation with vector clocks
- [ ] Gossip protocol for peer sync
- [ ] Conflict resolution strategy
- [ ] Network transport integration

### Week 9-10: Privacy & Lifecycle
- [ ] Privacy enforcement mechanisms
- [ ] Data retention policies
- [ ] Anonymization pipeline
- [ ] Compliance testing

### Week 11-12: Optimization & Testing
- [ ] Performance profiling and tuning
- [ ] Integration testing
- [ ] Load testing
- [ ] Documentation completion

---

## Performance Targets & Validation

### Query Performance Benchmarks
- Intent-based retrieval: < 50ms (p95)
- Pattern lookup: < 30ms (p95)
- Event storage: < 20ms (p95)
- Full-text search: < 100ms (p95)
- Sync payload size: < 50KB (typical 15KB)

### System Validation
- Verify retrieval latencies meet targets
- Validate data consistency across devices
- Test graceful fallback scenarios
- Confirm privacy policies enforced
- Validate pattern quality metrics

---

## File References

**Specification File**:
`/home/sparrow/projects/embedded/mia/docs/architecture/voice-command-knowledge-storage-spec.json`

**Key Modules to Implement**:
- `modules/knowledge_store/hot_cache.py` - In-memory cache layer
- `modules/knowledge_store/warm_database.py` - SQLite storage
- `modules/knowledge_store/retrieval.py` - Query and similarity search
- `modules/knowledge_store/patterns.py` - Pattern detection
- `modules/knowledge_store/sync.py` - Synchronization protocol
- `modules/knowledge_store/privacy.py` - Privacy enforcement
- `modules/knowledge_store/lifecycle.py` - Data retention management

---

## Next Steps

1. Review specification with team
2. Finalize storage schema based on project constraints
3. Begin Phase 1 implementation
4. Set up performance monitoring and testing infrastructure
5. Integrate with existing MCP framework
