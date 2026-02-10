# Voice Learning Field Mappings

Complete mapping between LLM prompt output JSON fields and MCP DTO dataclass fields.

## Overview

Each of the 5 voice learning prompts produces JSON output that must be validated, coerced, and hydrated into typed Python dataclasses.

**Field Mapping Pattern**:
```
Prompt JSON field → Validation coercion → DTO dataclass field
```

**Coercion Strategies**:
- Type coercion: String percentages ("85%") → float (0.85)
- Enum validation: Ensures categorical fields match allowed values
- Partial recovery: Optional fields get sensible defaults if missing
- Nested structures: Nested JSON objects → dataclasses or Dict[str, Any]

---

## 1. mia-voice-command-learning

**Purpose**: Extract learning from a single voice command interaction

**LLM Prompt Output** → **DTO: MiaVoiceCommandLearningOutput**

### Core Fields (Typed Spine)

| JSON Field | Type | DTO Field | Type | Coercion | Required |
|---|---|---|---|---|---|
| `success` | bool | `success` | bool | Identity | ✅ YES |
| `command_pattern_family` | string | `command_pattern_family` | str | str() | ✅ YES |
| `phrasing_variations` | array[string] | `phrasing_variations` | List[str] | coerce_list() | ❌ NO |

### Nested Structures (Flexible Edges)

#### parameter_extraction_quality → ParameterExtractionQuality

```json
{
  "success": bool,
  "issues": [string],
  "confidence": float (0.0-1.0)
}
```

| JSON Path | Type | DTO Path | Type | Coercion |
|---|---|---|---|---|
| `parameter_extraction_quality.success` | bool | `parameter_extraction_quality.success` | bool | coerce_bool() |
| `parameter_extraction_quality.issues` | array | `parameter_extraction_quality.issues` | List[str] | coerce_list() |
| `parameter_extraction_quality.confidence` | number \| string | `parameter_extraction_quality.confidence` | float | coerce_float() |

#### context_effectiveness → ContextEffectiveness

```json
{
  "signals_used": [string],
  "improvement_potential": float (0.0-1.0)
}
```

| JSON Path | Type | DTO Path | Type | Coercion |
|---|---|---|---|---|
| `context_effectiveness.signals_used` | array | `context_effectiveness.signals_used` | List[str] | coerce_list() |
| `context_effectiveness.improvement_potential` | number \| string | `context_effectiveness.improvement_potential` | float | coerce_float() |

#### confidence_calibration → ConfidenceCalibration

```json
{
  "appropriate": bool,
  "adjustment": float (optional)
}
```

| JSON Path | Type | DTO Path | Type | Coercion |
|---|---|---|---|---|
| `confidence_calibration.appropriate` | bool | `confidence_calibration.appropriate` | bool | coerce_bool() |
| `confidence_calibration.adjustment` | number \| null | `confidence_calibration.adjustment` | Optional[float] | coerce_float() |

### Flexible Fields (Edges)

| JSON Field | Type | DTO Field | Type | Notes |
|---|---|---|---|---|
| `failure_root_cause` | string \| null | `failure_root_cause` | Optional[str] | Only populated if success=false |
| `user_adaptation_insights` | object | `user_adaptation_insights` | Dict[str, Any] | Flexible structure |
| `next_command_prediction` | string \| null | `next_command_prediction` | Optional[str] | Predicted next intent |
| `learning_priorities` | array[string] | `learning_priorities` | List[str] | High-value areas to focus on |
| `recommendations_for_improvement` | array[string] | `recommendations_for_improvement` | List[str] | Actionable improvements |

### Metadata Fields

| JSON Field | DTO Field | Value | Set By |
|---|---|---|---|
| N/A | `extracted_at` | datetime.now() | Validation code |
| N/A | `interaction_id` | Caller provided | Orchestrator |

### Validation Rules

- **Success/Satisfaction interdependency**: If `success=true`, `satisfaction_score` should be absent
- **Context signals**: `signals_used` should be populated if context improved accuracy
- **Learning priorities**: Should identify 2-5 high-value areas

---

## 2. mia-voice-command-failure-analysis

**Purpose**: Analyze command failures and identify recovery/prevention strategies

**LLM Prompt Output** → **DTO: MiaVoiceCommandFailureOutput**

### Core Fields (Typed Spine)

| JSON Field | Type | DTO Field | Type | Coercion | Required |
|---|---|---|---|---|---|
| `failure_classification` | string enum | `failure_classification` | FailureClassification enum | Enum validation | ✅ YES |
| `preventable` | bool | `preventable` | bool | coerce_bool() | ✅ YES |
| `root_causes` | array[string] | `root_causes` | List[str] | coerce_list() | ❌ NO |

**failure_classification Allowed Values**: `"edge_case"` \| `"systematic"` \| `"user_specific"`

### Nested Structures (Flexible Edges)

#### recovery_strategy → FailureRecoveryStrategy

```json
{
  "clarifying_questions": [string],
  "alternative_interpretations": [string],
  "missing_context_signals": [string]
}
```

All fields optional, coerced to List[str].

#### pattern_discovery → FailurePatternDiscovery

```json
{
  "pattern_name": string | null,
  "frequency": string | null,
  "similar_commands": [string]
}
```

#### user_personalization → UserPersonalizationInsights

```json
{
  "user_specific_rules": [string],
  "preference_learned": string | null
}
```

### Flexible Fields (Edges)

| JSON Field | Type | DTO Field | Type | Notes |
|---|---|---|---|---|
| `improvement_actions` | array[object] | `improvement_actions` | List[ImprovementAction] | Each has action, impact, priority |
| `prevention_strategy` | string \| null | `prevention_strategy` | Optional[str] | How to prevent this failure in future |
| `learning_value` | string enum | `learning_value` | LearningValue enum | "high" \| "medium" \| "low" |
| `follow_up_actions` | array[string] | `follow_up_actions` | List[str] | Actionable next steps |

### Metadata Fields

| JSON Field | DTO Field | Value | Set By |
|---|---|---|---|
| N/A | `analyzed_at` | datetime.now() | Validation code |
| N/A | `failure_id` | Caller provided | Orchestrator |

### Validation Rules

- **failure_classification** must be one of: "edge_case", "systematic", "user_specific"
- **learning_value** must be one of: "high", "medium", "low"
- **preventable** should be true xor recovery_strategy populated (either prevent or recover)

---

## 3. mia-voice-command-pattern-synthesis

**Purpose**: Synthesize patterns from 100+ command interactions

**LLM Prompt Output** → **DTO: MiaVoiceCommandPatternOutput**

### Core Fields (Typed Spine)

| JSON Field | Type | DTO Field | Type | Coercion | Required |
|---|---|---|---|---|---|
| `summary` | string | `summary` | str | str() | ✅ YES |
| `interaction_statistics` | object | `interaction_statistics` | InteractionStatistics | See nested | ❌ NO |
| `intent_families` | array[object] | `intent_families` | List[CommandFamilyEntry] | See nested | ❌ NO |

### Nested Structures (Flexible Edges)

#### interaction_statistics → InteractionStatistics

| JSON Field | Type | DTO Field | Type | Coercion |
|---|---|---|---|---|
| `total_analyzed` | integer | `total_analyzed` | int | int() |
| `success_rate` | number \| string | `success_rate` | float | coerce_float() |
| `average_confidence` | number \| string | `average_confidence` | float | coerce_float() |
| `user_satisfaction_avg` | number \| null | `user_satisfaction_avg` | Optional[float] | coerce_float() |
| `unique_intents` | integer | `unique_intents` | int | int() |
| `unique_users` | integer | `unique_users` | int | int() |

**Validation**: `total_analyzed` should be >= 100 (warning if < 100)

#### intent_families[] → CommandFamilyEntry[]

| JSON Field | Type | DTO Field | Type | Coercion |
|---|---|---|---|---|
| `intent` | string | `intent` | str | str() |
| `success_rate` | number \| string | `success_rate` | float | coerce_float() (0.0-1.0) |
| `variations` | array[string] | `variations` | List[str] | coerce_list() |
| `keyword_patterns` | object | `keyword_patterns` | Dict[str, Any] | Identity |
| `parameters` | array[object] | `parameters` | List[Dict[str, Any]] | coerce_list() |
| `context_dependency` | string | `context_dependency` | str | str() |
| `confidence_threshold_recommended` | number \| string | `confidence_threshold_recommended` | float | coerce_float() (0.0-1.0) |
| `common_failures` | array[string] | `common_failures` | List[str] | coerce_list() |
| `user_satisfaction` | number \| string | `user_satisfaction` | float | coerce_float() (1.0-5.0) |

### Flexible Fields (Edges)

All of these are Dict[str, Any] - flexible structure for extensibility:

| JSON Field | DTO Field | Notes |
|---|---|---|
| `parameter_extraction_rules` | `parameter_extraction_rules` | Array of extraction rule objects |
| `context_effectiveness_analysis` | `context_effectiveness_analysis` | Context signal importance mapping |
| `failure_pattern_analysis` | `failure_pattern_analysis` | Failure patterns and frequencies |
| `personalization_opportunities` | `personalization_opportunities` | User segment patterns |
| `command_sequence_patterns` | `command_sequence_patterns` | Multi-command sequences |
| `recommended_improvements` | `recommended_improvements` | Prioritized improvements |
| `confidence_calibration_analysis` | `confidence_calibration_analysis` | Confidence threshold analysis |
| `next_steps` | `next_steps` | List[str] - Recommended next actions |

### Metadata Fields

| JSON Field | DTO Field | Type | Set By |
|---|---|---|---|
| `learning_value` | `learning_value` | float (0.0-1.0) | LLM |
| `implementation_priority` | `implementation_priority` | ImplementationPriority enum | LLM |
| N/A | `synthesized_at` | datetime | Validation code |
| N/A | `analysis_id` | Optional[str] | Orchestrator |

### Validation Rules

- `total_analyzed` should be >= 10 (warning), >= 100 (recommended)
- `success_rate` must be in [0.0, 1.0]
- `confidence_threshold_recommended` must be in [0.0, 1.0]
- `user_satisfaction` (if present) should be in [1.0, 5.0]

---

## 4. mia-voice-context-analyzer

**Purpose**: Analyze how context signals improve command interpretation

**LLM Prompt Output** → **DTO: MiaVoiceContextAnalyzerOutput**

### Core Fields (Typed Spine)

| JSON Field | Type | DTO Field | Type | Coercion | Required |
|---|---|---|---|---|---|
| `context_impact_summary` | string | `context_impact_summary` | str | str() | ✅ YES |
| `accuracy_metrics` | object | `accuracy_metrics` | AccuracyMetrics | See nested | ❌ NO |
| `context_signal_importance` | array[object] | `context_signal_importance` | List[ContextSignalImportance] | See nested | ❌ NO |

### Nested Structures (Flexible Edges)

#### accuracy_metrics → AccuracyMetrics

| JSON Field | Type | DTO Field | Type | Coercion | Validation |
|---|---|---|---|---|---|
| `without_context` | number \| string | `without_context` | float | coerce_float() | [0.0-1.0] |
| `with_partial_context` | number \| string | `with_partial_context` | float | coerce_float() | [0.0-1.0] |
| `with_full_context` | number \| string | `with_full_context` | float | coerce_float() | [0.0-1.0] |
| `context_improvement_percentage` | number \| string | `context_improvement_percentage` | float | coerce_float() | [0.0-100.0] |

**Cross-field validation**: `without_context <= with_partial_context <= with_full_context`

#### context_signal_importance[] → ContextSignalImportance[]

| JSON Field | Type | DTO Field | Type | Coercion |
|---|---|---|---|---|
| `signal` | string | `signal` | str | str() |
| `value_score` | number \| string | `value_score` | float | coerce_float() (0.0-1.0) |
| `improvement_impact` | number \| string | `improvement_impact` | float | coerce_float() (0.0-1.0) |
| `availability` | string | `availability` | str | Enum: "always" \| "sometimes" \| "rare" |

### Flexible Fields (Edges)

All Dict[str, Any]:

| JSON Field | DTO Field | Structure |
|---|---|---|
| `intent_context_mapping` | `intent_context_mapping` | Per-intent context dependency rules |
| `parameter_inference_rules` | `parameter_inference_rules` | How to infer parameters from context |
| `confidence_adjustment_rules` | `confidence_adjustment_rules` | Confidence calibration based on context |
| `location_patterns` | `location_patterns` | Location-specific patterns (home, car, office, etc) |
| `time_patterns` | `time_patterns` | Time-specific patterns (morning, afternoon, evening, night) |
| `missing_context_analysis` | `missing_context_analysis` | Missing signals and how to infer them |
| `recommendations` | `recommendations` | List[Dict] of context improvement recommendations |
| `next_actions` | `next_actions` | List[str] of suggested next steps |

### Metadata Fields

| JSON Field | DTO Field | Value | Set By |
|---|---|---|---|
| N/A | `analyzed_at` | datetime.now() | Validation code |
| N/A | `analysis_id` | Caller provided | Orchestrator |

### Validation Rules

- All accuracy metrics must be in [0.0, 1.0]
- `context_improvement_percentage` must be in [0.0, 100.0]
- Must have: `without_context <= with_partial_context <= with_full_context` (monotonic increase)
- Signal importance scores should sum to approximately 1.0 or represent independent importance

---

## 5. mia-voice-command-knowledge-synthesis

**Purpose**: Synthesize all learning into comprehensive improvement strategies

**LLM Prompt Output** → **DTO: MiaVoiceCommandKnowledgeSynthesisOutput**

### Core Fields (Typed Spine)

| JSON Field | Type | DTO Field | Type | Coercion | Required |
|---|---|---|---|---|---|
| `executive_summary` | string | `executive_summary` | str | str() | ✅ YES |
| `synthesis_timestamp` | string (ISO8601) | `synthesis_timestamp` | datetime | coerce_datetime() | ❌ NO |
| `data_sources` | object | `data_sources` | DataSources | See nested | ❌ NO |

### Nested Structures (Flexible Edges)

#### data_sources → DataSources

| JSON Field | Type | DTO Field | Type | Coercion |
|---|---|---|---|---|
| `total_interactions_analyzed` | integer | `total_interactions_analyzed` | int | int() |
| `time_period` | string \| null | `time_period` | Optional[str] | str() |
| `users_represented` | integer | `users_represented` | int | int() |
| `devices_represented` | integer | `devices_represented` | int | int() |
| `baseline_accuracy` | number \| string | `baseline_accuracy` | float | coerce_float() (0.0-1.0) |

#### command_family_library[] → CommandFamilyEntry[]

Each entry in the library is a command family definition:

```json
{
  "family_name": "string",
  "canonical_intent": "string",
  "variations": ["string"],
  "recognition_confidence": 0.0-1.0,
  "success_rate": 0.0-1.0,
  "average_user_satisfaction": 1.0-5.0,
  "complexity": "simple|medium|complex",
  "parameters": [object],
  "context_dependency": "none|low|medium|high",
  "common_failures": [string],
  "recognition_rules": [object]
}
```

All fields are Dict[str, Any] (flexible).

### Flexible Fields (Edges)

All Dict[str, Any] - complete flexibility for knowledge structures:

| JSON Field | DTO Field | Content Type |
|---|---|---|
| `intent_recognition_rules` | `intent_recognition_rules` | List[Dict] of matching rules per intent |
| `failure_prevention_strategy` | `failure_prevention_strategy` | List[Dict] of failure modes + prevention |
| `context_enhancement_plan` | `context_enhancement_plan` | List[Dict] of context signal improvements |
| `personalization_framework` | `personalization_framework` | Dict with user segments and custom rules |
| `improvement_roadmap` | `improvement_roadmap` | List[Dict] of phased improvements |
| `metrics_and_monitoring` | `metrics_and_monitoring` | Dict of KPIs and tracking |
| `implementation_checklist` | `implementation_checklist` | List[Dict] of actionable items |
| `risk_assessment` | `risk_assessment` | List[Dict] of risks and mitigations |
| `success_criteria` | `success_criteria` | List[str] of criteria to track |
| `continuous_improvement_loop` | `continuous_improvement_loop` | Dict of feedback and adaptation strategy |

### Metadata Fields

| JSON Field | DTO Field | Type | Set By |
|---|---|---|---|
| `next_synthesis_trigger` | `next_synthesis_trigger` | Optional[str] | LLM |
| N/A | `synthesis_id` | Optional[str] | Orchestrator |

### Validation Rules

- `executive_summary` should be 1-3 paragraphs (200-500 words)
- `total_interactions_analyzed` should match sum from data sources
- `baseline_accuracy` must be in [0.0, 1.0]
- Command family library should reference all major intents discovered

---

## Coercion Helper Functions

All type coercions are implemented in `validation.py`:

### coerce_bool(value)
- Input: bool, str, int, float, any
- Handles: "true", "yes", "1", "on" (case-insensitive)

### coerce_float(value)
- Input: float, int, str, any
- Handles: "0.85", "85%", "0.85", integers
- Range: Typically [0.0, 1.0] but validates per field

### coerce_int(value)
- Input: int, float, str, any
- Returns: Integer representation

### coerce_datetime(value)
- Input: datetime, str (ISO8601), any
- Handles: "2025-01-28T..." with or without timezone

### coerce_list(value)
- Input: list, tuple, str, any
- Returns: List representation

---

## Error Handling Strategy

### Partial Data Recovery

If a required field is missing:
1. Log warning
2. Continue processing (don't fail)
3. Use sensible default for DTO instantiation
4. Set metadata flag if tracking needed

### Type Coercion Failures

If type coercion fails:
1. Log warning with field name and value
2. Keep original value (don't coerce)
3. Continue processing
4. DTO will receive unexpected type (validate if needed)

### Validation Failures

If schema validation fails:
1. Log warning (not error)
2. Attempt field-by-field validation
3. Create DTO with partial data
4. Return best-effort result

---

## Testing Field Mappings

Each mapping should have tests validating:

1. **Happy path**: Valid input → correct DTO
2. **Type coercion**: "85%" → 0.85 float
3. **Enum validation**: Invalid enum value → warning + safe default
4. **Optional fields**: Missing optional field → None or []
5. **Nested structures**: Nested JSON → nested dataclass
6. **Partial data**: Some fields missing → valid DTO with defaults
7. **Extra fields**: Unknown JSON fields → preserved in flexible Dict fields

See `tests/test_field_mappings.py` for comprehensive test cases.

---

## Field Mapping Evolution

As prompt templates evolve:

1. **Version tracking**: Track prompt template version in metadata
2. **Backward compatibility**: New versions should support old callers
3. **Migration helpers**: Provide field mapping for old → new
4. **Documentation**: Update this file when fields change
5. **Testing**: Add tests for new field combinations

---

## Summary

**Typed Spine Strategy**:
- Core fields that define the DTO are strictly typed
- Types are coerced at boundary (JSON → Python)
- Enums ensure categorical fields are valid

**Flexible Edges Strategy**:
- Complex nested structures use Dict[str, Any]
- Allows LLM responses to be unpredictable
- Enables evolution without schema changes

**Coercion Strategy**:
- Happens at JSON parsing boundary
- Handles common format variations (percentages, timestamps)
- Graceful degradation (log warning, continue)

**Validation Strategy**:
- Schema validation first (if schema available)
- Field-level validation second
- Audit log all failures
- Never fail on validation (best-effort recovery)
