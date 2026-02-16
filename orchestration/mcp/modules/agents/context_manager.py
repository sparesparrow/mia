"""
Context Manager Agent

Manages interaction context, user preferences, command history, and knowledge lifecycle.
Provides persistent context across sessions with privacy-preserving storage.

Role: Context Storage & Retrieval
Parent System: core-orchestrator
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_framework import MCPServer, Tool

logger = logging.getLogger(__name__)


class ContextOperation(str, Enum):
    """Context operations"""
    STORE = "store_context"
    RETRIEVE = "retrieve_context"
    QUERY = "query_history"
    UPDATE_PREFERENCES = "update_preferences"
    ARCHIVE = "archive_knowledge"
    DELETE = "delete_context"


class StorageLayer(str, Enum):
    """Storage layer types"""
    SESSION = "session"      # In-memory, 30min TTL
    HISTORICAL = "historical"  # Persistent, 12 months
    KNOWLEDGE = "knowledge"   # Indefinite with versioning


@dataclass
class ContextEntry:
    """A context entry with metadata"""
    key: str
    data: Dict[str, Any]
    layer: StorageLayer
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    version: int = 1
    user_id_hash: Optional[str] = None  # Anonymized user ID


class LRUCache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 1800):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry["data"]

    async def set(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        async with self._lock:
            expires_at = time.time() + (ttl or self._default_ttl)

            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self._max_size:
                # Remove oldest entry
                self._cache.popitem(last=False)

            self._cache[key] = {
                "data": data,
                "expires_at": expires_at,
                "created_at": time.time(),
            }

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear_expired(self) -> int:
        """Clear expired entries, return count cleared"""
        async with self._lock:
            now = time.time()
            expired = [
                k for k, v in self._cache.items()
                if v["expires_at"] and v["expires_at"] < now
            ]
            for k in expired:
                del self._cache[k]
            return len(expired)


class ContextManagerAgent(MCPServer):
    """
    Context storage and retrieval agent.

    Responsibilities:
    - Store and index user context information
    - Maintain command execution history
    - Manage user preferences and profiles
    - Track device and environmental context
    - Provide context-aware queries
    - Implement privacy-preserving storage
    - Manage knowledge base versioning
    - Implement data lifecycle policies

    Storage Layers:
    - Session: In-memory cache with disk backup, 30min TTL
    - Historical: Time-series storage, 12 months retention
    - Knowledge: Vector + traditional DB, indefinite with versioning

    Success Metrics:
    - Query response time: <100ms (p95)
    - Data retrieval accuracy: 99.99%
    - Storage efficiency: >85%
    - Privacy compliance: 100%
    """

    def __init__(
        self,
        name: str = "context-manager",
        version: str = "1.0.0",
        redis_client: Optional[Any] = None,
        db_client: Optional[Any] = None,
        vector_db: Optional[Any] = None,
        session_ttl: int = 1800,  # 30 minutes
        history_retention_days: int = 365,
    ):
        super().__init__(name, version)

        # External storage (optional)
        self.redis_client = redis_client
        self.db_client = db_client
        self.vector_db = vector_db

        # Configuration
        self.session_ttl = session_ttl
        self.history_retention_days = history_retention_days

        # In-memory storage layers (fallback when external storage unavailable)
        self._session_cache = LRUCache(max_size=10000, default_ttl=session_ttl)
        self._historical_store: Dict[str, List[Dict[str, Any]]] = {}
        self._knowledge_base: Dict[str, Dict[str, Any]] = {}

        # Metrics
        self.metrics = {
            "total_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "storage_operations": 0,
            "query_latency_sum": 0.0,
        }

        # Audit log (in-memory, for demo)
        self._audit_log: List[Dict[str, Any]] = []

        # Register tools
        self._register_tools()

        logger.info(f"ContextManagerAgent initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register MCP tools"""

        # Tool 1: Store context
        self.add_tool(Tool(
            name="store_context",
            description="Store context data with optional TTL and layer specification",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Storage key"},
                    "data": {"type": "object", "description": "Data to store"},
                    "layer": {"type": "string", "enum": ["session", "historical", "knowledge"]},
                    "user_id": {"type": "string", "description": "User ID (will be hashed)"},
                    "ttl": {"type": "integer", "description": "TTL in seconds (session only)"},
                },
                "required": ["key", "data"],
            },
            handler=self.store_context,
        ))

        # Tool 2: Retrieve context
        self.add_tool(Tool(
            name="retrieve_context",
            description="Retrieve context data by key or user",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Storage key"},
                    "user_id": {"type": "string", "description": "User ID"},
                    "layer": {"type": "string", "enum": ["session", "historical", "knowledge"]},
                },
            },
            handler=self.retrieve_context,
        ))

        # Tool 3: Query history
        self.add_tool(Tool(
            name="query_history",
            description="Query historical command data",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "intent": {"type": "string", "description": "Filter by intent"},
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "limit": {"type": "integer", "description": "Max results", "default": 100},
                },
            },
            handler=self.query_history,
        ))

        # Tool 4: Update preferences
        self.add_tool(Tool(
            name="update_preferences",
            description="Update user preferences",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "preferences": {"type": "object", "description": "Preferences to update"},
                    "merge": {"type": "boolean", "description": "Merge with existing", "default": True},
                },
                "required": ["user_id", "preferences"],
            },
            handler=self.update_preferences,
        ))

        # Tool 5: Store pattern
        self.add_tool(Tool(
            name="store_pattern",
            description="Store a learned pattern in knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {"type": "string", "description": "Type of pattern"},
                    "pattern_data": {"type": "object", "description": "Pattern data"},
                    "confidence": {"type": "number", "description": "Pattern confidence"},
                },
                "required": ["pattern_type", "pattern_data"],
            },
            handler=self.store_pattern,
        ))

        # Tool 6: Query patterns
        self.add_tool(Tool(
            name="query_patterns",
            description="Query knowledge base for patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {"type": "string", "description": "Filter by type"},
                    "min_confidence": {"type": "number", "description": "Minimum confidence"},
                    "limit": {"type": "integer", "description": "Max results", "default": 50},
                },
            },
            handler=self.query_patterns,
        ))

        # Tool 7: Get context metrics
        self.add_tool(Tool(
            name="get_context_metrics",
            description="Get context manager metrics",
            inputSchema={"type": "object", "properties": {}},
            handler=self.get_context_metrics,
        ))

        logger.info(f"Registered {len(self.tools)} context manager tools")

    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy"""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    def _log_audit(
        self,
        operation: str,
        key: str,
        user_id_hash: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Log operation for audit trail"""
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "key": key,
            "user_id_hash": user_id_hash,
            "success": success,
        })

        # Keep last 10000 entries
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]

    async def store_context(
        self,
        key: str,
        data: Dict[str, Any],
        layer: str = "session",
        user_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """Store context data"""
        start_time = asyncio.get_event_loop().time()
        self.metrics["total_operations"] += 1
        self.metrics["storage_operations"] += 1

        user_id_hash = self._hash_user_id(user_id) if user_id else None
        storage_key = f"{user_id_hash}:{key}" if user_id_hash else key

        try:
            now = datetime.now().isoformat()

            if layer == "session":
                # Store in session cache
                await self._session_cache.set(
                    storage_key,
                    {
                        "data": data,
                        "user_id_hash": user_id_hash,
                        "created_at": now,
                        "updated_at": now,
                    },
                    ttl=ttl or self.session_ttl,
                )

                # Also store in Redis if available
                if self.redis_client:
                    try:
                        await self.redis_client.setex(
                            f"session:{storage_key}",
                            ttl or self.session_ttl,
                            json.dumps(data),
                        )
                    except Exception as e:
                        logger.warning(f"Redis store failed: {e}")

            elif layer == "historical":
                # Store in historical storage
                if storage_key not in self._historical_store:
                    self._historical_store[storage_key] = []

                self._historical_store[storage_key].append({
                    "data": data,
                    "timestamp": now,
                    "user_id_hash": user_id_hash,
                })

                # Keep last 1000 entries per key
                if len(self._historical_store[storage_key]) > 1000:
                    self._historical_store[storage_key] = \
                        self._historical_store[storage_key][-1000:]

            elif layer == "knowledge":
                # Store in knowledge base with versioning
                if storage_key in self._knowledge_base:
                    version = self._knowledge_base[storage_key].get("version", 0) + 1
                else:
                    version = 1

                self._knowledge_base[storage_key] = {
                    "data": data,
                    "version": version,
                    "created_at": now,
                    "updated_at": now,
                    "user_id_hash": user_id_hash,
                }

            self._log_audit("store", key, user_id_hash, True)

            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics["query_latency_sum"] += latency

            return json.dumps({
                "status": "success",
                "key": key,
                "layer": layer,
                "latency_ms": latency,
            })

        except Exception as e:
            self._log_audit("store", key, user_id_hash, False)
            logger.error(f"Store context failed: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
            })

    async def retrieve_context(
        self,
        key: Optional[str] = None,
        user_id: Optional[str] = None,
        layer: str = "session",
    ) -> str:
        """Retrieve context data"""
        start_time = asyncio.get_event_loop().time()
        self.metrics["total_operations"] += 1

        user_id_hash = self._hash_user_id(user_id) if user_id else None
        storage_key = f"{user_id_hash}:{key}" if user_id_hash and key else key

        try:
            result = None

            if layer == "session":
                # Try cache first
                result = await self._session_cache.get(storage_key)
                if result:
                    self.metrics["cache_hits"] += 1
                else:
                    self.metrics["cache_misses"] += 1

                    # Try Redis if available
                    if not result and self.redis_client:
                        try:
                            redis_data = await self.redis_client.get(
                                f"session:{storage_key}"
                            )
                            if redis_data:
                                result = {"data": json.loads(redis_data)}
                        except Exception as e:
                            logger.warning(f"Redis retrieve failed: {e}")

            elif layer == "historical":
                if storage_key in self._historical_store:
                    entries = self._historical_store[storage_key]
                    result = {
                        "entries": entries[-100:],  # Last 100
                        "total_count": len(entries),
                    }

            elif layer == "knowledge":
                if storage_key in self._knowledge_base:
                    result = self._knowledge_base[storage_key]

            self._log_audit("retrieve", key or "all", user_id_hash, result is not None)

            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics["query_latency_sum"] += latency

            return json.dumps({
                "status": "success" if result else "not_found",
                "data": result,
                "key": key,
                "layer": layer,
                "latency_ms": latency,
            })

        except Exception as e:
            self._log_audit("retrieve", key or "all", user_id_hash, False)
            logger.error(f"Retrieve context failed: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
            })

    async def query_history(
        self,
        user_id: Optional[str] = None,
        intent: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> str:
        """Query historical command data"""
        self.metrics["total_operations"] += 1

        results = []
        user_id_hash = self._hash_user_id(user_id) if user_id else None

        try:
            # Parse time filters
            start_dt = datetime.fromisoformat(start_time) if start_time else None
            end_dt = datetime.fromisoformat(end_time) if end_time else None

            # Search historical store
            for key, entries in self._historical_store.items():
                for entry in entries:
                    # Filter by user
                    if user_id_hash and entry.get("user_id_hash") != user_id_hash:
                        continue

                    # Filter by intent
                    if intent and entry.get("data", {}).get("intent") != intent:
                        continue

                    # Filter by time
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    if start_dt and entry_time < start_dt:
                        continue
                    if end_dt and entry_time > end_dt:
                        continue

                    results.append(entry)

                    if len(results) >= limit:
                        break

                if len(results) >= limit:
                    break

            # Sort by timestamp descending
            results.sort(key=lambda x: x["timestamp"], reverse=True)

            self._log_audit("query_history", f"user:{user_id_hash}", user_id_hash, True)

            return json.dumps({
                "status": "success",
                "results": results[:limit],
                "total_found": len(results),
            })

        except Exception as e:
            logger.error(f"Query history failed: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
            })

    async def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        merge: bool = True,
    ) -> str:
        """Update user preferences"""
        self.metrics["total_operations"] += 1

        user_id_hash = self._hash_user_id(user_id)
        pref_key = f"preferences:{user_id_hash}"

        try:
            existing = {}
            if merge and pref_key in self._knowledge_base:
                existing = self._knowledge_base[pref_key].get("data", {})

            # Merge or replace
            updated_prefs = {**existing, **preferences} if merge else preferences

            await self.store_context(
                key=f"preferences:{user_id}",
                data=updated_prefs,
                layer="knowledge",
                user_id=user_id,
            )

            self._log_audit("update_preferences", pref_key, user_id_hash, True)

            return json.dumps({
                "status": "success",
                "preferences": updated_prefs,
                "merged": merge,
            })

        except Exception as e:
            logger.error(f"Update preferences failed: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
            })

    async def store_pattern(
        self,
        pattern_type: str,
        pattern_data: Dict[str, Any],
        confidence: float = 1.0,
    ) -> str:
        """Store a learned pattern in knowledge base"""
        self.metrics["total_operations"] += 1

        pattern_id = f"{pattern_type}:{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            pattern_entry = {
                "pattern_type": pattern_type,
                "data": pattern_data,
                "confidence": confidence,
                "created_at": datetime.now().isoformat(),
            }

            self._knowledge_base[pattern_id] = {
                "data": pattern_entry,
                "version": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            self._log_audit("store_pattern", pattern_id, None, True)

            return json.dumps({
                "status": "success",
                "pattern_id": pattern_id,
                "pattern_type": pattern_type,
            })

        except Exception as e:
            logger.error(f"Store pattern failed: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
            })

    async def query_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> str:
        """Query knowledge base for patterns"""
        self.metrics["total_operations"] += 1

        results = []

        try:
            for key, entry in self._knowledge_base.items():
                data = entry.get("data", {})

                # Filter by pattern type
                if pattern_type and data.get("pattern_type") != pattern_type:
                    continue

                # Filter by confidence
                if data.get("confidence", 0) < min_confidence:
                    continue

                results.append({
                    "pattern_id": key,
                    **data,
                })

                if len(results) >= limit:
                    break

            # Sort by confidence descending
            results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

            return json.dumps({
                "status": "success",
                "patterns": results[:limit],
                "total_found": len(results),
            })

        except Exception as e:
            logger.error(f"Query patterns failed: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
            })

    async def get_context_metrics(self) -> str:
        """Get context manager metrics"""
        total_ops = self.metrics["total_operations"]
        cache_total = self.metrics["cache_hits"] + self.metrics["cache_misses"]

        return json.dumps({
            "total_operations": total_ops,
            "cache_hits": self.metrics["cache_hits"],
            "cache_misses": self.metrics["cache_misses"],
            "cache_hit_rate": (
                self.metrics["cache_hits"] / cache_total
                if cache_total > 0 else 0.0
            ),
            "storage_operations": self.metrics["storage_operations"],
            "average_latency_ms": (
                self.metrics["query_latency_sum"] / total_ops
                if total_ops > 0 else 0.0
            ),
            "knowledge_base_size": len(self._knowledge_base),
            "historical_keys": len(self._historical_store),
            "audit_log_size": len(self._audit_log),
        })

    async def cleanup_expired(self) -> Dict[str, int]:
        """Cleanup expired data across all layers"""
        cleaned = {
            "session": 0,
            "historical": 0,
        }

        # Clean session cache
        cleaned["session"] = await self._session_cache.clear_expired()

        # Clean historical data older than retention period
        cutoff = datetime.now() - timedelta(days=self.history_retention_days)
        cutoff_str = cutoff.isoformat()

        for key in list(self._historical_store.keys()):
            entries = self._historical_store[key]
            original_count = len(entries)
            self._historical_store[key] = [
                e for e in entries if e["timestamp"] > cutoff_str
            ]
            cleaned["historical"] += original_count - len(self._historical_store[key])

        logger.info(f"Cleanup completed: {cleaned}")
        return cleaned


# Test/demo
if __name__ == "__main__":
    async def main():
        agent = ContextManagerAgent()

        # Test storing context
        result = await agent.store_context(
            key="test_command",
            data={"intent": "play_music", "confidence": 0.95},
            layer="session",
            user_id="user123",
        )
        print("Store result:", result)

        # Test retrieving context
        result = await agent.retrieve_context(
            key="test_command",
            user_id="user123",
            layer="session",
        )
        print("Retrieve result:", result)

        # Test storing pattern
        result = await agent.store_pattern(
            pattern_type="intent_variation",
            pattern_data={"base_intent": "play_music", "variations": ["play", "listen"]},
            confidence=0.88,
        )
        print("Pattern result:", result)

        # Get metrics
        metrics = await agent.get_context_metrics()
        print("Metrics:", metrics)

    asyncio.run(main())
