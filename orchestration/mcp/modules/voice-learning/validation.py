"""
Validation Module for Voice Learning DTOs

Handles:
1. JSON schema validation of LLM outputs
2. Field coercion (string → proper types)
3. Partial data recovery (optional fields)
4. Audit logging of validation failures
5. Field alignment between prompts and DTOs
"""

import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar, Union
from datetime import datetime
from jsonschema import validate, ValidationError, Draft7Validator
import sys
import os

from dtos import (
    MiaVoiceCommandLearningOutput,
    MiaVoiceCommandFailureOutput,
    MiaVoiceCommandPatternOutput,
    MiaVoiceContextAnalyzerOutput,
    MiaVoiceCommandKnowledgeSynthesisOutput,
    ParameterExtractionQuality,
    ContextEffectiveness,
    ConfidenceCalibration,
    FailureClassification,
    LearningValue,
    ImplementationPriority,
    InteractionStatistics,
    CommandFamilyEntry,
    AccuracyMetrics,
    ContextSignalImportance,
    DataSources,
)


# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


T = TypeVar('T')


# ============================================================================
# Field Alignment Specifications
# ============================================================================

FIELD_ALIGNMENT = {
    "mia-voice-command-learning": {
        "success": {"json_field": "success", "type": bool, "required": True},
        "command_pattern_family": {"json_field": "command_pattern_family", "type": str, "required": True},
        "phrasing_variations": {"json_field": "phrasing_variations", "type": list, "required": False},
        "parameter_extraction_quality.success": {"json_field": "parameter_extraction_quality.success", "type": bool},
        "context_effectiveness.signals_used": {"json_field": "context_effectiveness.signals_used", "type": list},
        "failure_root_cause": {"json_field": "failure_root_cause", "type": str, "required": False},
        "next_command_prediction": {"json_field": "next_command_prediction", "type": str, "required": False},
        "learning_priorities": {"json_field": "learning_priorities", "type": list, "required": False},
    },
    "mia-voice-command-failure-analysis": {
        "failure_classification": {"json_field": "failure_classification", "type": str, "required": True,
                                  "enum": ["edge_case", "systematic", "user_specific"]},
        "preventable": {"json_field": "preventable", "type": bool, "required": True},
        "root_causes": {"json_field": "root_causes", "type": list, "required": False},
        "learning_value": {"json_field": "learning_value", "type": str, "required": False,
                          "enum": ["high", "medium", "low"]},
    },
    "mia-voice-command-pattern-synthesis": {
        "summary": {"json_field": "summary", "type": str, "required": True},
        "intent_families": {"json_field": "intent_families", "type": list, "required": False},
        "learning_value": {"json_field": "learning_value", "type": float, "required": False},
        "implementation_priority": {"json_field": "implementation_priority", "type": str, "required": False},
    },
    "mia-voice-context-analyzer": {
        "context_impact_summary": {"json_field": "context_impact_summary", "type": str, "required": True},
        "accuracy_metrics.without_context": {"json_field": "accuracy_metrics.without_context", "type": float},
        "accuracy_metrics.with_full_context": {"json_field": "accuracy_metrics.with_full_context", "type": float},
    },
    "mia-voice-command-knowledge-synthesis": {
        "executive_summary": {"json_field": "executive_summary", "type": str, "required": True},
        "command_family_library": {"json_field": "command_family_library", "type": list, "required": False},
    },
}


# ============================================================================
# Type Coercion Strategies
# ============================================================================

def coerce_bool(value: Any) -> bool:
    """Coerce value to boolean"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on')
    if isinstance(value, (int, float)):
        return bool(value)
    raise ValueError(f"Cannot coerce {value} to bool")


def coerce_float(value: Any) -> float:
    """Coerce value to float"""
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, str):
        # Handle percentage strings like "85%" or "0.85"
        cleaned = value.strip().rstrip('%')
        return float(cleaned) / 100 if '%' in value else float(cleaned)
    raise ValueError(f"Cannot coerce {value} to float")


def coerce_int(value: Any) -> int:
    """Coerce value to integer"""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"Cannot coerce {value} to int")


def coerce_datetime(value: Any) -> datetime:
    """Coerce value to datetime"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Try ISO 8601 format
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                raise ValueError(f"Cannot parse datetime: {value}")
    raise ValueError(f"Cannot coerce {value} to datetime")


def coerce_list(value: Any) -> list:
    """Coerce value to list"""
    if isinstance(value, list):
        return value
    if isinstance(value, (str, tuple)):
        return list(value) if isinstance(value, tuple) else [value]
    return [value]


def coerce_value(value: Any, target_type: Type) -> Any:
    """Generic value coercion helper"""
    if value is None:
        return None

    if target_type == bool:
        return coerce_bool(value)
    elif target_type == float:
        return coerce_float(value)
    elif target_type == int:
        return coerce_int(value)
    elif target_type == datetime:
        return coerce_datetime(value)
    elif target_type == list:
        return coerce_list(value)
    elif target_type == str:
        return str(value)
    elif target_type == dict:
        return dict(value) if isinstance(value, dict) else {}

    return value


# ============================================================================
# JSON Schema Validation
# ============================================================================

def validate_json_schema(prompt_id: str, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validate JSON data against schema"""
    try:
        validate(instance=data, schema=schema)
        logger.debug(f"Schema validation passed for {prompt_id}")
    except ValidationError as e:
        logger.warning(f"Schema validation failed for {prompt_id}: {e.message}")
        # Don't raise - allow partial data recovery


# ============================================================================
# Field Access & Coercion
# ============================================================================

def get_nested_field(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested field from dict using dot notation (e.g., 'accuracy_metrics.without_context')"""
    keys = path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default

    return current


def set_nested_field(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set nested field in dict using dot notation"""
    keys = path.split('.')
    current = data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value


# ============================================================================
# Validation & Parsing
# ============================================================================

def validate_and_parse_json(
    prompt_id: str,
    llm_response: str,
    schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Parse JSON from LLM response with graceful degradation

    Steps:
    1. Parse JSON from LLM response
    2. Validate schema compliance (if schema provided)
    3. Perform semantic validation
    4. Apply field coercions and transformations
    5. Log validation failures

    Args:
        prompt_id: ID of the prompt/tool
        llm_response: Raw string response from LLM
        schema: JSON Schema for validation

    Returns:
        Dictionary of parsed and validated data
    """
    data = {}

    # Step 1: Parse JSON from LLM response
    try:
        data = json.loads(llm_response)
        logger.debug(f"Successfully parsed JSON for {prompt_id}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON for {prompt_id}: {e}")
        # Attempt to extract JSON from malformed response
        data = extract_json_from_text(llm_response)
        if not data:
            raise ValueError(f"Could not extract JSON from LLM response: {llm_response[:200]}")

    # Step 2: Validate schema (if provided)
    if schema:
        try:
            validate_json_schema(prompt_id, data, schema)
        except Exception as e:
            logger.warning(f"Schema validation failed for {prompt_id}: {e}")

    # Step 3: Apply field-level validation and coercion
    validated_data = validate_and_coerce_fields(prompt_id, data)

    # Step 4: Log any issues
    log_validation_result(prompt_id, validated_data)

    return validated_data


def validate_and_coerce_fields(prompt_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and coerce individual fields based on alignment specs"""
    validated = {}
    alignment = FIELD_ALIGNMENT.get(prompt_id, {})

    for dto_field, spec in alignment.items():
        json_field = spec.get("json_field", dto_field)
        field_type = spec.get("type")
        is_required = spec.get("required", False)
        allowed_enum = spec.get("enum")

        # Get value from data
        value = get_nested_field(data, json_field)

        if value is None and not is_required:
            # Optional field - use default
            validated[dto_field] = None
            continue

        if value is None and is_required:
            # Required field missing - log error but don't fail
            logger.warning(f"Required field '{json_field}' missing for {prompt_id}")
            continue

        # Validate enum
        if allowed_enum and value not in allowed_enum:
            logger.warning(f"Field '{json_field}' value '{value}' not in allowed values {allowed_enum}")

        # Coerce type
        try:
            if field_type:
                validated[dto_field] = coerce_value(value, field_type)
            else:
                validated[dto_field] = value
        except ValueError as e:
            logger.warning(f"Type coercion failed for '{json_field}': {e}")
            validated[dto_field] = value  # Keep original if coercion fails

    # Preserve any additional fields from original data
    used_fields = set()
    for spec in alignment.values():
        used_fields.add(spec.get("json_field", ""))

    for key, value in data.items():
        if key not in used_fields:
            validated[key] = value

    return validated


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON object from text that may contain other content"""
    # Find first { and last }
    start = text.find('{')
    end = text.rfind('}')

    if start >= 0 and end > start:
        try:
            json_text = text[start:end+1]
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    return {}


def log_validation_result(prompt_id: str, data: Dict[str, Any]) -> None:
    """Log validation results for audit trail"""
    logger.info(
        f"Validation complete for {prompt_id}: "
        f"{len(data)} fields parsed, "
        f"missing required fields: {len([f for f in FIELD_ALIGNMENT.get(prompt_id, {}).values() if f.get('required') and f.get('json_field') not in data])}"
    )


# ============================================================================
# DTO Instantiation
# ============================================================================

def create_learning_output(data: Dict[str, Any]) -> MiaVoiceCommandLearningOutput:
    """Create MiaVoiceCommandLearningOutput DTO from validated data"""
    # Build nested structures
    param_quality = None
    if data.get("parameter_extraction_quality"):
        pq = data["parameter_extraction_quality"]
        param_quality = ParameterExtractionQuality(
            success=pq.get("success", False),
            issues=pq.get("issues", []),
            confidence=coerce_float(pq.get("confidence", 1.0))
        )

    context_eff = None
    if data.get("context_effectiveness"):
        ce = data["context_effectiveness"]
        context_eff = ContextEffectiveness(
            signals_used=ce.get("signals_used", []),
            improvement_potential=coerce_float(ce.get("improvement_potential", 0.0))
        )

    conf_cal = None
    if data.get("confidence_calibration"):
        cc = data["confidence_calibration"]
        conf_cal = ConfidenceCalibration(
            appropriate=coerce_bool(cc.get("appropriate", False)),
            adjustment=cc.get("adjustment")
        )

    return MiaVoiceCommandLearningOutput(
        success=coerce_bool(data.get("success", False)),
        command_pattern_family=str(data.get("command_pattern_family", "")),
        phrasing_variations=coerce_list(data.get("phrasing_variations", [])),
        parameter_extraction_quality=param_quality,
        context_effectiveness=context_eff,
        confidence_calibration=conf_cal,
        failure_root_cause=data.get("failure_root_cause"),
        user_adaptation_insights=data.get("user_adaptation_insights", {}),
        next_command_prediction=data.get("next_command_prediction"),
        learning_priorities=coerce_list(data.get("learning_priorities", [])),
        recommendations_for_improvement=coerce_list(data.get("recommendations_for_improvement", [])),
        extracted_at=datetime.now(),
    )


def create_failure_output(data: Dict[str, Any]) -> MiaVoiceCommandFailureOutput:
    """Create MiaVoiceCommandFailureOutput DTO from validated data"""
    classification_str = str(data.get("failure_classification", "edge_case")).lower()
    try:
        classification = FailureClassification(classification_str)
    except ValueError:
        classification = FailureClassification.EDGE_CASE
        logger.warning(f"Invalid failure classification: {data.get('failure_classification')}")

    learning_value_str = str(data.get("learning_value", "medium")).lower()
    try:
        learning_value = LearningValue(learning_value_str)
    except ValueError:
        learning_value = LearningValue.MEDIUM

    return MiaVoiceCommandFailureOutput(
        failure_classification=classification,
        preventable=coerce_bool(data.get("preventable", False)),
        root_causes=coerce_list(data.get("root_causes", [])),
        pattern_discovery=data.get("pattern_discovery"),
        prevention_strategy=data.get("prevention_strategy"),
        learning_value=learning_value,
        follow_up_actions=coerce_list(data.get("follow_up_actions", [])),
        analyzed_at=datetime.now(),
    )


def create_pattern_output(data: Dict[str, Any]) -> MiaVoiceCommandPatternOutput:
    """Create MiaVoiceCommandPatternOutput DTO from validated data"""
    # Build InteractionStatistics
    stats_data = data.get("interaction_statistics", {})
    stats = InteractionStatistics(
        total_analyzed=int(stats_data.get("total_analyzed", 0)),
        success_rate=coerce_float(stats_data.get("success_rate", 0.0)),
        average_confidence=coerce_float(stats_data.get("average_confidence", 0.0)),
        user_satisfaction_avg=stats_data.get("user_satisfaction_avg"),
        unique_intents=int(stats_data.get("unique_intents", 0)),
        unique_users=int(stats_data.get("unique_users", 0)),
    )

    # Build CommandFamilyEntry list
    families = []
    for family_data in data.get("intent_families", []):
        family = CommandFamilyEntry(
            intent=str(family_data.get("intent", "")),
            success_rate=coerce_float(family_data.get("success_rate", 0.0)),
            variations=coerce_list(family_data.get("variations", [])),
            keyword_patterns=family_data.get("keyword_patterns", {}),
            parameters=coerce_list(family_data.get("parameters", [])),
            context_dependency=str(family_data.get("context_dependency", "none")),
            confidence_threshold_recommended=coerce_float(family_data.get("confidence_threshold_recommended", 0.8)),
            common_failures=coerce_list(family_data.get("common_failures", [])),
            user_satisfaction=coerce_float(family_data.get("user_satisfaction", 0.0)),
        )
        families.append(family)

    priority_str = str(data.get("implementation_priority", "medium")).lower()
    try:
        priority = ImplementationPriority(priority_str)
    except ValueError:
        priority = ImplementationPriority.MEDIUM

    return MiaVoiceCommandPatternOutput(
        summary=str(data.get("summary", "")),
        interaction_statistics=stats,
        intent_families=families,
        parameter_extraction_rules=coerce_list(data.get("parameter_extraction_rules", [])),
        context_effectiveness_analysis=data.get("context_effectiveness_analysis", {}),
        failure_pattern_analysis=coerce_list(data.get("failure_pattern_analysis", [])),
        personalization_opportunities=coerce_list(data.get("personalization_opportunities", [])),
        command_sequence_patterns=coerce_list(data.get("command_sequence_patterns", [])),
        recommended_improvements=coerce_list(data.get("recommended_improvements", [])),
        confidence_calibration_analysis=data.get("confidence_calibration_analysis", {}),
        next_steps=coerce_list(data.get("next_steps", [])),
        learning_value=coerce_float(data.get("learning_value", 0.0)),
        implementation_priority=priority,
        synthesized_at=datetime.now(),
    )


def create_context_output(data: Dict[str, Any]) -> MiaVoiceContextAnalyzerOutput:
    """Create MiaVoiceContextAnalyzerOutput DTO from validated data"""
    # Build AccuracyMetrics
    metrics_data = data.get("accuracy_metrics", {})
    metrics = AccuracyMetrics(
        without_context=coerce_float(metrics_data.get("without_context", 0.0)),
        with_partial_context=coerce_float(metrics_data.get("with_partial_context", 0.0)),
        with_full_context=coerce_float(metrics_data.get("with_full_context", 0.0)),
        context_improvement_percentage=coerce_float(metrics_data.get("context_improvement_percentage", 0.0)),
    )

    # Build ContextSignalImportance list
    signal_importance = []
    for signal_data in data.get("context_signal_importance", []):
        signal = ContextSignalImportance(
            signal=str(signal_data.get("signal", "")),
            value_score=coerce_float(signal_data.get("value_score", 0.0)),
            improvement_impact=coerce_float(signal_data.get("improvement_impact", 0.0)),
            availability=str(signal_data.get("availability", "sometimes")),
        )
        signal_importance.append(signal)

    return MiaVoiceContextAnalyzerOutput(
        context_impact_summary=str(data.get("context_impact_summary", "")),
        accuracy_metrics=metrics,
        context_signal_importance=signal_importance,
        intent_context_mapping=coerce_list(data.get("intent_context_mapping", [])),
        parameter_inference_rules=coerce_list(data.get("parameter_inference_rules", [])),
        confidence_adjustment_rules=coerce_list(data.get("confidence_adjustment_rules", [])),
        location_patterns=data.get("location_patterns", {}),
        time_patterns=data.get("time_patterns", {}),
        missing_context_analysis=data.get("missing_context_analysis", {}),
        recommendations=coerce_list(data.get("recommendations", [])),
        next_actions=coerce_list(data.get("next_actions", [])),
        analyzed_at=datetime.now(),
    )


def create_synthesis_output(data: Dict[str, Any]) -> MiaVoiceCommandKnowledgeSynthesisOutput:
    """Create MiaVoiceCommandKnowledgeSynthesisOutput DTO from validated data"""
    # Build DataSources
    sources_data = data.get("data_sources", {})
    sources = DataSources(
        total_interactions_analyzed=int(sources_data.get("total_interactions_analyzed", 0)),
        time_period=sources_data.get("time_period"),
        users_represented=int(sources_data.get("users_represented", 0)),
        devices_represented=int(sources_data.get("devices_represented", 0)),
        baseline_accuracy=coerce_float(sources_data.get("baseline_accuracy", 0.0)),
    )

    return MiaVoiceCommandKnowledgeSynthesisOutput(
        executive_summary=str(data.get("executive_summary", "")),
        synthesis_timestamp=coerce_datetime(data.get("synthesis_timestamp", datetime.now().isoformat())),
        data_sources=sources,
        command_family_library=coerce_list(data.get("command_family_library", [])),
        intent_recognition_rules=coerce_list(data.get("intent_recognition_rules", [])),
        failure_prevention_strategy=coerce_list(data.get("failure_prevention_strategy", [])),
        context_enhancement_plan=coerce_list(data.get("context_enhancement_plan", [])),
        personalization_framework=data.get("personalization_framework", {}),
        improvement_roadmap=coerce_list(data.get("improvement_roadmap", [])),
        metrics_and_monitoring=data.get("metrics_and_monitoring", {}),
        implementation_checklist=coerce_list(data.get("implementation_checklist", [])),
        risk_assessment=coerce_list(data.get("risk_assessment", [])),
        success_criteria=coerce_list(data.get("success_criteria", [])),
        next_synthesis_trigger=data.get("next_synthesis_trigger"),
        continuous_improvement_loop=data.get("continuous_improvement_loop", {}),
    )
