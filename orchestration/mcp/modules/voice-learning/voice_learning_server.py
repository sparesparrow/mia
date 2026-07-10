"""
Voice Learning MCP Server

Implements MCPServer subclass that registers and serves 5 voice learning tools
via Model Context Protocol (MCP).

Tools provided:
1. mia_analyze_command_learning - Extract learning from single command
2. mia_analyze_failure - Analyze command failures and recovery
3. mia_synthesize_patterns - Synthesize patterns from multiple commands
4. mia_analyze_context_effectiveness - Analyze context impact on accuracy
5. mia_synthesize_knowledge - Comprehensive knowledge synthesis

Usage:
    server = VoiceLearningServer(
        llm_client=my_llm_client,
        context_manager=my_context_manager
    )
    await server.start(ws_url="ws://orchestrator:8000")
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

# Assuming mcp_framework is available at parent level
import sys
import os
_MODULES_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _MODULES_DIR)
sys.path.insert(0, os.path.join(_MODULES_DIR, "shared"))

from mcp_framework import MCPServer, Tool, MessageType

from mcp_tools import (
    VoiceLearningToolRegistry,
    AnalyzeCommandLearningHandler,
    AnalyzeCommandFailureHandler,
    SynthesizePatternsHandler,
    AnalyzeContextEffectivenessHandler,
    SynthesizeKnowledgeHandler,
)

logger = logging.getLogger(__name__)


class VoiceLearningServer(MCPServer):
    """MCP Server for voice command learning tools"""

    def __init__(
        self,
        name: str = "voice-learning",
        version: str = "1.0.0",
        llm_client: Optional[Any] = None,
        context_manager: Optional[Any] = None,
        schemas_path: str = "schemas.json",
        mcp_prompts_client: Optional[Any] = None,
        mcp_prompts_dir: Optional[str] = None,
    ):
        """
        Initialize Voice Learning MCP Server

        Args:
            name: Server name
            version: Server version
            llm_client: LLM client for prompt processing (optional)
            context_manager: Context manager for storing/retrieving patterns
            schemas_path: Path to JSON schemas file
            mcp_prompts_client: Optional client with call_tool(name, args) for mcp-prompts
            mcp_prompts_dir: Base mcp-prompts prompt directory; defaults to env or local checkout
        """
        super().__init__(name, version)

        self.llm_client = llm_client
        self.context_manager = context_manager
        self.schemas_path = schemas_path
        self.mcp_prompts_client = mcp_prompts_client
        self.mcp_prompts_dir = Path(
            mcp_prompts_dir
            or os.getenv("MIA_MCP_PROMPTS_DIR")
            or "/home/sparrow/projects/mcp/ai-mcp-monorepo/packages/mcp-prompts/data/prompts"
        )
        self.staging_dir = self.mcp_prompts_dir / "staging"
        self.staging_log_path = self.staging_dir / "review-log.jsonl"

        # Initialize tool registry
        self.tool_registry = VoiceLearningToolRegistry(llm_client, schemas_path)

        # Track statistics
        self.stats = {
            "tools_called": 0,
            "errors": 0,
            "last_call": None,
            "call_times": {},  # Per-tool timing
            "published_prompts": 0,
        }

        # Register all tools
        self._register_tools()

        logger.info(f"Voice Learning Server initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register all 5 voice learning tools with MCP server"""

        # Tool 1: Analyze Command Learning
        tool1 = Tool(
            name="mia_analyze_command_learning",
            description="Extract learning signals from a voice command interaction. Analyzes success patterns, identifies user variations, and discovers learning opportunities.",
            inputSchema=self.tool_registry.handlers[
                "mia_analyze_command_learning"
            ].handlers["mia_analyze_command_learning"].LEARNING_INPUT_SCHEMA
            if hasattr(self.tool_registry.handlers["mia_analyze_command_learning"], "handlers")
            else {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "device_type": {"type": "string"},
                    "raw_input": {"type": "string"},
                    "intent": {"type": "string"},
                    "confidence": {"type": "number"},
                    "success": {"type": "boolean"},
                },
                "required": ["user_id", "raw_input", "intent", "success"],
            },
            handler=self._make_handler("mia_analyze_command_learning"),
        )
        self.add_tool(tool1)

        # Tool 2: Analyze Failure
        tool2 = Tool(
            name="mia_analyze_failure",
            description="Analyze voice command failures and misinterpretations. Identifies root causes, recovery strategies, and prevention opportunities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "device_type": {"type": "string"},
                    "raw_input": {"type": "string"},
                    "interpreted_intent": {"type": "string"},
                    "actual_intent": {"type": "string"},
                    "user_clarification": {"type": "string"},
                },
                "required": ["user_id", "raw_input", "interpreted_intent", "actual_intent"],
            },
            handler=self._make_handler("mia_analyze_failure"),
        )
        self.add_tool(tool2)

        # Tool 3: Synthesize Patterns
        tool3 = Tool(
            name="mia_synthesize_patterns",
            description="Synthesize generalizable patterns from multiple voice command interactions. Extracts command families, variations, and improved recognition rules.",
            inputSchema={
                "type": "object",
                "properties": {
                    "interaction_count": {"type": "integer"},
                    "interactions": {"type": "array"},
                    "success_rate": {"type": "number"},
                    "avg_confidence": {"type": "number"},
                    "intent_count": {"type": "integer"},
                    "user_count": {"type": "integer"},
                },
                "required": ["interaction_count", "interactions"],
            },
            handler=self._make_handler("mia_synthesize_patterns"),
        )
        self.add_tool(tool3)

        # Tool 4: Analyze Context Effectiveness
        tool4 = Tool(
            name="mia_analyze_context_effectiveness",
            description="Analyze how context signals (location, time, device state, history) influence command interpretation accuracy.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sample_size": {"type": "integer"},
                    "user_input": {"type": "string"},
                    "intent": {"type": "string"},
                    "raw_confidence": {"type": "number"},
                    "final_confidence": {"type": "number"},
                    "no_context_accuracy": {"type": "number"},
                    "with_full_context": {"type": "number"},
                },
                "required": ["sample_size", "user_input", "intent"],
            },
            handler=self._make_handler("mia_analyze_context_effectiveness"),
        )
        self.add_tool(tool4)

        # Tool 5: Synthesize Knowledge
        tool5 = Tool(
            name="mia_synthesize_knowledge",
            description="Synthesize all learning from voice command analysis into comprehensive improvement strategies and knowledge updates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "learning_insights": {"type": ["object", "array"]},
                    "failure_insights": {"type": ["object", "array"]},
                    "pattern_insights": {"type": ["object", "array"]},
                    "context_insights": {"type": ["object", "array"]},
                    "total_interactions": {"type": "integer"},
                    "baseline_accuracy": {"type": "number"},
                },
                "required": [
                    "learning_insights",
                    "failure_insights",
                    "pattern_insights",
                    "context_insights",
                ],
            },
            handler=self._make_handler("mia_synthesize_knowledge"),
        )
        self.add_tool(tool5)

        logger.info(f"Registered {len(self.tools)} voice learning tools")

    def _make_handler(self, tool_name: str):
        """Create handler wrapper for tool"""

        async def handler(**kwargs) -> str:
            """Wrapped tool handler with timing and statistics tracking"""
            try:
                start_time = asyncio.get_event_loop().time()

                # Call tool via registry
                result = await self.tool_registry.call_tool(tool_name, **kwargs)

                end_time = asyncio.get_event_loop().time()
                elapsed = end_time - start_time

                # Update statistics
                self.stats["tools_called"] += 1
                self.stats["last_call"] = datetime.now().isoformat()
                if tool_name not in self.stats["call_times"]:
                    self.stats["call_times"][tool_name] = []
                self.stats["call_times"][tool_name].append(elapsed)

                logger.info(
                    f"Tool {tool_name} completed in {elapsed:.2f}s "
                    f"(total calls: {self.stats['tools_called']})"
                )

                return result

            except Exception as e:
                logger.error(f"Error in tool {tool_name}: {e}")
                self.stats["errors"] += 1
                raise

        return handler

    async def store_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]) -> None:
        """
        Store discovered pattern in context manager

        Args:
            pattern_type: Type of pattern (learning, failure, sequence, etc)
            pattern_data: Pattern details
        """
        if not self.context_manager:
            logger.warning("Context manager not configured, skipping pattern storage")
            return

        try:
            # Store pattern with metadata
            storage_key = f"voice-pattern:{pattern_type}:{datetime.now().isoformat()}"
            await self.context_manager.store(storage_key, pattern_data)
            logger.info(f"Pattern stored: {storage_key}")
        except Exception as e:
            logger.error(f"Failed to store pattern: {e}")

    async def retrieve_pattern(self, pattern_type: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user-specific pattern from context manager

        Args:
            pattern_type: Type of pattern
            user_id: User identifier

        Returns:
            Pattern data or None if not found
        """
        if not self.context_manager:
            logger.warning("Context manager not configured, returning None")
            return None

        try:
            # Retrieve most recent pattern of this type for user
            patterns = await self.context_manager.query(
                f"voice-pattern:{pattern_type}:*",
                filters={"user_id": user_id},
            )
            if patterns:
                return patterns[0]  # Most recent
        except Exception as e:
            logger.error(f"Failed to retrieve pattern: {e}")

        return None

    @staticmethod
    def _slugify(value: str, fallback: str = "learned-pattern") -> str:
        """Create a stable filesystem-safe slug for staged prompt IDs."""
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug[:80] or fallback

    @staticmethod
    def _pattern_content(pattern: Dict[str, Any]) -> str:
        """Extract human-reviewable prompt content from a learned pattern."""
        for key in ("content", "prompt", "pattern", "summary", "recommendation"):
            value = pattern.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return json.dumps(pattern, indent=2, sort_keys=True)

    def _build_staged_prompt(
        self,
        pattern: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build an mcp-prompts-compatible prompt document for review staging."""
        metadata = metadata or {}
        now = datetime.now().isoformat()
        intent = str(metadata.get("intent") or pattern.get("intent") or "voice-learning")
        source = str(metadata.get("source") or "mia-voice-learning")
        name_seed = str(pattern.get("name") or pattern.get("title") or f"MIA learned pattern: {intent}")
        slug_seed = f"mia-learned-{intent}-{name_seed}"
        prompt_id = self._slugify(slug_seed)

        tags = list(dict.fromkeys([
            "mia",
            "voice-learning",
            "auto-generated",
            "staged",
            "#learned",
            intent,
            *[str(tag) for tag in metadata.get("tags", [])],
        ]))

        return {
            "id": prompt_id,
            "name": name_seed,
            "description": metadata.get(
                "description",
                "Auto-generated MIA voice-learning pattern staged for human review.",
            ),
            "content": self._pattern_content(pattern),
            "isTemplate": bool(metadata.get("isTemplate", False)),
            "variables": metadata.get("variables", []),
            "tags": tags,
            "category": "staging",
            "createdAt": now,
            "updatedAt": now,
            "version": 1,
            "metadata": {
                "source": source,
                "reviewStatus": "staged",
                "reviewInstruction": "Review weekly; promote to data/prompts/ or delete.",
                "origin": "MIA voice-learning feedback loop",
                **{k: v for k, v in metadata.items() if k not in {"tags", "variables", "description", "isTemplate"}},
            },
        }

    async def _call_mcp_prompts_create_prompt(self, prompt: Dict[str, Any]) -> Optional[Any]:
        """Best-effort create_prompt call for injected mcp-prompts clients."""
        if not self.mcp_prompts_client:
            return None

        payload = {
            "name": prompt["name"],
            "content": prompt["content"],
            "category": prompt["category"],
            "tags": prompt["tags"],
            "isTemplate": prompt["isTemplate"],
            "variables": prompt["variables"],
        }
        client = self.mcp_prompts_client
        if hasattr(client, "__aenter__"):
            async with client as active_client:
                return await active_client.call_tool("create_prompt", payload)
        return await client.call_tool("create_prompt", payload)

    async def publish_learned_prompt(
        self,
        pattern: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Publish a learned voice pattern into mcp-prompts staging.

        The staged file is the durable handoff for weekly human review. If an
        mcp-prompts client is injected, the method also calls create_prompt via
        that client; failures are logged but do not block local staging.
        """
        prompt = self._build_staged_prompt(pattern, metadata)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = self.staging_dir / f"{prompt['id']}.json"

        if prompt_path.exists():
            timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
            prompt["id"] = f"{prompt['id']}-{timestamp_suffix}"
            prompt_path = self.staging_dir / f"{prompt['id']}.json"

        prompt_path.write_text(json.dumps(prompt, indent=2, ensure_ascii=False) + "\n")

        mcp_result = None
        mcp_error = None
        try:
            mcp_result = await self._call_mcp_prompts_create_prompt(prompt)
        except Exception as exc:
            mcp_error = str(exc)
            logger.warning("mcp-prompts create_prompt call failed; staged file kept: %s", exc)

        review_record = {
            "timestamp": datetime.now().isoformat(),
            "prompt_id": prompt["id"],
            "path": str(prompt_path),
            "status": "staged",
            "mcp_create_prompt": "ok" if mcp_result is not None else "skipped" if mcp_error is None else "failed",
            "mcp_error": mcp_error,
        }
        with self.staging_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(review_record, ensure_ascii=False) + "\n")

        self.stats["published_prompts"] += 1
        logger.info("Published learned prompt to staging: %s", prompt_path)
        return {**review_record, "prompt": prompt, "mcp_result": mcp_result}

    async def run_learning_cycle(
        self,
        interactions: list,
        user_id: Optional[str] = None,
        sample_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Run complete voice learning cycle: analyze → synthesize → store

        Orchestrates the learning pipeline:
        1. Analyze individual commands for learning
        2. Synthesize patterns from interactions
        3. Analyze failure modes
        4. Analyze context effectiveness
        5. Generate comprehensive knowledge synthesis
        6. Store learned patterns

        Args:
            interactions: List of command interaction objects
            user_id: Filter patterns to user (optional)
            sample_size: Number of interactions to process

        Returns:
            Dictionary with learning cycle results
        """
        logger.info(f"Starting voice learning cycle with {len(interactions)} interactions")

        results = {
            "timestamp": datetime.now().isoformat(),
            "interaction_count": len(interactions),
            "user_id": user_id,
            "learning_results": {},
            "pattern_results": {},
            "failure_results": {},
            "context_results": {},
            "synthesis_results": {},
            "stored_patterns": 0,
            "published_prompts": [],
            "errors": [],
        }

        try:
            # Step 1: Analyze command learning (sample interactions)
            learning_batch = interactions[:sample_size]
            for interaction in learning_batch:
                try:
                    result = await self.tool_registry.call_tool(
                        "mia_analyze_command_learning",
                        user_id=user_id or "unknown",
                        timestamp=interaction.get("timestamp", datetime.now().isoformat()),
                        device_type=interaction.get("device_type", "unknown"),
                        location=interaction.get("location", "unknown"),
                        time_of_day=interaction.get("time_of_day", "unknown"),
                        raw_input=interaction.get("raw_input", ""),
                        intent=interaction.get("intent", ""),
                        confidence=interaction.get("confidence", 0.5),
                        parameters=interaction.get("parameters", {}),
                        success=interaction.get("success", False),
                        satisfaction_score=interaction.get("satisfaction_score"),
                        actual_action=interaction.get("actual_action", ""),
                        previous_intent=interaction.get("previous_intent"),
                        recent_commands=interaction.get("recent_commands", []),
                        device_state=interaction.get("device_state", {}),
                        user_preferences=interaction.get("user_preferences", {}),
                    )
                    results["learning_results"][interaction.get("id")] = json.loads(result)
                except Exception as e:
                    logger.error(f"Learning analysis failed for interaction: {e}")
                    results["errors"].append(f"Learning analysis: {str(e)}")

            # Step 2: Synthesize patterns
            try:
                success_count = sum(
                    1 for i in interactions if i.get("success", False)
                )
                success_rate = success_count / len(interactions) if interactions else 0.0

                pattern_result = await self.tool_registry.call_tool(
                    "mia_synthesize_patterns",
                    interaction_count=len(interactions),
                    interactions=interactions,
                    success_rate=success_rate,
                    avg_confidence=sum(
                        i.get("confidence", 0.5) for i in interactions
                    )
                    / len(interactions)
                    if interactions
                    else 0.0,
                    satisfaction_avg=None,
                    intent_count=len(set(i.get("intent", "unknown") for i in interactions)),
                    user_count=1 if user_id else len(set(i.get("user_id", "unknown") for i in interactions)),
                )
                results["pattern_results"] = json.loads(pattern_result)

                # Store patterns
                await self.store_pattern("synthesis", results["pattern_results"])
                results["stored_patterns"] += 1

            except Exception as e:
                logger.error(f"Pattern synthesis failed: {e}")
                results["errors"].append(f"Pattern synthesis: {str(e)}")

            # Step 3: Analyze context effectiveness
            try:
                context_result = await self.tool_registry.call_tool(
                    "mia_analyze_context_effectiveness",
                    sample_size=len(interactions),
                    user_input="context analysis",
                    intent="analysis",
                    raw_confidence=0.5,
                    final_confidence=0.7,
                    success=True,
                    location="unspecified",
                    time_of_day="unspecified",
                    day_of_week="unspecified",
                    device_state="idle",
                    device_type="unspecified",
                    recent_activities=[],
                    recent_commands=[],
                    recent_count=5,
                    user_profile={},
                    device_capabilities=[],
                    network_status="online",
                    user_schedule=None,
                    ambient_conditions={},
                    no_context_accuracy=0.75,
                    partial_context_accuracy=0.82,
                    full_context_accuracy=0.89,
                )
                results["context_results"] = json.loads(context_result)

                # Store context insights
                await self.store_pattern("context", results["context_results"])
                results["stored_patterns"] += 1

            except Exception as e:
                logger.error(f"Context analysis failed: {e}")
                results["errors"].append(f"Context analysis: {str(e)}")

            # Step 4: Synthesize comprehensive knowledge
            try:
                synthesis_result = await self.tool_registry.call_tool(
                    "mia_synthesize_knowledge",
                    learning_count=len(results["learning_results"]),
                    learning_insights=results["learning_results"],
                    failure_count=len([i for i in interactions if not i.get("success")]),
                    failure_insights={},
                    pattern_sample_size=sample_size,
                    pattern_insights=results["pattern_results"],
                    context_insights=results["context_results"],
                    timestamp=datetime.now().isoformat(),
                    total_interactions=len(interactions),
                    time_period=f"last {len(interactions)} commands",
                    user_count=1 if user_id else len(
                        set(i.get("user_id") for i in interactions if i.get("user_id"))
                    ),
                    device_count=len(set(i.get("device_type") for i in interactions if i.get("device_type"))),
                    baseline_accuracy=success_rate,
                )
                results["synthesis_results"] = json.loads(synthesis_result)

                # Store knowledge synthesis
                await self.store_pattern("knowledge", results["synthesis_results"])
                results["stored_patterns"] += 1

                # Stage learned knowledge for weekly mcp-prompts review (Option C).
                published = await self.publish_learned_prompt(
                    results["synthesis_results"],
                    metadata={
                        "intent": "knowledge-synthesis",
                        "source": "mia_synthesize_knowledge",
                        "user_id": user_id,
                        "interaction_count": len(interactions),
                        "tags": ["knowledge-synthesis", "weekly-review"],
                    },
                )
                results["published_prompts"].append(published)

            except Exception as e:
                logger.error(f"Knowledge synthesis failed: {e}")
                results["errors"].append(f"Knowledge synthesis: {str(e)}")

            logger.info(
                f"Voice learning cycle complete: "
                f"{results['learning_results']} learning analyses, "
                f"{results['stored_patterns']} patterns stored"
            )

        except Exception as e:
            logger.error(f"Learning cycle failed: {e}")
            results["errors"].append(f"Learning cycle: {str(e)}")

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get server statistics"""
        avg_call_time = {}
        for tool_name, times in self.stats["call_times"].items():
            if times:
                avg_call_time[tool_name] = sum(times) / len(times)

        return {
            "name": self.name,
            "version": self.version,
            "initialized": self.initialized,
            "tools_registered": len(self.tools),
            "tools_called": self.stats["tools_called"],
            "errors": self.stats["errors"],
            "last_call": self.stats["last_call"],
            "published_prompts": self.stats["published_prompts"],
            "staging_dir": str(self.staging_dir),
            "average_call_times": avg_call_time,
        }

    async def shutdown(self) -> None:
        """Shutdown server"""
        self.running = False
        logger.info("Voice Learning Server shutting down")
