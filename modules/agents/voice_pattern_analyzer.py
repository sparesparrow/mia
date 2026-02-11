"""
Voice Pattern Analyzer Agent

Detects variations in voice commands, identifies user preferences, recognizes
successful patterns, and extracts linguistic features.

Role: Voice Command Pattern Detection
Parent System: learning_loop_orchestrator
"""

import asyncio
import json
import logging
import re
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_framework import MCPServer, Tool

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of patterns"""
    LINGUISTIC = "linguistic"       # Synonyms, phrasings, filler words
    BEHAVIORAL = "behavioral"       # Sequences, time-based, context-based
    ACOUSTIC = "acoustic"           # Pronunciation, speech rate
    SUCCESS = "success"             # High success structures


@dataclass
class CommandSample:
    """A voice command sample for analysis"""
    command_id: str
    voice_text: str
    intent: str
    confidence: float
    parameters: Dict[str, Any]
    success: bool
    user_id: str
    device_type: str
    timestamp: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectedPattern:
    """A detected pattern"""
    pattern_id: str
    pattern_type: PatternType
    pattern_name: str
    description: str
    confidence: float
    examples: List[str]
    frequency: int
    intent: Optional[str] = None
    user_ids: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class LinguisticAnalyzer:
    """Analyzes linguistic patterns in voice commands"""

    def __init__(self):
        # Common filler phrases
        self.filler_patterns = [
            r'\b(um|uh|like|you know|basically|actually|so)\b',
            r'\b(please|can you|could you|would you)\b',
            r'\b(hey|hi|hello)\s+(mia|assistant|there)\b',
        ]

        # Intent synonyms (base to variations)
        self.intent_synonyms = {
            "play_music": ["play", "listen to", "put on", "start", "queue"],
            "stop": ["stop", "pause", "halt", "end", "quit"],
            "volume": ["volume", "louder", "quieter", "turn up", "turn down"],
            "navigation": ["navigate", "directions", "route", "take me", "go to"],
            "climate": ["temperature", "ac", "heat", "cool", "fan", "warm", "cold"],
            "call": ["call", "phone", "dial", "ring"],
        }

    def extract_filler_phrases(self, text: str) -> List[str]:
        """Extract filler phrases from text"""
        fillers = []
        text_lower = text.lower()
        for pattern in self.filler_patterns:
            matches = re.findall(pattern, text_lower)
            fillers.extend(matches)
        return fillers

    def detect_intent_synonyms(
        self,
        samples: List[CommandSample],
    ) -> Dict[str, List[str]]:
        """Detect synonyms used for each intent"""
        intent_words: Dict[str, Counter] = defaultdict(Counter)

        for sample in samples:
            if sample.success:
                words = sample.voice_text.lower().split()
                for word in words:
                    # Check if word is a known synonym
                    for intent, synonyms in self.intent_synonyms.items():
                        if word in synonyms and sample.intent == intent:
                            intent_words[intent][word] += 1

        # Return top synonyms per intent
        result = {}
        for intent, counter in intent_words.items():
            result[intent] = [word for word, _ in counter.most_common(10)]
        return result

    def detect_parameter_phrasings(
        self,
        samples: List[CommandSample],
    ) -> Dict[str, List[str]]:
        """Detect different ways users phrase parameters"""
        param_phrasings: Dict[str, List[str]] = defaultdict(list)

        for sample in samples:
            if sample.success and sample.parameters:
                for param, value in sample.parameters.items():
                    # Extract the phrase around the parameter value
                    if str(value) in sample.voice_text:
                        idx = sample.voice_text.lower().find(str(value).lower())
                        if idx > 0:
                            context = sample.voice_text[max(0, idx-20):idx+len(str(value))+20]
                            param_phrasings[param].append(context)

        return dict(param_phrasings)


class BehavioralAnalyzer:
    """Analyzes behavioral patterns in command usage"""

    def detect_command_sequences(
        self,
        samples: List[CommandSample],
        min_sequence_length: int = 2,
        min_occurrences: int = 3,
    ) -> List[Dict[str, Any]]:
        """Detect common command sequences"""
        # Group by user and sort by time
        user_commands: Dict[str, List[CommandSample]] = defaultdict(list)
        for sample in samples:
            user_commands[sample.user_id].append(sample)

        # Find sequences
        sequences: Counter = Counter()

        for user_id, commands in user_commands.items():
            commands.sort(key=lambda x: x.timestamp)

            # Look at pairs and triples
            for i in range(len(commands) - 1):
                # Pair
                seq = (commands[i].intent, commands[i+1].intent)
                sequences[seq] += 1

                # Triple
                if i < len(commands) - 2:
                    seq = (commands[i].intent, commands[i+1].intent, commands[i+2].intent)
                    sequences[seq] += 1

        # Filter by minimum occurrences
        common_sequences = [
            {"sequence": list(seq), "count": count}
            for seq, count in sequences.most_common()
            if count >= min_occurrences and len(seq) >= min_sequence_length
        ]

        return common_sequences

    def detect_time_patterns(
        self,
        samples: List[CommandSample],
    ) -> Dict[str, Dict[str, int]]:
        """Detect time-based usage patterns"""
        patterns = {
            "by_hour": defaultdict(lambda: defaultdict(int)),
            "by_day": defaultdict(lambda: defaultdict(int)),
        }

        for sample in samples:
            try:
                dt = datetime.fromisoformat(sample.timestamp)
                hour = dt.hour
                day = dt.strftime("%A")

                patterns["by_hour"][sample.intent][str(hour)] += 1
                patterns["by_day"][sample.intent][day] += 1
            except Exception:
                continue

        # Convert to regular dicts
        return {
            "by_hour": {k: dict(v) for k, v in patterns["by_hour"].items()},
            "by_day": {k: dict(v) for k, v in patterns["by_day"].items()},
        }

    def detect_context_patterns(
        self,
        samples: List[CommandSample],
    ) -> Dict[str, Dict[str, int]]:
        """Detect context-based patterns"""
        patterns = {
            "by_device": defaultdict(lambda: defaultdict(int)),
            "by_location": defaultdict(lambda: defaultdict(int)),
        }

        for sample in samples:
            patterns["by_device"][sample.intent][sample.device_type] += 1

            location = sample.context.get("location", "unknown")
            patterns["by_location"][sample.intent][location] += 1

        return {
            "by_device": {k: dict(v) for k, v in patterns["by_device"].items()},
            "by_location": {k: dict(v) for k, v in patterns["by_location"].items()},
        }


class SuccessPatternAnalyzer:
    """Analyzes patterns in successful commands"""

    def identify_high_success_structures(
        self,
        samples: List[CommandSample],
        min_samples: int = 5,
    ) -> List[Dict[str, Any]]:
        """Identify command structures with high success rates"""
        # Group by structure (intent + has_parameters)
        structures: Dict[str, List[CommandSample]] = defaultdict(list)

        for sample in samples:
            has_params = len(sample.parameters) > 0
            structure = f"{sample.intent}:{'with_params' if has_params else 'no_params'}"
            structures[structure].append(sample)

        # Calculate success rates
        results = []
        for structure, structure_samples in structures.items():
            if len(structure_samples) >= min_samples:
                success_count = sum(1 for s in structure_samples if s.success)
                success_rate = success_count / len(structure_samples)

                if success_rate >= 0.8:  # High success threshold
                    results.append({
                        "structure": structure,
                        "success_rate": success_rate,
                        "sample_count": len(structure_samples),
                        "examples": [s.voice_text for s in structure_samples[:3]],
                    })

        return sorted(results, key=lambda x: -x["success_rate"])

    def identify_optimal_confidence_threshold(
        self,
        samples: List[CommandSample],
    ) -> Dict[str, float]:
        """Identify optimal confidence thresholds per intent"""
        # Group by intent
        by_intent: Dict[str, List[CommandSample]] = defaultdict(list)
        for sample in samples:
            by_intent[sample.intent].append(sample)

        thresholds = {}

        for intent, intent_samples in by_intent.items():
            if len(intent_samples) < 10:
                continue

            # Find threshold that maximizes accuracy
            best_threshold = 0.5
            best_accuracy = 0.0

            for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
                correct = sum(
                    1 for s in intent_samples
                    if (s.confidence >= threshold) == s.success
                )
                accuracy = correct / len(intent_samples)

                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_threshold = threshold

            thresholds[intent] = best_threshold

        return thresholds


class VoicePatternAnalyzerAgent(MCPServer):
    """
    Voice command pattern detection agent.

    Responsibilities:
    - Detect voice command variations and synonyms
    - Identify user speech patterns and preferences
    - Extract linguistic features from commands
    - Recognize successful command structures
    - Track pronunciation variations
    - Analyze command sequencing patterns
    - Identify multi-turn interaction patterns
    - Detect user preference shifts

    Pattern Types:
    - Linguistic: Intent synonyms, parameter phrasings, context expressions, filler phrases
    - Behavioral: Command sequences, time-based, context-based, user habits
    - Acoustic: Pronunciation variations, speech rate, prosody
    - Success: High success structures, optimal parameters, effective context usage

    Success Metrics:
    - Pattern detection accuracy: >88%
    - Variation coverage: >80%
    - User preference accuracy: >85%
    - Pattern actionability: >75%
    """

    def __init__(
        self,
        name: str = "voice-pattern-analyzer",
        version: str = "1.0.0",
        context_manager: Optional[Any] = None,
        message_bus: Optional[Any] = None,
    ):
        super().__init__(name, version)

        self.context_manager = context_manager
        self.message_bus = message_bus

        # Analyzers
        self._linguistic = LinguisticAnalyzer()
        self._behavioral = BehavioralAnalyzer()
        self._success = SuccessPatternAnalyzer()

        # Pattern storage
        self._detected_patterns: Dict[str, DetectedPattern] = {}
        self._command_samples: List[CommandSample] = []

        # Metrics
        self.metrics = {
            "samples_analyzed": 0,
            "patterns_detected": 0,
            "analyses_run": 0,
        }

        # Register tools
        self._register_tools()

        logger.info(f"VoicePatternAnalyzerAgent initialized: {name} v{version}")

    def _register_tools(self) -> None:
        """Register MCP tools"""

        # Tool 1: Add command sample
        self.add_tool(Tool(
            name="add_command_sample",
            description="Add a command sample for pattern analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {"type": "string"},
                    "voice_text": {"type": "string"},
                    "intent": {"type": "string"},
                    "confidence": {"type": "number"},
                    "parameters": {"type": "object"},
                    "success": {"type": "boolean"},
                    "user_id": {"type": "string"},
                    "device_type": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["command_id", "voice_text", "intent", "success", "user_id"],
            },
            handler=self.add_command_sample,
        ))

        # Tool 2: Detect patterns
        self.add_tool(Tool(
            name="detect_patterns",
            description="Run pattern detection on collected samples",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_types": {"type": "array", "items": {"type": "string"}},
                    "min_samples": {"type": "integer", "default": 10},
                },
            },
            handler=self.detect_patterns,
        ))

        # Tool 3: Get user preferences
        self.add_tool(Tool(
            name="get_user_preferences",
            description="Get detected preferences for a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                },
                "required": ["user_id"],
            },
            handler=self.get_user_preferences,
        ))

        # Tool 4: Get command variations
        self.add_tool(Tool(
            name="get_command_variations",
            description="Get detected variations for an intent",
            inputSchema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                },
                "required": ["intent"],
            },
            handler=self.get_command_variations,
        ))

        # Tool 5: Get detected patterns
        self.add_tool(Tool(
            name="get_detected_patterns",
            description="Get all detected patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {"type": "string"},
                    "min_confidence": {"type": "number", "default": 0.5},
                },
            },
            handler=self.get_detected_patterns,
        ))

        # Tool 6: Analyze command batch
        self.add_tool(Tool(
            name="analyze_command_batch",
            description="Analyze a batch of commands for patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "commands": {"type": "array", "items": {"type": "object"}},
                    "analysis_period": {"type": "string"},
                },
                "required": ["commands"],
            },
            handler=self.analyze_command_batch,
        ))

        # Tool 7: Get pattern metrics
        self.add_tool(Tool(
            name="get_pattern_metrics",
            description="Get pattern analyzer metrics",
            inputSchema={"type": "object", "properties": {}},
            handler=self.get_pattern_metrics,
        ))

        logger.info(f"Registered {len(self.tools)} voice pattern analyzer tools")

    async def add_command_sample(
        self,
        command_id: str,
        voice_text: str,
        intent: str,
        success: bool,
        user_id: str,
        confidence: float = 0.0,
        parameters: Optional[Dict[str, Any]] = None,
        device_type: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a command sample for analysis"""
        sample = CommandSample(
            command_id=command_id,
            voice_text=voice_text,
            intent=intent,
            confidence=confidence,
            parameters=parameters or {},
            success=success,
            user_id=user_id,
            device_type=device_type,
            timestamp=datetime.now().isoformat(),
            context=context or {},
        )

        self._command_samples.append(sample)
        self.metrics["samples_analyzed"] += 1

        # Keep last 10000 samples
        if len(self._command_samples) > 10000:
            self._command_samples = self._command_samples[-10000:]

        return json.dumps({
            "status": "success",
            "command_id": command_id,
            "total_samples": len(self._command_samples),
        })

    async def detect_patterns(
        self,
        pattern_types: Optional[List[str]] = None,
        min_samples: int = 10,
    ) -> str:
        """Run pattern detection on collected samples"""
        self.metrics["analyses_run"] += 1

        if len(self._command_samples) < min_samples:
            return json.dumps({
                "status": "insufficient_data",
                "message": f"Need at least {min_samples} samples, have {len(self._command_samples)}",
            })

        pattern_types = pattern_types or ["linguistic", "behavioral", "success"]
        detected = []
        import uuid

        # Linguistic patterns
        if "linguistic" in pattern_types:
            # Intent synonyms
            synonyms = self._linguistic.detect_intent_synonyms(self._command_samples)
            for intent, words in synonyms.items():
                if len(words) >= 2:
                    pattern = DetectedPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type=PatternType.LINGUISTIC,
                        pattern_name=f"synonyms_{intent}",
                        description=f"Detected {len(words)} synonym variations for {intent}",
                        confidence=0.8,
                        examples=words[:5],
                        frequency=len(words),
                        intent=intent,
                        recommendations=[f"Add synonyms to {intent} recognition: {words}"],
                    )
                    self._detected_patterns[pattern.pattern_id] = pattern
                    detected.append(asdict(pattern))

            # Filler phrases (aggregate across samples)
            all_fillers: Counter = Counter()
            for sample in self._command_samples:
                fillers = self._linguistic.extract_filler_phrases(sample.voice_text)
                all_fillers.update(fillers)

            if all_fillers:
                top_fillers = [f for f, _ in all_fillers.most_common(10)]
                pattern = DetectedPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type=PatternType.LINGUISTIC,
                    pattern_name="common_fillers",
                    description=f"Common filler phrases detected",
                    confidence=0.7,
                    examples=top_fillers,
                    frequency=sum(all_fillers.values()),
                    recommendations=["Consider filtering these filler phrases during processing"],
                )
                self._detected_patterns[pattern.pattern_id] = pattern
                detected.append(asdict(pattern))

        # Behavioral patterns
        if "behavioral" in pattern_types:
            # Command sequences
            sequences = self._behavioral.detect_command_sequences(self._command_samples)
            for seq_data in sequences[:5]:  # Top 5 sequences
                pattern = DetectedPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type=PatternType.BEHAVIORAL,
                    pattern_name=f"sequence_{'-'.join(seq_data['sequence'])}",
                    description=f"Command sequence detected: {' -> '.join(seq_data['sequence'])}",
                    confidence=0.75,
                    examples=[' -> '.join(seq_data['sequence'])],
                    frequency=seq_data['count'],
                    recommendations=["Consider suggesting next command in sequence"],
                )
                self._detected_patterns[pattern.pattern_id] = pattern
                detected.append(asdict(pattern))

            # Time patterns
            time_patterns = self._behavioral.detect_time_patterns(self._command_samples)
            for intent, hour_dist in time_patterns.get("by_hour", {}).items():
                if hour_dist:
                    peak_hour = max(hour_dist.items(), key=lambda x: x[1])
                    pattern = DetectedPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type=PatternType.BEHAVIORAL,
                        pattern_name=f"time_pattern_{intent}",
                        description=f"{intent} peaks at hour {peak_hour[0]}",
                        confidence=0.7,
                        examples=[f"Peak usage at {peak_hour[0]}:00"],
                        frequency=peak_hour[1],
                        intent=intent,
                        recommendations=[f"Optimize {intent} processing during peak hours"],
                    )
                    self._detected_patterns[pattern.pattern_id] = pattern
                    detected.append(asdict(pattern))

        # Success patterns
        if "success" in pattern_types:
            # High success structures
            high_success = self._success.identify_high_success_structures(self._command_samples)
            for struct_data in high_success[:5]:
                pattern = DetectedPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type=PatternType.SUCCESS,
                    pattern_name=f"high_success_{struct_data['structure']}",
                    description=f"High success rate ({struct_data['success_rate']:.0%}) for {struct_data['structure']}",
                    confidence=struct_data['success_rate'],
                    examples=struct_data['examples'],
                    frequency=struct_data['sample_count'],
                    recommendations=["Use this structure as template for training"],
                )
                self._detected_patterns[pattern.pattern_id] = pattern
                detected.append(asdict(pattern))

            # Optimal thresholds
            thresholds = self._success.identify_optimal_confidence_threshold(self._command_samples)
            if thresholds:
                pattern = DetectedPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type=PatternType.SUCCESS,
                    pattern_name="optimal_thresholds",
                    description="Optimal confidence thresholds by intent",
                    confidence=0.85,
                    examples=[f"{k}: {v}" for k, v in thresholds.items()],
                    frequency=len(thresholds),
                    recommendations=[f"Adjust thresholds: {thresholds}"],
                )
                self._detected_patterns[pattern.pattern_id] = pattern
                detected.append(asdict(pattern))

        self.metrics["patterns_detected"] = len(self._detected_patterns)

        return json.dumps({
            "status": "success",
            "patterns_detected": len(detected),
            "patterns": detected,
            "samples_analyzed": len(self._command_samples),
        })

    async def get_user_preferences(self, user_id: str) -> str:
        """Get detected preferences for a user"""
        user_samples = [s for s in self._command_samples if s.user_id == user_id]

        if not user_samples:
            return json.dumps({
                "status": "no_data",
                "user_id": user_id,
            })

        # Analyze user-specific patterns
        preferences = {
            "top_intents": [],
            "preferred_devices": [],
            "common_phrases": [],
            "success_rate": 0.0,
            "avg_confidence": 0.0,
        }

        # Top intents
        intent_counter = Counter(s.intent for s in user_samples)
        preferences["top_intents"] = [{"intent": k, "count": v} for k, v in intent_counter.most_common(5)]

        # Preferred devices
        device_counter = Counter(s.device_type for s in user_samples)
        preferences["preferred_devices"] = [{"device": k, "count": v} for k, v in device_counter.most_common(3)]

        # Success rate
        success_count = sum(1 for s in user_samples if s.success)
        preferences["success_rate"] = success_count / len(user_samples)

        # Average confidence
        preferences["avg_confidence"] = sum(s.confidence for s in user_samples) / len(user_samples)

        # Common phrases/fillers
        all_fillers: Counter = Counter()
        for sample in user_samples:
            fillers = self._linguistic.extract_filler_phrases(sample.voice_text)
            all_fillers.update(fillers)
        preferences["common_phrases"] = [f for f, _ in all_fillers.most_common(5)]

        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "sample_count": len(user_samples),
            "preferences": preferences,
        })

    async def get_command_variations(self, intent: str) -> str:
        """Get detected variations for an intent"""
        intent_samples = [s for s in self._command_samples if s.intent == intent]

        if not intent_samples:
            return json.dumps({
                "status": "no_data",
                "intent": intent,
            })

        # Get unique phrasings
        phrasings = list(set(s.voice_text.lower().strip() for s in intent_samples))

        # Get parameters used
        all_params: Set[str] = set()
        for s in intent_samples:
            all_params.update(s.parameters.keys())

        # Success rate
        success_count = sum(1 for s in intent_samples if s.success)
        success_rate = success_count / len(intent_samples)

        # Synonyms detected
        synonyms = self._linguistic.detect_intent_synonyms(intent_samples)

        return json.dumps({
            "status": "success",
            "intent": intent,
            "sample_count": len(intent_samples),
            "unique_phrasings": len(phrasings),
            "example_phrasings": phrasings[:10],
            "parameters_used": list(all_params),
            "success_rate": success_rate,
            "detected_synonyms": synonyms.get(intent, []),
        })

    async def get_detected_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.5,
    ) -> str:
        """Get all detected patterns"""
        patterns = []

        for pattern in self._detected_patterns.values():
            # Filter by type
            if pattern_type and pattern.pattern_type.value != pattern_type:
                continue

            # Filter by confidence
            if pattern.confidence < min_confidence:
                continue

            patterns.append(asdict(pattern))

        return json.dumps({
            "status": "success",
            "patterns": patterns,
            "total_patterns": len(patterns),
        })

    async def analyze_command_batch(
        self,
        commands: List[Dict[str, Any]],
        analysis_period: Optional[str] = None,
    ) -> str:
        """Analyze a batch of commands for patterns"""
        # Add samples
        for cmd in commands:
            await self.add_command_sample(
                command_id=cmd.get("command_id", str(hash(cmd.get("voice_text", "")))),
                voice_text=cmd.get("voice_text", ""),
                intent=cmd.get("intent", "unknown"),
                confidence=cmd.get("confidence", 0.5),
                parameters=cmd.get("parameters", {}),
                success=cmd.get("success", True),
                user_id=cmd.get("user_id", "unknown"),
                device_type=cmd.get("device_type", "unknown"),
                context=cmd.get("context", {}),
            )

        # Run detection
        result = await self.detect_patterns()

        return result

    async def get_pattern_metrics(self) -> str:
        """Get pattern analyzer metrics"""
        return json.dumps({
            "status": "success",
            "metrics": {
                "samples_analyzed": self.metrics["samples_analyzed"],
                "patterns_detected": self.metrics["patterns_detected"],
                "analyses_run": self.metrics["analyses_run"],
                "current_sample_count": len(self._command_samples),
                "pattern_types": {
                    pt.value: sum(1 for p in self._detected_patterns.values() if p.pattern_type == pt)
                    for pt in PatternType
                },
            },
        })


# Test/demo
if __name__ == "__main__":
    async def main():
        agent = VoicePatternAnalyzerAgent()

        # Add some samples
        commands = [
            {"voice_text": "play some music", "intent": "play_music", "success": True},
            {"voice_text": "play jazz", "intent": "play_music", "success": True},
            {"voice_text": "listen to rock", "intent": "play_music", "success": True},
            {"voice_text": "put on some tunes", "intent": "play_music", "success": False},
            {"voice_text": "navigate to home", "intent": "navigation", "success": True},
            {"voice_text": "take me home", "intent": "navigation", "success": True},
            {"voice_text": "go to work", "intent": "navigation", "success": True},
            {"voice_text": "stop the music", "intent": "stop", "success": True},
            {"voice_text": "pause playback", "intent": "stop", "success": True},
            {"voice_text": "um hey mia play something", "intent": "play_music", "success": True},
        ]

        for i, cmd in enumerate(commands):
            await agent.add_command_sample(
                command_id=f"cmd-{i}",
                user_id="user123",
                **cmd,
            )

        # Detect patterns
        result = await agent.detect_patterns()
        print("Patterns:", json.dumps(json.loads(result), indent=2))

        # Get user preferences
        prefs = await agent.get_user_preferences("user123")
        print("User Preferences:", json.dumps(json.loads(prefs), indent=2))

    asyncio.run(main())
