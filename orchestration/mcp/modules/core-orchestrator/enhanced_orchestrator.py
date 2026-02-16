"""
MIA Universal: Enhanced Core Orchestrator
Advanced MCP host with improved NLP, context management, and UI abstraction
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import aiohttp
import websockets
from pathlib import Path

# Import our MCP framework
from ..shared.mcp_framework import (
    MCPServer, MCPClient, MCPMessage, MCPTransport,
    WebSocketTransport, HTTPTransport, Tool, Prompt, create_tool
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Enhanced service information"""
    name: str
    host: str
    port: int
    capabilities: List[str]
    health_status: str = "unknown"
    last_seen: Optional[datetime] = None
    response_time: float = 0.0
    error_count: int = 0
    service_type: str = "mcp"  # mcp, http, websocket
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UserContext:
    """User context information"""
    user_id: str
    current_location: str = "unknown"
    preferred_language: str = "en"
    timezone: str = "UTC"
    preferences: Dict[str, str] = None
    last_activity: Optional[datetime] = None

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.last_activity is None:
            self.last_activity = datetime.now()


@dataclass
class SessionContext:
    """Session context for conversation state"""
    session_id: str
    user_id: str
    interface_type: str  # voice, text, web, mobile
    created_at: datetime
    last_accessed: datetime
    command_history: List[str] = None
    response_history: List[str] = None
    variables: Dict[str, str] = None
    last_intent: str = ""
    last_parameters: Dict[str, str] = None
    last_used_service: str = ""
    service_state: Dict[str, str] = None

    def __post_init__(self):
        if self.command_history is None:
            self.command_history = []
        if self.response_history is None:
            self.response_history = []
        if self.variables is None:
            self.variables = {}
        if self.last_parameters is None:
            self.last_parameters = {}
        if self.service_state is None:
            self.service_state = {}

    def is_active(self) -> bool:
        """Check if session is still active (within 30 minutes)"""
        return datetime.now() - self.last_accessed < timedelta(minutes=30)


@dataclass
class IntentResult:
    """Result of intent classification"""
    intent: str
    confidence: float
    parameters: Dict[str, str]
    original_text: str
    context_used: bool = False
    alternatives: List[Tuple[str, float]] = None

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []


class EnhancedNLPProcessor:
    """Advanced NLP processor with context awareness and learning"""
    
    def __init__(self):
        self.intent_patterns = self._initialize_patterns()
        self.context_patterns = self._initialize_context_patterns()
        self.parameter_extractors = self._initialize_extractors()
        
    def _initialize_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize intent patterns with weights and context"""
        return {
            "play_music": {
                "keywords": ["play", "music", "song", "track", "album", "artist", "spotify", "youtube", "stream"],
                "weight": 1.0,
                "requires_context": False,
                "context_boost": {"last_intent": ["control_volume", "switch_audio"], "boost": 0.3}
            },
            "control_volume": {
                "keywords": ["volume", "loud", "quiet", "mute", "unmute", "louder", "quieter", "sound"],
                "weight": 1.0,
                "requires_context": False,
                "context_boost": {"last_intent": ["play_music"], "boost": 0.2}
            },
            "switch_audio": {
                "keywords": ["switch", "change", "output", "headphones", "speakers", "bluetooth", "rtsp", "device"],
                "weight": 1.0,
                "requires_context": False,
                "context_boost": {"last_intent": ["play_music", "control_volume"], "boost": 0.2}
            },
            "system_control": {
                "keywords": ["open", "close", "launch", "run", "execute", "kill", "start", "stop", "application"],
                "weight": 1.0,
                "requires_context": False
            },
            "file_operation": {
                "keywords": ["download", "upload", "copy", "move", "delete", "create", "save", "file"],
                "weight": 1.0,
                "requires_context": False
            },
            "smart_home": {
                "keywords": ["lights", "temperature", "thermostat", "lock", "unlock", "dim", "brightness", "home"],
                "weight": 1.0,
                "requires_context": False,
                "context_boost": {"location": ["home", "house"], "boost": 0.3}
            },
            "communication": {
                "keywords": ["send", "call", "message", "text", "email", "whatsapp", "telegram", "notify"],
                "weight": 1.0,
                "requires_context": False
            },
            "navigation": {
                "keywords": ["directions", "navigate", "route", "map", "location", "traffic", "gps", "drive"],
                "weight": 1.0,
                "requires_context": False
            },
            "hardware_control": {
                "keywords": ["gpio", "pin", "sensor", "led", "relay", "pwm", "analog", "digital", "hardware"],
                "weight": 1.0,
                "requires_context": False
            },
            "question_answer": {
                "keywords": ["what", "how", "why", "when", "where", "who", "tell", "explain", "define"],
                "weight": 0.8,
                "requires_context": False
            },
            "follow_up": {
                "keywords": ["yes", "no", "continue", "stop", "again", "repeat", "more", "next", "previous"],
                "weight": 0.5,
                "requires_context": True
            }
        }
    
    def _initialize_context_patterns(self) -> Dict[str, List[str]]:
        """Initialize context-sensitive patterns"""
        return {
            "pronouns": ["it", "that", "this", "them", "they"],
            "relative_references": ["same", "similar", "different", "another", "other"],
            "temporal_references": ["again", "before", "after", "next", "previous", "last"]
        }
    
    def _initialize_extractors(self) -> Dict[str, callable]:
        """Initialize parameter extraction functions"""
        return {
            "play_music": self._extract_music_params,
            "control_volume": self._extract_volume_params,
            "switch_audio": self._extract_audio_params,
            "system_control": self._extract_system_params,
            "hardware_control": self._extract_hardware_params,
            "smart_home": self._extract_home_params,
            "file_operation": self._extract_file_params,
            "navigation": self._extract_navigation_params
        }
    
    async def parse_command(self, text: str, context: Optional[SessionContext] = None) -> IntentResult:
        """Parse command with context awareness"""
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        if not words:
            return IntentResult("unknown", 0.0, {}, text)
        
        # Calculate intent scores
        intent_scores = {}
        context_used = False
        
        for intent, config in self.intent_patterns.items():
            score = self._calculate_intent_score(text_lower, words, intent, config, context)
            if score > 0:
                intent_scores[intent] = score
                
                # Apply context boost if available
                if context and "context_boost" in config:
                    boost_score = self._apply_context_boost(config["context_boost"], context)
                    if boost_score > 0:
                        intent_scores[intent] += boost_score
                        context_used = True
        
        if not intent_scores:
            return IntentResult("unknown", 0.0, {}, text)
        
        # Sort by score and get alternatives
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        best_intent, best_score = sorted_intents[0]
        
        # Normalize confidence score
        confidence = min(best_score / len(words), 1.0)
        
        # Extract parameters
        parameters = {}
        if best_intent in self.parameter_extractors:
            parameters = await self.parameter_extractors[best_intent](text_lower, words, context)
        
        # Get alternatives (top 3)
        alternatives = [(intent, score) for intent, score in sorted_intents[1:4]]
        
        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            parameters=parameters,
            original_text=text,
            context_used=context_used,
            alternatives=alternatives
        )
    
    def _calculate_intent_score(self, text: str, words: List[str], intent: str, 
                               config: Dict[str, Any], context: Optional[SessionContext]) -> float:
        """Calculate intent score with various factors"""
        keywords = config.get("keywords", [])
        weight = config.get("weight", 1.0)
        
        # Basic keyword matching
        keyword_score = sum(1 for keyword in keywords if keyword in text)
        
        # Position weighting (earlier words get higher weight)
        position_score = 0
        for i, word in enumerate(words[:5]):  # Check first 5 words
            if word in keywords:
                position_score += (5 - i) * 0.1
        
        # Context requirement check
        if config.get("requires_context", False) and not context:
            return 0
        
        return (keyword_score + position_score) * weight
    
    def _apply_context_boost(self, boost_config: Dict[str, Any], context: SessionContext) -> float:
        """Apply context-based score boost"""
        boost = 0.0
        
        if "last_intent" in boost_config:
            if context.last_intent in boost_config["last_intent"]:
                boost += boost_config.get("boost", 0.1)
        
        if "location" in boost_config:
            user_location = context.variables.get("location", "").lower()
            if any(loc in user_location for loc in boost_config["location"]):
                boost += boost_config.get("boost", 0.1)
        
        return boost
    
    async def _extract_music_params(self, text: str, words: List[str], 
                                  context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract music-related parameters"""
        params = {}
        
        # Artist extraction
        by_pattern = r"by\s+([^,\n]+)"
        by_match = re.search(by_pattern, text)
        if by_match:
            params["artist"] = by_match.group(1).strip()
        
        # Genre detection
        genres = ["jazz", "rock", "classical", "pop", "electronic", "ambient", "folk", "metal", "blues", "country"]
        for genre in genres:
            if genre in text:
                params["genre"] = genre
                break
        
        # Platform detection
        platforms = ["spotify", "youtube", "soundcloud", "apple music"]
        for platform in platforms:
            if platform in text:
                params["platform"] = platform
                break
        
        # Mood/energy detection
        moods = {
            "relaxing": ["relaxing", "calm", "peaceful", "chill"],
            "energetic": ["energetic", "upbeat", "fast", "dance"],
            "sad": ["sad", "melancholy", "depressing"],
            "happy": ["happy", "cheerful", "uplifting"]
        }
        
        for mood, keywords in moods.items():
            if any(keyword in text for keyword in keywords):
                params["mood"] = mood
                break
        
        # Default query if no specific parameters
        if not params:
            query_words = [w for w in words if w not in ["play", "music", "song", "some"]]
            if query_words:
                params["query"] = " ".join(query_words)
        
        return params
    
    async def _extract_volume_params(self, text: str, words: List[str], 
                                   context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract volume control parameters"""
        params = {}
        
        # Volume actions
        actions = {
            "up": ["up", "higher", "louder", "increase"],
            "down": ["down", "lower", "quieter", "decrease"],
            "mute": ["mute", "silent", "off"],
            "unmute": ["unmute", "on"],
            "max": ["max", "maximum", "full"],
            "min": ["min", "minimum"]
        }
        
        for action, keywords in actions.items():
            if any(keyword in text for keyword in keywords):
                params["action"] = action
                break
        
        # Numeric volume level
        numbers = re.findall(r'\b(\d+)\b', text)
        if numbers:
            level = int(numbers[0])
            if 0 <= level <= 100:
                params["level"] = str(level)
        
        # Percentage
        percent_match = re.search(r'(\d+)%', text)
        if percent_match:
            params["level"] = percent_match.group(1)
        
        return params
    
    async def _extract_audio_params(self, text: str, words: List[str], 
                                  context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract audio device parameters"""
        params = {}
        
        devices = {
            "headphones": ["headphones", "headset", "earbuds"],
            "speakers": ["speakers", "speaker"],
            "bluetooth": ["bluetooth", "bt"],
            "rtsp": ["rtsp", "network", "streaming"],
            "hdmi": ["hdmi", "tv", "television"],
            "usb": ["usb"]
        }
        
        for device, keywords in devices.items():
            if any(keyword in text for keyword in keywords):
                params["device"] = device
                break
        
        return params
    
    async def _extract_system_params(self, text: str, words: List[str], 
                                   context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract system control parameters"""
        params = {}
        
        actions = ["open", "close", "launch", "run", "execute", "kill", "start", "stop"]
        
        for i, word in enumerate(words):
            if word in actions:
                params["action"] = word
                # Get target application/command
                if i + 1 < len(words):
                    target = " ".join(words[i + 1:])
                    params["target"] = target
                break
        
        return params
    
    async def _extract_hardware_params(self, text: str, words: List[str], 
                                     context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract hardware control parameters"""
        params = {}
        
        # GPIO pin extraction
        pin_pattern = r'pin\s*(\d+)|gpio\s*(\d+)'
        pin_match = re.search(pin_pattern, text)
        if pin_match:
            pin_num = pin_match.group(1) or pin_match.group(2)
            params["pin"] = pin_num
        
        # Actions
        actions = {
            "on": ["on", "high", "enable", "activate"],
            "off": ["off", "low", "disable", "deactivate"],
            "toggle": ["toggle", "switch"],
            "read": ["read", "get", "check"],
            "write": ["write", "set"]
        }
        
        for action, keywords in actions.items():
            if any(keyword in text for keyword in keywords):
                params["action"] = action
                break
        
        # Value for PWM/analog
        value_pattern = r'to\s+(\d+)|value\s+(\d+)|(\d+)%'
        value_match = re.search(value_pattern, text)
        if value_match:
            value = value_match.group(1) or value_match.group(2) or value_match.group(3)
            params["value"] = value
        
        return params
    
    async def _extract_home_params(self, text: str, words: List[str], 
                                 context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract smart home parameters"""
        params = {}
        
        # Device types
        devices = {
            "lights": ["lights", "light", "lamp", "bulb"],
            "temperature": ["temperature", "thermostat", "heating", "cooling"],
            "security": ["lock", "unlock", "alarm", "camera", "door"],
            "blinds": ["blinds", "curtains", "shades"]
        }
        
        for device, keywords in devices.items():
            if any(keyword in text for keyword in keywords):
                params["device_type"] = device
                break
        
        # Actions
        actions = {
            "on": ["on", "turn on", "enable"],
            "off": ["off", "turn off", "disable"],
            "dim": ["dim", "dimmer"],
            "brighten": ["brighten", "brighter"],
            "lock": ["lock"],
            "unlock": ["unlock"]
        }
        
        for action, keywords in actions.items():
            if any(keyword in text for keyword in keywords):
                params["action"] = action
                break
        
        # Room/location
        rooms = ["living room", "bedroom", "kitchen", "bathroom", "office", "garage"]
        for room in rooms:
            if room in text:
                params["location"] = room
                break
        
        # Temperature value
        temp_pattern = r'(\d+)\s*degrees?|(\d+)°'
        temp_match = re.search(temp_pattern, text)
        if temp_match:
            temp = temp_match.group(1) or temp_match.group(2)
            params["temperature"] = temp
        
        return params
    
    async def _extract_file_params(self, text: str, words: List[str], 
                                 context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract file operation parameters"""
        params = {}
        
        # URLs
        url_pattern = r'https?://[^\s]+'
        url_match = re.search(url_pattern, text)
        if url_match:
            params["url"] = url_match.group(0)
        
        # File paths
        path_pattern = r'[/\\][\w\s/\\.-]+'
        path_match = re.search(path_pattern, text)
        if path_match:
            params["path"] = path_match.group(0)
        
        # Actions
        actions = ["download", "upload", "copy", "move", "delete", "create", "save"]
        for action in actions:
            if action in text:
                params["action"] = action
                break
        
        return params
    
    async def _extract_navigation_params(self, text: str, words: List[str], 
                                       context: Optional[SessionContext]) -> Dict[str, str]:
        """Extract navigation parameters"""
        params = {}
        
        # Destination extraction
        to_pattern = r'to\s+([^,\n]+)'
        to_match = re.search(to_pattern, text)
        if to_match:
            params["destination"] = to_match.group(1).strip()
        
        # Transportation mode
        modes = {
            "driving": ["drive", "driving", "car"],
            "walking": ["walk", "walking", "foot"],
            "transit": ["transit", "bus", "train", "public"],
            "cycling": ["bike", "cycling", "bicycle"]
        }
        
        for mode, keywords in modes.items():
            if any(keyword in text for keyword in keywords):
                params["mode"] = mode
                break
        
        return params


class ContextManager:
    """Context management for users, sessions, and devices"""
    
    def __init__(self, data_dir: str = "/tmp/ai-servis/context"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.users_cache: Dict[str, UserContext] = {}
        self.sessions_cache: Dict[str, SessionContext] = {}
        
        # Load existing contexts
        self._load_contexts()
    
    def _load_contexts(self):
        """Load existing contexts from disk"""
        try:
            # Load users
            users_file = self.data_dir / "users.json"
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                    for user_id, data in users_data.items():
                        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
                        self.users_cache[user_id] = UserContext(**data)
            
            # Load sessions
            sessions_file = self.data_dir / "sessions.json"
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                    for session_id, data in sessions_data.items():
                        data['created_at'] = datetime.fromisoformat(data['created_at'])
                        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
                        self.sessions_cache[session_id] = SessionContext(**data)
            
            logger.info(f"Loaded {len(self.users_cache)} users and {len(self.sessions_cache)} sessions")
            
        except Exception as e:
            logger.error(f"Error loading contexts: {e}")
    
    def _save_contexts(self):
        """Save contexts to disk"""
        try:
            # Save users
            users_data = {}
            for user_id, context in self.users_cache.items():
                data = asdict(context)
                data['last_activity'] = data['last_activity'].isoformat()
                users_data[user_id] = data
            
            with open(self.data_dir / "users.json", 'w') as f:
                json.dump(users_data, f, indent=2)
            
            # Save sessions (only active ones)
            sessions_data = {}
            for session_id, context in self.sessions_cache.items():
                if context.is_active():
                    data = asdict(context)
                    data['created_at'] = data['created_at'].isoformat()
                    data['last_accessed'] = data['last_accessed'].isoformat()
                    sessions_data[session_id] = data
            
            with open(self.data_dir / "sessions.json", 'w') as f:
                json.dump(sessions_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving contexts: {e}")
    
    def create_session(self, user_id: str, interface_type: str) -> str:
        """Create a new session"""
        import uuid
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        
        session = SessionContext(
            session_id=session_id,
            user_id=user_id,
            interface_type=interface_type,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
        
        self.sessions_cache[session_id] = session
        self._save_contexts()
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get session context"""
        session = self.sessions_cache.get(session_id)
        if session and session.is_active():
            session.last_accessed = datetime.now()
            return session
        return None
    
    def update_session(self, session_id: str, **kwargs):
        """Update session context"""
        if session_id in self.sessions_cache:
            session = self.sessions_cache[session_id]
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_accessed = datetime.now()
            self._save_contexts()
    
    def add_to_history(self, session_id: str, command: str, response: str):
        """Add command and response to session history"""
        session = self.sessions_cache.get(session_id)
        if session:
            session.command_history.append(command)
            session.response_history.append(response)
            
            # Keep only last 50 entries
            if len(session.command_history) > 50:
                session.command_history = session.command_history[-50:]
                session.response_history = session.response_history[-50:]
            
            session.last_accessed = datetime.now()
            self._save_contexts()
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired = [sid for sid, session in self.sessions_cache.items() if not session.is_active()]
        for session_id in expired:
            del self.sessions_cache[session_id]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
            self._save_contexts()


@dataclass
class CommandInteraction:
    """Record of a voice command interaction"""
    command_text: str
    intent: str
    confidence: float
    parameters: Dict[str, str]
    success: bool
    response: str
    timestamp: datetime
    session_id: str
    execution_time_ms: float


class VoiceCommandAnalytics:
    """Tracks voice command interactions for learning and improvement (Phases 3 & 4)"""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or "/tmp/ai-servis/analytics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.interactions: List[CommandInteraction] = []
        self._load_interactions()

    def record_interaction(self, interaction: CommandInteraction) -> None:
        """Record a command interaction for analytics"""
        self.interactions.append(interaction)
        self._save_interactions()

    def get_success_rate(self, intent: Optional[str] = None) -> float:
        """Get success rate, optionally filtered by intent"""
        filtered = [i for i in self.interactions if not intent or i.intent == intent]
        if not filtered:
            return 0.0
        return sum(1 for i in filtered if i.success) / len(filtered)

    def get_low_confidence_commands(self, threshold: float = 0.5) -> List[CommandInteraction]:
        """Find commands that consistently have low confidence"""
        return [i for i in self.interactions if i.confidence < threshold]

    def get_failed_patterns(self) -> Dict[str, int]:
        """Identify intents with high failure rates"""
        intent_failures: Dict[str, int] = {}
        for i in self.interactions:
            if not i.success:
                intent_failures[i.intent] = intent_failures.get(i.intent, 0) + 1
        return dict(sorted(intent_failures.items(), key=lambda x: x[1], reverse=True))

    def get_command_frequency(self) -> Dict[str, int]:
        """Get frequency of each intent type"""
        freq: Dict[str, int] = {}
        for i in self.interactions:
            freq[i.intent] = freq.get(i.intent, 0) + 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))

    def suggest_improvements(self) -> List[Dict[str, Any]]:
        """Analyze patterns and suggest improvements (Phase 4 Learning Loop)"""
        suggestions = []
        failed = self.get_failed_patterns()
        for intent, count in failed.items():
            if count >= 3:
                success_rate = self.get_success_rate(intent)
                suggestions.append({
                    "intent": intent,
                    "failure_count": count,
                    "success_rate": success_rate,
                    "suggestion": (
                        f"Intent '{intent}' has {count} failures "
                        f"({success_rate:.0%} success). "
                        f"Consider adding keywords or adjusting patterns."
                    ),
                })

        low_conf = self.get_low_confidence_commands()
        if len(low_conf) > 5:
            common_words: Dict[str, int] = {}
            for cmd in low_conf:
                for word in cmd.command_text.lower().split():
                    common_words[word] = common_words.get(word, 0) + 1
            top_ambiguous = sorted(
                common_words.items(), key=lambda x: x[1], reverse=True
            )[:5]
            suggestions.append({
                "type": "ambiguous_words",
                "words": [w for w, _ in top_ambiguous],
                "suggestion": (
                    "These words frequently appear in low-confidence commands. "
                    "Consider adding disambiguation rules."
                ),
            })

        return suggestions

    def _load_interactions(self) -> None:
        path = self.data_dir / "interactions.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                self.interactions = [
                    CommandInteraction(
                        **{**d, "timestamp": datetime.fromisoformat(d["timestamp"])}
                    )
                    for d in data
                ]
            except Exception as e:
                logger.warning(f"Failed to load interactions: {e}")

    def _save_interactions(self) -> None:
        path = self.data_dir / "interactions.json"
        try:
            data = [
                {**asdict(i), "timestamp": i.timestamp.isoformat()}
                for i in self.interactions[-1000:]  # Keep last 1000
            ]
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save interactions: {e}")


class EnhancedCoreOrchestrator(MCPServer):
    """Enhanced Core Orchestrator with advanced features"""
    
    def __init__(self):
        super().__init__("ai-servis-core-enhanced", "2.0.0")
        self.services: Dict[str, ServiceInfo] = {}
        self.mcp_clients: Dict[str, MCPClient] = {}
        self.nlp_processor = EnhancedNLPProcessor()
        self.context_manager = ContextManager()
        self.analytics = VoiceCommandAnalytics()
        self.setup_tools()
        self._register_voice_prompts()

        # Background tasks
        self._cleanup_task = None
        self._health_check_task = None
    
    def setup_tools(self):
        """Setup enhanced orchestrator tools"""
        
        # Enhanced voice command processing
        voice_command_tool = create_tool(
            name="process_voice_command",
            description="Process natural language command with context awareness and advanced NLP",
            schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The voice command text to process"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID for context management"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID for personalization"
                    },
                    "interface_type": {
                        "type": "string",
                        "description": "Interface type (voice, text, web, mobile)",
                        "default": "voice"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context information",
                        "properties": {
                            "location": {"type": "string"},
                            "time": {"type": "string"},
                            "device_id": {"type": "string"}
                        }
                    }
                },
                "required": ["text"]
            },
            handler=self.handle_enhanced_voice_command
        )
        self.add_tool(voice_command_tool)
        
        # Context management tools
        create_session_tool = create_tool(
            name="create_session",
            description="Create a new user session",
            schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "interface_type": {"type": "string"}
                },
                "required": ["user_id", "interface_type"]
            },
            handler=self.handle_create_session
        )
        self.add_tool(create_session_tool)
        
        # Service analytics
        service_analytics_tool = create_tool(
            name="service_analytics",
            description="Get service performance analytics",
            schema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "metric": {"type": "string", "enum": ["response_time", "error_rate", "usage"]}
                }
            },
            handler=self.handle_service_analytics
        )
        self.add_tool(service_analytics_tool)
        
        # Intent analysis
        analyze_intent_tool = create_tool(
            name="analyze_intent",
            description="Analyze command intent with confidence scores and alternatives",
            schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "session_id": {"type": "string"}
                },
                "required": ["text"]
            },
            handler=self.handle_analyze_intent
        )
        self.add_tool(analyze_intent_tool)

        # Voice command analytics (Phase 3 & 4)
        voice_analytics_tool = create_tool(
            name="voice_analytics",
            description="Get voice command analytics, usage patterns, and improvement suggestions",
            schema={
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["success_rate", "frequency", "failures", "suggestions"],
                    },
                    "intent": {
                        "type": "string",
                        "description": "Filter by intent",
                    },
                },
            },
            handler=self.handle_voice_analytics,
        )
        self.add_tool(voice_analytics_tool)

    def _register_voice_prompts(self):
        """Register voice command prompts for the skill (Phase 1)"""
        self.add_prompt(Prompt(
            name="voice-command-design-principles",
            description="Design guidelines for voice commands based on device type and user context",
            arguments=[
                {"name": "deviceType", "description": "Target device (mobile, raspberry-pi)", "required": True},
                {"name": "userContext", "description": "User type (developer, homeowner)", "required": True},
                {"name": "focusAreas", "description": "Detected usage patterns", "required": False},
            ],
        ))
        self.add_prompt(Prompt(
            name="voice-command-clarity-checklist",
            description="Evaluate clarity and usability of voice commands",
            arguments=[
                {"name": "commands", "description": "List of current commands to evaluate", "required": True},
                {"name": "userFeedback", "description": "Collected user feedback", "required": False},
            ],
        ))
        self.add_prompt(Prompt(
            name="mia-context-analyzer",
            description="Analyze current context to interpret ambiguous voice commands",
            arguments=[
                {"name": "currentLocation", "description": "Device location", "required": True},
                {"name": "recentActions", "description": "Recent action history", "required": True},
                {"name": "deviceState", "description": "Current system state", "required": True},
                {"name": "timeOfDay", "description": "Current time", "required": True},
            ],
        ))
        self.add_prompt(Prompt(
            name="voice-response-generator",
            description="Generate a confident voice response based on interpreted command",
            arguments=[
                {"name": "interpretation", "description": "Chosen command interpretation", "required": True},
                {"name": "confidence", "description": "Confidence score", "required": True},
                {"name": "context", "description": "Extracted context", "required": True},
            ],
        ))

    async def handle_voice_analytics(
        self, metric: str = "suggestions", intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle voice analytics requests"""
        if metric == "success_rate":
            return {"success_rate": self.analytics.get_success_rate(intent)}
        elif metric == "frequency":
            return {"frequency": self.analytics.get_command_frequency()}
        elif metric == "failures":
            return {"failed_patterns": self.analytics.get_failed_patterns()}
        elif metric == "suggestions":
            return {"suggestions": self.analytics.suggest_improvements()}
        return {"error": f"Unknown metric: {metric}"}

    async def handle_enhanced_voice_command(self, text: str, session_id: Optional[str] = None,
                                          user_id: Optional[str] = None,
                                          interface_type: str = "voice",
                                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle enhanced voice command with context, prompt enhancement, and analytics"""
        logger.info(f"Processing enhanced command: {text}")
        start_time = time.time()

        try:
            # Create session if needed
            if not session_id and user_id:
                session_id = self.context_manager.create_session(user_id, interface_type)
            elif not session_id:
                session_id = self.context_manager.create_session("anonymous", interface_type)

            # Get session context
            session_context = self.context_manager.get_session(session_id)

            # Phase 2: Parse command with context (keyword-based NLP)
            intent_result = await self.nlp_processor.parse_command(text, session_context)

            # Phase 2: Enhance with MCP prompts if available
            intent_result = await self._enhance_with_prompts(text, intent_result, session_context)

            logger.info(f"Intent: {intent_result.intent} (confidence: {intent_result.confidence:.2f})")

            # Phase 3: Route and execute command
            response = await self._route_enhanced_command(intent_result, session_context, context)

            # Update context
            if session_context:
                self.context_manager.update_session(
                    session_id,
                    last_intent=intent_result.intent,
                    last_parameters=intent_result.parameters
                )
                self.context_manager.add_to_history(session_id, text, response)

            # Phase 3: Record interaction for analytics
            execution_time_ms = (time.time() - start_time) * 1000
            is_success = "error" not in str(response).lower()
            self.analytics.record_interaction(CommandInteraction(
                command_text=text,
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                parameters=intent_result.parameters,
                success=is_success,
                response=str(response),
                timestamp=datetime.now(),
                session_id=session_id,
                execution_time_ms=execution_time_ms,
            ))

            return {
                "response": response,
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
                "context_used": intent_result.context_used,
                "alternatives": intent_result.alternatives,
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Error processing enhanced command: {e}")
            return {
                "response": f"Error processing command: {str(e)}",
                "intent": "error",
                "confidence": 0.0,
                "session_id": session_id
            }
    
    async def handle_create_session(self, user_id: str, interface_type: str) -> Dict[str, Any]:
        """Handle session creation"""
        session_id = self.context_manager.create_session(user_id, interface_type)
        return {
            "session_id": session_id,
            "user_id": user_id,
            "interface_type": interface_type,
            "created_at": datetime.now().isoformat()
        }
    
    async def handle_service_analytics(self, service_name: Optional[str] = None, 
                                     metric: str = "response_time") -> Dict[str, Any]:
        """Handle service analytics request"""
        analytics = {}
        
        services_to_analyze = [service_name] if service_name else list(self.services.keys())
        
        for name in services_to_analyze:
            if name in self.services:
                service = self.services[name]
                analytics[name] = {
                    "response_time": service.response_time,
                    "error_count": service.error_count,
                    "health_status": service.health_status,
                    "last_seen": service.last_seen.isoformat() if service.last_seen else None
                }
        
        return {"analytics": analytics, "metric": metric}
    
    async def handle_analyze_intent(self, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle intent analysis request"""
        session_context = None
        if session_id:
            session_context = self.context_manager.get_session(session_id)
        
        intent_result = await self.nlp_processor.parse_command(text, session_context)
        
        return {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "parameters": intent_result.parameters,
            "context_used": intent_result.context_used,
            "alternatives": intent_result.alternatives,
            "original_text": intent_result.original_text
        }
    
    async def _enhance_with_prompts(
        self,
        text: str,
        intent_result: IntentResult,
        session_context: Optional[SessionContext],
    ) -> IntentResult:
        """Enhance intent result using MCP prompts (Phase 2).

        Falls back to the original keyword-based result if the
        mcp-prompts server is unavailable.
        """
        prompts_client = self.mcp_clients.get("mcp-prompts")
        if not prompts_client:
            return intent_result

        try:
            context_data = {
                "currentLocation": (
                    session_context.variables.get("location", "unknown")
                    if session_context
                    else "unknown"
                ),
                "recentActions": json.dumps(
                    session_context.command_history[-5:]
                    if session_context
                    else []
                ),
                "deviceState": json.dumps(
                    {"services": list(self.services.keys())}
                ),
                "timeOfDay": datetime.now().strftime("%H:%M"),
            }
            context_analysis = await prompts_client.get_prompt(
                "mia-context-analyzer", context_data
            )

            if context_analysis and "messages" in context_analysis:
                analysis_text = (
                    context_analysis["messages"][0]
                    .get("content", {})
                    .get("text", "")
                )
                if analysis_text:
                    intent_result = IntentResult(
                        intent=intent_result.intent,
                        confidence=min(intent_result.confidence + 0.1, 1.0),
                        parameters=intent_result.parameters,
                        original_text=intent_result.original_text,
                        context_used=True,
                        alternatives=intent_result.alternatives,
                    )
        except Exception as e:
            logger.debug(f"MCP prompts enhancement unavailable: {e}")

        return intent_result

    async def _route_enhanced_command(self, intent_result: IntentResult,
                                    session_context: Optional[SessionContext],
                                    additional_context: Optional[Dict[str, Any]]) -> str:
        """Route command with enhanced logic"""
        intent = intent_result.intent
        parameters = intent_result.parameters

        # Handle follow-up commands
        if intent == "follow_up" and session_context:
            return await self._handle_follow_up(intent_result, session_context)
        
        # Low confidence handling
        if intent_result.confidence < 0.3:
            alternatives = [alt[0] for alt in intent_result.alternatives[:2]]
            return f"I'm not sure what you meant. Did you mean: {', '.join(alternatives)}? (confidence: {intent_result.confidence:.2f})"
        
        # Route to appropriate service
        service_mapping = {
            "play_music": "ai-audio-assistant",
            "control_volume": "ai-audio-assistant", 
            "switch_audio": "ai-audio-assistant",
            "system_control": "ai-platform-linux",
            "file_operation": "webgrab-server",
            "hardware_control": "hardware-bridge",
            "smart_home": "ai-home-automation",
            "communication": "ai-communications",
            "navigation": "ai-maps-navigation"
        }
        
        service_name = service_mapping.get(intent)
        if not service_name:
            return f"No service available for intent: {intent}"
        
        # Enhanced service call with retry logic
        result = await self._call_service_enhanced(service_name, intent, parameters, session_context)
        return result
    
    async def _handle_follow_up(self, intent_result: IntentResult, 
                              session_context: SessionContext) -> str:
        """Handle follow-up commands using context"""
        if not session_context.last_intent:
            return "I don't have context for a follow-up. Please be more specific."
        
        # Merge parameters from context
        merged_params = session_context.last_parameters.copy()
        merged_params.update(intent_result.parameters)
        
        # Create new intent result with context
        contextual_intent = IntentResult(
            intent=session_context.last_intent,
            confidence=0.8,
            parameters=merged_params,
            original_text=intent_result.original_text,
            context_used=True
        )
        
        return await self._route_enhanced_command(contextual_intent, session_context, None)
    
    async def _call_service_enhanced(self, service_name: str, tool_name: str,
                                   parameters: Dict[str, str],
                                   session_context: Optional[SessionContext]) -> str:
        """Enhanced service call with monitoring and retry"""
        if service_name not in self.services:
            return f"Service {service_name} not available"
        
        service = self.services[service_name]
        start_time = time.time()
        
        try:
            # Add session context to parameters if available
            if session_context:
                parameters["session_id"] = session_context.session_id
                parameters["user_id"] = session_context.user_id
            
            # Call service based on type
            if service.service_type == "mcp":
                result = await self._call_mcp_service(service_name, tool_name, parameters)
            elif service.service_type == "http":
                result = await self._call_http_service(service, tool_name, parameters)
            else:
                result = f"Unsupported service type: {service.service_type}"
            
            # Update service metrics
            response_time = time.time() - start_time
            service.response_time = response_time
            service.health_status = "healthy"
            service.last_seen = datetime.now()
            
            # Update session context
            if session_context:
                self.context_manager.update_session(
                    session_context.session_id,
                    last_used_service=service_name
                )
            
            return result
            
        except Exception as e:
            # Update error metrics
            service.error_count += 1
            service.health_status = "error"
            
            logger.error(f"Error calling service {service_name}: {e}")
            return f"Error calling service {service_name}: {str(e)}"
    
    async def _call_mcp_service(self, service_name: str, tool_name: str, 
                              parameters: Dict[str, str]) -> str:
        """Call MCP service"""
        client = self.mcp_clients.get(service_name)
        if not client:
            return f"MCP client not available for {service_name}"
        
        result = await client.call_tool(tool_name, parameters)
        return f"Service {service_name} responded: {result}"
    
    async def _call_http_service(self, service: ServiceInfo, tool_name: str,
                               parameters: Dict[str, str]) -> str:
        """Call HTTP service"""
        url = f"http://{service.host}:{service.port}/api/{tool_name}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=parameters) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("message", "HTTP service completed")
                else:
                    return f"HTTP error: {response.status}"
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self._health_check_task = asyncio.create_task(self._periodic_health_check())
        logger.info("Background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()
        logger.info("Background tasks stopped")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                self.context_manager.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def _periodic_health_check(self):
        """Periodic health check of services"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                await self._check_all_services_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check task: {e}")
    
    async def _check_all_services_health(self):
        """Check health of all registered services"""
        for service_name, service in self.services.items():
            try:
                # Simple ping check
                start_time = time.time()
                
                if service.service_type == "http":
                    url = f"http://{service.host}:{service.port}/health"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status == 200:
                                service.health_status = "healthy"
                            else:
                                service.health_status = "unhealthy"
                else:
                    # For MCP services, we'd ping them differently
                    service.health_status = "unknown"
                
                service.response_time = time.time() - start_time
                service.last_seen = datetime.now()
                
            except Exception as e:
                service.health_status = "error"
                service.error_count += 1
                logger.warning(f"Health check failed for {service_name}: {e}")


async def main():
    """Main entry point for enhanced orchestrator"""
    logger.info("Starting MIA Enhanced Core Orchestrator")
    
    # Create orchestrator
    orchestrator = EnhancedCoreOrchestrator()
    
    # Register enhanced services
    services_config = [
        {
            "name": "ai-audio-assistant",
            "host": "localhost",
            "port": 8082,
            "capabilities": ["audio", "music", "voice", "streaming", "volume", "playback"],
            "service_type": "http"
        },
        {
            "name": "ai-platform-linux", 
            "host": "localhost",
            "port": 8083,
            "capabilities": ["system", "process", "file", "command", "application"],
            "service_type": "http"
        },
        {
            "name": "hardware-bridge",
            "host": "localhost", 
            "port": 8084,
            "capabilities": ["gpio", "sensor", "actuator", "pwm", "i2c", "spi"],
            "service_type": "mcp"
        },
        {
            "name": "ai-home-automation",
            "host": "localhost",
            "port": 8085,
            "capabilities": ["lights", "temperature", "security", "automation"],
            "service_type": "http"
        },
        {
            "name": "mcp-prompts",
            "host": "localhost",
            "port": 8086,
            "capabilities": ["prompts", "voice-command", "context-analysis"],
            "service_type": "mcp"
        },
    ]
    
    for config in services_config:
        service = ServiceInfo(**config)
        orchestrator.services[service.name] = service
        logger.info(f"Registered service: {service.name}")
    
    # Start background tasks
    await orchestrator.start_background_tasks()
    
    # Start HTTP server
    from aiohttp import web
    
    app = web.Application()
    
    async def handle_command(request):
        """HTTP endpoint for command processing"""
        data = await request.json()
        result = await orchestrator.handle_enhanced_voice_command(**data)
        return web.json_response(result)
    
    async def handle_analytics(request):
        """HTTP endpoint for analytics"""
        service_name = request.query.get("service")
        metric = request.query.get("metric", "response_time")
        result = await orchestrator.handle_service_analytics(service_name, metric)
        return web.json_response(result)
    
    app.router.add_post("/api/command", handle_command)
    app.router.add_get("/api/analytics", handle_analytics)
    
    # CORS support
    async def add_cors_headers(request, response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    app.middlewares.append(add_cors_headers)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    
    logger.info("Enhanced Core Orchestrator started on port 8080")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Enhanced Core Orchestrator")
    finally:
        await orchestrator.stop_background_tasks()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())