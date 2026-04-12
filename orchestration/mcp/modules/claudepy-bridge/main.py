"""
MIA-Claudepy Bridge

Connects MIA's voice pipeline to claudepy's multi-provider AI orchestrator.
Provides multi-provider fallback, RAG-augmented voice commands, and cost optimization.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class VoiceCommandResult:
    """Result of processing a voice command."""
    response: str
    provider_used: str
    latency_ms: float
    tokens_used: int
    rag_context: Optional[List[str]] = None


class ClaudepyBridge:
    """
    Bridge MIA voice commands to claudepy AI orchestrator.
    
    Features:
    - Multi-provider fallback (Anthropic → Kimi → Gemini)
    - RAG-augmented voice command interpretation
    - Cost optimization via provider routing
    - mcp-prompts integration for voice design patterns
    """

    def __init__(
        self,
        prompts_dir: str = "data",
        chroma_db_path: str = "./chroma_db",
        default_provider: str = "kimi"
    ):
        self.prompts_dir = prompts_dir
        self.chroma_db_path = chroma_db_path
        self.default_provider = default_provider
        
        # These will be initialized on first use
        self._provider = None
        self._orchestrator = None
        self._retriever = None
        self._rag = None
        self._mcp_prompts = None
        self._initialized = False

    async def initialize(self):
        """Lazy initialization of claudepy components."""
        if self._initialized:
            return

        try:
            from claudepy.providers import ProviderRegistry, ProviderType
            from claudepy.agents import Orchestrator
            from claudepy.rag import RAGPipeline, ChromaRetriever
            from claudepy.types import McpServerConfig, TransportKind
            from claudepy.mcp import McpClient

            # Initialize provider
            provider_type = getattr(ProviderType, self.default_provider.upper(), ProviderType.ANTHROPIC)
            self._provider = ProviderRegistry.create(provider_type)
            
            # Initialize orchestrator
            self._orchestrator = Orchestrator(self._provider)
            
            # Initialize RAG
            self._retriever = ChromaRetriever(persist_directory=self.chroma_db_path)
            self._rag = RAGPipeline(self._retriever, self._provider)
            
            # Initialize mcp-prompts client
            config = McpServerConfig(
                transport=TransportKind.STDIO,
                command="node",
                args=["dist/mcp-server-standalone.js"],
                env={"PROMPTS_DIR": self.prompts_dir}
            )
            self._mcp_prompts = McpClient(config)
            await self._mcp_prompts.__aenter__()
            
            self._initialized = True
            logger.info("ClaudepyBridge initialized successfully")
            
        except ImportError as e:
            logger.warning(f"claudepy not available: {e}. Bridge will operate in fallback mode.")
            self._initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize ClaudepyBridge: {e}")
            self._initialized = False
            raise

    async def process_voice_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        use_rag: bool = True,
        use_prompts: bool = True
    ) -> VoiceCommandResult:
        """
        Process a voice command through claudepy orchestrator.
        
        Args:
            text: The transcribed voice command
            context: Optional context (session_id, user_id, location, etc.)
            use_rag: Whether to use RAG retrieval
            use_prompts: Whether to use mcp-prompts for design patterns
            
        Returns:
            VoiceCommandResult with response and metadata
        """
        import time
        start_time = time.time()
        
        context = context or {}
        
        # Initialize if needed
        if not self._initialized:
            await self.initialize()
        
        # Fallback mode if claudepy not available
        if not self._initialized:
            return await self._fallback_process(text, context)
        
        try:
            from claudepy.types import LLMMessage
            
            # 1. Get voice design prompt from mcp-prompts
            system_content = "You are MIA, a helpful voice assistant."
            if use_prompts:
                try:
                    design_prompt = await self._mcp_prompts.call_tool("get_prompt", {
                        "id": "voice-command-design-principles"
                    })
                    if design_prompt and "content" in design_prompt:
                        system_content = design_prompt["content"]
                except Exception as e:
                    logger.warning(f"Failed to get design prompt: {e}")
            
            # 2. RAG: retrieve similar past commands
            rag_context = []
            if use_rag:
                try:
                    rag_result = await self._rag.query(
                        f"Voice command similar to: {text}",
                        top_k=3
                    )
                    rag_context = rag_result.context_used if hasattr(rag_result, 'context_used') else []
                except Exception as e:
                    logger.warning(f"RAG query failed: {e}")
            
            # 3. Build messages
            context_str = f"Context: {context}\n"
            if rag_context:
                context_str += f"Similar past commands: {rag_context}\n"
            
            messages = [
                LLMMessage(role="system", content=system_content),
                LLMMessage(role="user", content=f"{context_str}\nVoice command: {text}")
            ]
            
            # 4. Generate response with routing
            response = await self._orchestrator.generate(messages)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 5. Index this interaction for future RAG
            if use_rag:
                try:
                    await self._retriever.add(
                        texts=[f"Q: {text}\nA: {response.content}"],
                        sources=[f"voice-{context.get('session_id', 'unknown')}"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to index interaction: {e}")
            
            return VoiceCommandResult(
                response=response.content,
                provider_used=self.default_provider,
                latency_ms=latency_ms,
                tokens_used=response.usage.total_tokens if hasattr(response, 'usage') else 0,
                rag_context=rag_context
            )
            
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            # Fallback to simple processing
            return await self._fallback_process(text, context)

    async def _fallback_process(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> VoiceCommandResult:
        """Fallback processing when claudepy is not available."""
        import time
        start_time = time.time()
        
        # Simple echo/acknowledgment fallback
        response_text = f"I heard: {text}"
        
        # Simple intent matching
        text_lower = text.lower()
        if any(word in text_lower for word in ["lights", "light"]):
            if any(word in text_lower for word in ["on", "enable"]):
                response_text = "Turning on the lights."
            elif any(word in text_lower for word in ["off", "disable"]):
                response_text = "Turning off the lights."
        elif any(word in text_lower for word in ["weather", "temperature"]):
            response_text = "I'll check the weather for you."
        
        latency_ms = (time.time() - start_time) * 1000
        
        return VoiceCommandResult(
            response=response_text,
            provider_used="fallback",
            latency_ms=latency_ms,
            tokens_used=0,
            rag_context=None
        )

    async def get_voice_patterns(self, pattern_type: str = "all") -> List[Dict[str, Any]]:
        """
        Retrieve voice command patterns from mcp-prompts.
        
        Args:
            pattern_type: Filter by pattern type (e.g., "lighting", "media", "all")
            
        Returns:
            List of voice pattern dictionaries
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized or not self._mcp_prompts:
            logger.warning("Cannot get voice patterns: bridge not initialized")
            return []
        
        try:
            tags = ["mia", pattern_type] if pattern_type != "all" else ["mia"]
            result = await self._mcp_prompts.call_tool("list_prompts", {
                "tags": tags
            })
            return result.get("prompts", [])
        except Exception as e:
            logger.error(f"Failed to get voice patterns: {e}")
            return []

    async def close(self):
        """Clean up resources."""
        if self._mcp_prompts:
            try:
                await self._mcp_prompts.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing mcp-prompts: {e}")
        self._initialized = False

    def __del__(self):
        """Ensure cleanup on deletion."""
        if self._initialized:
            try:
                asyncio.get_event_loop().run_until_complete(self.close())
            except:
                pass
