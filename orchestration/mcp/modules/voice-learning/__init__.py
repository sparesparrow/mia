"""
Voice Learning Module for MIA

Implements voice command intelligence through 5 MCP tools:
1. analyze_command_learning - Extract learning from single commands
2. analyze_failure - Analyze failures and recovery strategies
3. synthesize_patterns - Synthesize patterns from multiple commands
4. analyze_context_effectiveness - Analyze context impact
5. synthesize_knowledge - Comprehensive knowledge synthesis

Architecture:
- DTOs: Type-safe data transfer objects with typed spine + flexible edges
- Validation: JSON schema validation with field coercion
- MCP Tools: 5 async tool handlers with LLM integration
- Schemas: JSON schemas for input/output validation
"""

from .dtos import (
    MiaVoiceCommandLearningOutput,
    MiaVoiceCommandFailureOutput,
    MiaVoiceCommandPatternOutput,
    MiaVoiceContextAnalyzerOutput,
    MiaVoiceCommandKnowledgeSynthesisOutput,
    dto_to_dict,
    dto_to_json,
)

from .validation import (
    validate_and_parse_json,
    validate_and_coerce_fields,
    create_learning_output,
    create_failure_output,
    create_pattern_output,
    create_context_output,
    create_synthesis_output,
)

from .mcp_tools import (
    VoiceLearningToolRegistry,
    AnalyzeCommandLearningHandler,
    AnalyzeCommandFailureHandler,
    SynthesizePatternsHandler,
    AnalyzeContextEffectivenessHandler,
    SynthesizeKnowledgeHandler,
)

__all__ = [
    # DTOs
    "MiaVoiceCommandLearningOutput",
    "MiaVoiceCommandFailureOutput",
    "MiaVoiceCommandPatternOutput",
    "MiaVoiceContextAnalyzerOutput",
    "MiaVoiceCommandKnowledgeSynthesisOutput",
    "dto_to_dict",
    "dto_to_json",
    # Validation
    "validate_and_parse_json",
    "validate_and_coerce_fields",
    "create_learning_output",
    "create_failure_output",
    "create_pattern_output",
    "create_context_output",
    "create_synthesis_output",
    # Tools
    "VoiceLearningToolRegistry",
    "AnalyzeCommandLearningHandler",
    "AnalyzeCommandFailureHandler",
    "SynthesizePatternsHandler",
    "AnalyzeContextEffectivenessHandler",
    "SynthesizeKnowledgeHandler",
]

__version__ = "1.0.0"
