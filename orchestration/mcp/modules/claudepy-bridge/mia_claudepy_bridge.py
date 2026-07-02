"""Claudepy bridge for MIA voice-command orchestration.

This module is intentionally import-light at module load time.  The real
claudepy objects are imported lazily in :meth:`ClaudepyBridge.initialize` so
MIA can still start in environments where the AI backend is not installed.

Routing a MIA voice path through this bridge
--------------------------------------------
The live voice entry point is
``orchestration/mcp/modules/core-orchestrator/enhanced_orchestrator.py``,
in ``EnhancedOrchestrator.handle_enhanced_voice_command(text, ...)``, which
today parses intent with a keyword NLP and dispatches via
``_route_enhanced_command(intent_result, session_context, context)``.

To route that path through claudepy (follow-up PR — core-orchestrator is
deliberately NOT modified here), ``_route_enhanced_command`` (or the
``question_answer`` / low-confidence branch of ``handle_enhanced_voice_command``)
would delegate to::

    result = await self.claudepy_bridge.process_voice_command(
        text,
        context={"session_id": session_id, "intent": intent_result.intent,
                 **(context or {})},
    )
    response = result.response

``ClaudepyBridge`` degrades to a keyword fallback when claudepy is unavailable,
so the orchestrator keeps working even without the AI backend installed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

_DEFAULT_PROMPTS_SERVER = (
    Path.home()
    / "projects/mcp/ai-mcp-monorepo/packages/mcp-prompts/dist/mcp-server-standalone.js"
)
_DEFAULT_PROMPTS_DIR = Path.home() / "projects/mcp/ai-mcp-monorepo/packages/mcp-prompts/data"


class _AsyncPromptClient(Protocol):
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any: ...

    async def __aenter__(self) -> "_AsyncPromptClient": ...

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...


@dataclass
class VoiceCommandResult:
    """Structured result returned to MIA's voice pipeline."""

    response: str
    provider_used: str
    latency_ms: float
    tokens_used: int = 0
    rag_context: List[str] = field(default_factory=list)
    intent: Optional[str] = None
    error: Optional[str] = None


class InMemoryVoiceRAG:
    """Tiny in-memory retriever for recent voice command context.

    H1 only needs a reversible bridge with tests; persistent ChromaDB can be
    swapped in later without changing the bridge API.
    """

    def __init__(self, max_items: int = 100) -> None:
        self.max_items = max_items
        self._items: List[Dict[str, str]] = []

    async def add_interaction(self, command: str, response: str) -> None:
        self._items.append({"command": command, "response": response})
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items :]

    async def retrieve(self, command: str, limit: int = 3) -> List[str]:
        terms = {token for token in command.lower().split() if len(token) > 2}
        scored: List[tuple[int, Dict[str, str]]] = []
        for item in self._items:
            haystack = f"{item['command']} {item['response']}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [f"Q: {item['command']}\nA: {item['response']}" for _, item in scored[:limit]]


class ClaudepyBridge:
    """Route MIA voice commands through claudepy with safe fallback behavior."""

    def __init__(
        self,
        *,
        default_provider: str = "kimi",
        prompts_server: Path | str = _DEFAULT_PROMPTS_SERVER,
        prompts_dir: Path | str = _DEFAULT_PROMPTS_DIR,
        rag: Optional[InMemoryVoiceRAG] = None,
        orchestrator: Optional[Any] = None,
        mcp_prompts: Optional[_AsyncPromptClient] = None,
    ) -> None:
        self.default_provider = default_provider
        self.prompts_server = Path(prompts_server)
        self.prompts_dir = Path(prompts_dir)
        self.rag = rag or InMemoryVoiceRAG()
        self._orchestrator = orchestrator
        self._mcp_prompts = mcp_prompts
        self._owns_mcp_client = False
        self._initialized = orchestrator is not None

    @property
    def initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        """Initialize claudepy provider/orchestrator and mcp-prompts client."""

        if self._initialized:
            return

        try:
            from claudepy.agents import Orchestrator
            from claudepy.mcp import McpClient
            from claudepy.providers import ProviderRegistry, ProviderType
            from claudepy.types import McpServerConfig, TransportKind
        except ImportError as exc:
            logger.warning("claudepy unavailable; using fallback voice processing: %s", exc)
            self._initialized = False
            return

        provider_type = getattr(ProviderType, self.default_provider.upper(), ProviderType.ANTHROPIC)
        provider = ProviderRegistry.create(provider_type)
        self._orchestrator = Orchestrator(provider)

        if self._mcp_prompts is None:
            config = McpServerConfig(
                transport=TransportKind.STDIO,
                command="node",
                args=[str(self.prompts_server)],
                env={"PROMPTS_DIR": str(self.prompts_dir)},
            )
            self._mcp_prompts = McpClient(config)
            await self._mcp_prompts.__aenter__()
            self._owns_mcp_client = True

        self._initialized = True

    async def process_voice_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        use_rag: bool = True,
        use_prompts: bool = True,
    ) -> VoiceCommandResult:
        """Process a transcribed voice command and return a structured result."""

        started = time.perf_counter()
        context = context or {}
        clean_text = text.strip()
        if not clean_text:
            return VoiceCommandResult(
                response="I did not catch a command.",
                provider_used="fallback",
                latency_ms=self._elapsed_ms(started),
                intent="unknown",
            )

        await self.initialize()
        if not self._initialized or self._orchestrator is None:
            return await self._fallback_process(clean_text, context, started)

        try:
            prompt = await self._voice_system_prompt(use_prompts)
            rag_context = await self.rag.retrieve(clean_text) if use_rag else []
            task = self._build_task(clean_text, context, prompt, rag_context)
            raw_response = await self._run_orchestrator(task)
            response_text = self._extract_response_text(raw_response)
            await self.rag.add_interaction(clean_text, response_text)
            return VoiceCommandResult(
                response=response_text,
                provider_used=self.default_provider,
                latency_ms=self._elapsed_ms(started),
                tokens_used=self._extract_tokens(raw_response),
                rag_context=rag_context,
                intent=self._infer_intent(clean_text),
            )
        except Exception as exc:
            logger.exception("claudepy voice processing failed; falling back")
            result = await self._fallback_process(clean_text, context, started)
            result.error = str(exc)
            return result

    async def close(self) -> None:
        if self._owns_mcp_client and self._mcp_prompts is not None:
            await self._mcp_prompts.__aexit__(None, None, None)
        self._initialized = False

    async def _voice_system_prompt(self, use_prompts: bool) -> str:
        default = "You are MIA, a concise voice assistant. Interpret the user command and answer with the action to take."
        if not use_prompts or self._mcp_prompts is None:
            return default
        try:
            result = await self._mcp_prompts.call_tool(
                "get_prompt", {"id": "voice-command-design-principles"}
            )
        except Exception as exc:
            logger.debug("mcp-prompts lookup failed: %s", exc)
            return default
        if isinstance(result, dict):
            return str(result.get("content") or result.get("prompt") or default)
        return default

    def _build_task(
        self,
        text: str,
        context: Dict[str, Any],
        system_prompt: str,
        rag_context: List[str],
    ) -> str:
        parts = [system_prompt, f"Voice command: {text}"]
        if context:
            parts.append(f"Runtime context: {context}")
        if rag_context:
            parts.append("Relevant past voice interactions:\n" + "\n---\n".join(rag_context))
        return "\n\n".join(parts)

    async def _run_orchestrator(self, task: str) -> Any:
        # The real claudepy Orchestrator exposes execute(task, sub_tasks=None);
        # prefer it so the bridge actually reaches claudepy in production. run()/
        # generate() are kept as forward-compatible fallbacks for alternate shims.
        if hasattr(self._orchestrator, "execute"):
            return await self._orchestrator.execute(task)
        if hasattr(self._orchestrator, "run"):
            return await self._orchestrator.run(task=task, provider_type=None)
        if hasattr(self._orchestrator, "generate"):
            return await self._orchestrator.generate(task)
        raise RuntimeError("Unsupported claudepy orchestrator interface")

    async def _fallback_process(
        self, text: str, context: Dict[str, Any], started: float
    ) -> VoiceCommandResult:
        intent = self._infer_intent(text)
        response_by_intent = {
            "smart_home": "I can route that smart-home command.",
            "communication": "I can route that message command.",
            "navigation": "I can route that navigation command.",
            "question_answer": "I can answer that once the AI backend is available.",
        }
        response = response_by_intent.get(intent, f"I heard: {text}")
        await self.rag.add_interaction(text, response)
        return VoiceCommandResult(
            response=response,
            provider_used="fallback",
            latency_ms=self._elapsed_ms(started),
            intent=intent,
        )

    def _infer_intent(self, text: str) -> str:
        lowered = text.lower()
        if any(word in lowered for word in ("light", "thermostat", "temperature", "home")):
            return "smart_home"
        if any(word in lowered for word in ("send", "message", "call", "telegram", "whatsapp")):
            return "communication"
        if any(word in lowered for word in ("navigate", "route", "map", "where")):
            return "navigation"
        if lowered.startswith(("what", "how", "why", "when", "who")):
            return "question_answer"
        return "unknown"

    def _extract_response_text(self, response: Any) -> str:
        if isinstance(response, str):
            return response
        if hasattr(response, "content"):
            return str(response.content)
        if isinstance(response, dict):
            return str(response.get("content") or response.get("response") or response)
        return str(response)

    def _extract_tokens(self, response: Any) -> int:
        usage = getattr(response, "usage", None)
        if usage is not None and hasattr(usage, "total_tokens"):
            return int(usage.total_tokens)
        if isinstance(response, dict):
            usage_dict = response.get("usage") or {}
            if isinstance(usage_dict, dict):
                return int(usage_dict.get("total_tokens", 0) or 0)
        return 0

    def _elapsed_ms(self, started: float) -> float:
        return (time.perf_counter() - started) * 1000
