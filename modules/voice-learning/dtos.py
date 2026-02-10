"""
MIA Voice Learning DTOs - Typed Data Transfer Objects for Voice Command Intelligence

Uses "typed spine + flexible edges" pattern:
- Core fields are strictly typed
- Complex nested structures use Dict[str, Any] for LLM flexibility
- Enums for categorical fields with validation
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, TypedDict
from enum import Enum
from datetime import datetime
import json


# ============================================================================
# Enums for Categorical Fields
# ============================================================================

class FailureClassification(str, Enum):
    """Classification of voice command failure type"""
    EDGE_CASE = "edge_case"
    SYSTEMATIC = "systematic"
    USER_SPECIFIC = "user_specific"


class LearningValue(str, Enum):
    """Value level of learning or pattern"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ImplementationPriority(str, Enum):
    """Priority level for implementation"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplexityLevel(str, Enum):
    """Complexity level of command or pattern"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


# ============================================================================
# DTO 1: MiaVoiceCommandLearningOutput
# Maps: mia-voice-command-learning.json output
# ============================================================================

@dataclass
class ParameterExtractionQuality:
    """Details about parameter extraction success"""
    success: bool
    issues: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ContextEffectiveness:
    """Analysis of context signal impact"""
    signals_used: List[str] = field(default_factory=list)
    improvement_potential: float = 0.0


@dataclass
class ConfidenceCalibration:
    """Confidence score calibration analysis"""
    appropriate: bool
    adjustment: Optional[float] = None


@dataclass
class MiaVoiceCommandLearningOutput:
    """Learning extracted from a single voice command interaction"""

    # Typed spine - core fields
    success: bool
    command_pattern_family: str
    phrasing_variations: List[str] = field(default_factory=list)
    parameter_extraction_quality: Optional[ParameterExtractionQuality] = None
    context_effectiveness: Optional[ContextEffectiveness] = None
    confidence_calibration: Optional[ConfidenceCalibration] = None

    # Flexible edges - complex nested data
    failure_root_cause: Optional[str] = None
    user_adaptation_insights: Dict[str, Any] = field(default_factory=dict)
    next_command_prediction: Optional[str] = None
    learning_priorities: List[str] = field(default_factory=list)
    recommendations_for_improvement: List[str] = field(default_factory=list)

    # Metadata
    extracted_at: Optional[datetime] = None
    interaction_id: Optional[str] = None


# ============================================================================
# DTO 2: MiaVoiceCommandFailureOutput
# Maps: mia-voice-command-failure-analysis.json output
# ============================================================================

@dataclass
class FailureRecoveryStrategy:
    """Strategy for recovering from a command failure"""
    clarifying_questions: List[str] = field(default_factory=list)
    alternative_interpretations: List[str] = field(default_factory=list)
    missing_context_signals: List[str] = field(default_factory=list)


@dataclass
class FailurePatternDiscovery:
    """Discovery of recurring failure patterns"""
    pattern_name: Optional[str] = None
    frequency: Optional[str] = None
    similar_commands: List[str] = field(default_factory=list)


@dataclass
class UserPersonalizationInsights:
    """User-specific learnings from failure"""
    user_specific_rules: List[str] = field(default_factory=list)
    preference_learned: Optional[str] = None


@dataclass
class ImprovementAction:
    """A specific action to improve system"""
    action: str
    impact: Optional[str] = None
    priority: ImplementationPriority = ImplementationPriority.MEDIUM


@dataclass
class MiaVoiceCommandFailureOutput:
    """Analysis of a voice command failure"""

    # Typed spine - core fields
    failure_classification: FailureClassification
    preventable: bool
    root_causes: List[str] = field(default_factory=list)
    recovery_strategy: Optional[FailureRecoveryStrategy] = None

    # Flexible edges
    pattern_discovery: Optional[FailurePatternDiscovery] = None
    improvement_actions: List[ImprovementAction] = field(default_factory=list)
    user_personalization: Optional[UserPersonalizationInsights] = None
    prevention_strategy: Optional[str] = None
    learning_value: LearningValue = LearningValue.MEDIUM
    follow_up_actions: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: Optional[datetime] = None
    failure_id: Optional[str] = None


# ============================================================================
# DTO 3: MiaVoiceCommandPatternOutput
# Maps: mia-voice-command-pattern-synthesis.json output
# ============================================================================

@dataclass
class InteractionStatistics:
    """Statistics about analyzed interactions"""
    total_analyzed: int = 0
    success_rate: float = 0.0
    average_confidence: float = 0.0
    user_satisfaction_avg: Optional[float] = None
    unique_intents: int = 0
    unique_users: int = 0


@dataclass
class CommandFamilyEntry:
    """A recognized command family pattern"""
    intent: str
    success_rate: float = 0.0
    variations: List[str] = field(default_factory=list)
    keyword_patterns: Dict[str, Any] = field(default_factory=dict)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    context_dependency: str = "none"
    confidence_threshold_recommended: float = 0.8
    common_failures: List[str] = field(default_factory=list)
    user_satisfaction: float = 0.0


@dataclass
class MiaVoiceCommandPatternOutput:
    """Synthesized patterns from multiple command interactions"""

    # Typed spine - core fields
    summary: str
    interaction_statistics: InteractionStatistics = field(default_factory=InteractionStatistics)
    intent_families: List[CommandFamilyEntry] = field(default_factory=list)

    # Flexible edges - flexible structure for various patterns
    parameter_extraction_rules: List[Dict[str, Any]] = field(default_factory=list)
    context_effectiveness_analysis: Dict[str, Any] = field(default_factory=dict)
    failure_pattern_analysis: List[Dict[str, Any]] = field(default_factory=list)
    personalization_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    command_sequence_patterns: List[Dict[str, Any]] = field(default_factory=list)
    recommended_improvements: List[Dict[str, Any]] = field(default_factory=list)
    confidence_calibration_analysis: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)

    # Metadata
    learning_value: float = 0.0
    implementation_priority: ImplementationPriority = ImplementationPriority.MEDIUM
    synthesized_at: Optional[datetime] = None
    analysis_id: Optional[str] = None


# ============================================================================
# DTO 4: MiaVoiceContextAnalyzerOutput
# Maps: mia-voice-context-analyzer.json output
# ============================================================================

@dataclass
class AccuracyMetrics:
    """Accuracy measurements with and without context"""
    without_context: float = 0.0
    with_partial_context: float = 0.0
    with_full_context: float = 0.0
    context_improvement_percentage: float = 0.0


@dataclass
class ContextSignalImportance:
    """Importance of a single context signal"""
    signal: str
    value_score: float
    improvement_impact: float
    availability: str = "sometimes"


@dataclass
class MiaVoiceContextAnalyzerOutput:
    """Analysis of context effectiveness in command interpretation"""

    # Typed spine - core fields
    context_impact_summary: str
    accuracy_metrics: AccuracyMetrics = field(default_factory=AccuracyMetrics)
    context_signal_importance: List[ContextSignalImportance] = field(default_factory=list)

    # Flexible edges - flexible context patterns and rules
    intent_context_mapping: List[Dict[str, Any]] = field(default_factory=list)
    parameter_inference_rules: List[Dict[str, Any]] = field(default_factory=list)
    confidence_adjustment_rules: List[Dict[str, Any]] = field(default_factory=list)
    location_patterns: Dict[str, Any] = field(default_factory=dict)
    time_patterns: Dict[str, Any] = field(default_factory=dict)
    missing_context_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: Optional[datetime] = None
    analysis_id: Optional[str] = None


# ============================================================================
# DTO 5: MiaVoiceCommandKnowledgeSynthesisOutput
# Maps: mia-voice-command-knowledge-synthesis.json output
# ============================================================================

@dataclass
class DataSources:
    """Information about analyzed data sources"""
    total_interactions_analyzed: int = 0
    time_period: Optional[str] = None
    users_represented: int = 0
    devices_represented: int = 0
    baseline_accuracy: float = 0.0


@dataclass
class MiaVoiceCommandKnowledgeSynthesisOutput:
    """Comprehensive knowledge synthesis from all learning dimensions"""

    # Typed spine - core fields
    executive_summary: str
    synthesis_timestamp: datetime = field(default_factory=datetime.now)
    data_sources: DataSources = field(default_factory=DataSources)

    # Command family library - typed entries
    command_family_library: List[Dict[str, Any]] = field(default_factory=list)

    # Flexible edges - flexible rules and strategies
    intent_recognition_rules: List[Dict[str, Any]] = field(default_factory=list)
    failure_prevention_strategy: List[Dict[str, Any]] = field(default_factory=list)
    context_enhancement_plan: List[Dict[str, Any]] = field(default_factory=list)
    personalization_framework: Dict[str, Any] = field(default_factory=dict)
    improvement_roadmap: List[Dict[str, Any]] = field(default_factory=list)
    metrics_and_monitoring: Dict[str, Any] = field(default_factory=dict)
    implementation_checklist: List[Dict[str, Any]] = field(default_factory=list)
    risk_assessment: List[Dict[str, Any]] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    # Metadata
    next_synthesis_trigger: Optional[str] = None
    continuous_improvement_loop: Dict[str, Any] = field(default_factory=dict)
    synthesis_id: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def dto_to_dict(dto: Any) -> Dict[str, Any]:
    """Convert a DTO instance to dictionary, handling nested dataclasses"""
    result = {}
    for key, value in asdict(dto).items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, Enum):
            result[key] = value.value
        else:
            result[key] = value
    return result


def dto_to_json(dto: Any) -> str:
    """Convert a DTO instance to JSON string"""
    return json.dumps(dto_to_dict(dto), indent=2)
