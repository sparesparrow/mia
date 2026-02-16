#!/usr/bin/env python3
"""
MIA Universal: Advanced Voice Processing Framework
Provides TTS/STT with ElevenLabs, OpenAI Whisper, wake word detection, and VAD
"""

import asyncio
import logging
import os
import json
import io
import base64
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue
import tempfile
import wave

# Setup logging
logger = logging.getLogger(__name__)


class VoiceEngine(Enum):
    """Available voice processing engines"""
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    WHISPER_LOCAL = "whisper_local"
    MOCK = "mock"


class AudioQuality(Enum):
    """Audio quality settings"""
    LOW = "low"          # 16kHz, 16-bit
    MEDIUM = "medium"    # 22kHz, 16-bit
    HIGH = "high"        # 44.1kHz, 16-bit
    PREMIUM = "premium"  # 48kHz, 24-bit


class VoiceGender(Enum):
    """Voice gender options"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceProfile:
    """Voice profile configuration"""
    id: str
    name: str
    gender: VoiceGender
    language: str = "en"
    description: str = ""
    engine: VoiceEngine = VoiceEngine.ELEVENLABS
    sample_rate: int = 22050
    stability: float = 0.75
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


@dataclass
class TTSRequest:
    """Text-to-speech request"""
    text: str
    voice_profile: VoiceProfile
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    output_format: str = "mp3"
    quality: AudioQuality = AudioQuality.MEDIUM


@dataclass
class TTSResponse:
    """Text-to-speech response"""
    success: bool
    audio_data: Optional[bytes] = None
    audio_url: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    engine_used: Optional[VoiceEngine] = None
    processing_time_ms: Optional[int] = None


@dataclass
class STTRequest:
    """Speech-to-text request"""
    audio_data: bytes
    language: str = "en"
    model: str = "whisper-1"
    temperature: float = 0.0
    engine: VoiceEngine = VoiceEngine.OPENAI
    enable_vad: bool = True
    quality: AudioQuality = AudioQuality.MEDIUM


@dataclass
class STTResponse:
    """Speech-to-text response"""
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    language_detected: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    engine_used: Optional[VoiceEngine] = None
    processing_time_ms: Optional[int] = None
    segments: Optional[List[Dict[str, Any]]] = None


@dataclass
class WakeWordConfig:
    """Wake word detection configuration"""
    wake_words: List[str]
    sensitivity: float = 0.7
    timeout_ms: int = 5000
    min_duration_ms: int = 500
    max_duration_ms: int = 3000
    enable_beep: bool = True
    model_path: Optional[str] = None


@dataclass
class VADConfig:
    """Voice Activity Detection configuration"""
    aggressiveness: int = 2  # 0-3, higher = more aggressive
    frame_duration_ms: int = 30  # 10, 20, or 30 ms
    padding_duration_ms: int = 300
    sample_rate: int = 16000
    enable_webrtc: bool = True


class VoiceProcessorInterface(ABC):
    """Abstract interface for voice processors"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the voice processor"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the voice processor"""
        pass
    
    @abstractmethod
    async def text_to_speech(self, request: TTSRequest) -> TTSResponse:
        """Convert text to speech"""
        pass
    
    @abstractmethod
    async def speech_to_text(self, request: STTRequest) -> STTResponse:
        """Convert speech to text"""
        pass
    
    @abstractmethod
    async def get_available_voices(self) -> List[VoiceProfile]:
        """Get list of available voice profiles"""
        pass


class ElevenLabsProcessor(VoiceProcessorInterface):
    """ElevenLabs voice processor implementation"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"
        self.initialized = False
        self.voice_cache: Dict[str, VoiceProfile] = {}
        self.request_cache: Dict[str, TTSResponse] = {}
        
        logger.info("ElevenLabs processor created")
    
    async def initialize(self) -> bool:
        """Initialize ElevenLabs processor"""
        logger.info("--- Initializing ElevenLabs Voice Processor ---")
        
        if not self.api_key:
            logger.error("ElevenLabs API key not provided")
            return False
        
        try:
            # Test API connection by getting voices
            voices = await self.get_available_voices()
            
            if voices:
                self.initialized = True
                logger.info(f"ElevenLabs processor initialized with {len(voices)} voices")
                return True
            else:
                logger.error("Failed to retrieve ElevenLabs voices")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing ElevenLabs processor: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown ElevenLabs processor"""
        logger.info("Shutting down ElevenLabs processor")
        self.initialized = False
        self.voice_cache.clear()
        self.request_cache.clear()
    
    async def text_to_speech(self, request: TTSRequest) -> TTSResponse:
        """Convert text to speech using ElevenLabs"""
        start_time = time.time()
        
        logger.info(f"--- ElevenLabs TTS Request ---")
        logger.info(f"Text length: {len(request.text)} characters")
        logger.info(f"Voice: {request.voice_profile.name}")
        logger.info(f"Speed: {request.speed}")
        
        try:
            if not self.initialized:
                raise Exception("ElevenLabs processor not initialized")
            
            # Check cache first
            cache_key = self._generate_tts_cache_key(request)
            if cache_key in self.request_cache:
                logger.debug("Using cached TTS result")
                cached_response = self.request_cache[cache_key]
                return cached_response
            
            # Prepare request data
            tts_data = {
                "text": request.text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": request.voice_profile.stability,
                    "similarity_boost": request.voice_profile.similarity_boost,
                    "style": request.voice_profile.style,
                    "use_speaker_boost": request.voice_profile.use_speaker_boost
                }
            }
            
            # Mock API call for now
            await asyncio.sleep(0.5)  # Simulate API latency
            
            # Generate mock audio data
            mock_audio_data = self._generate_mock_audio(request.text, request.voice_profile.sample_rate)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            response = TTSResponse(
                success=True,
                audio_data=mock_audio_data,
                duration_ms=len(request.text) * 50,  # Rough estimate
                engine_used=VoiceEngine.ELEVENLABS,
                processing_time_ms=processing_time
            )
            
            # Cache response
            self.request_cache[cache_key] = response
            if len(self.request_cache) > 100:
                # Remove oldest entries
                oldest_keys = list(self.request_cache.keys())[:50]
                for key in oldest_keys:
                    del self.request_cache[key]
            
            logger.info(f"--- ElevenLabs TTS Completed Successfully ---")
            logger.info(f"Audio data size: {len(mock_audio_data)} bytes")
            logger.info(f"Processing time: {processing_time}ms")
            
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"--- ElevenLabs TTS Failed ---")
            logger.error(f"Error: {e}")
            
            return TTSResponse(
                success=False,
                error=str(e),
                engine_used=VoiceEngine.ELEVENLABS,
                processing_time_ms=processing_time
            )
    
    async def speech_to_text(self, request: STTRequest) -> STTResponse:
        """ElevenLabs doesn't provide STT, return error"""
        logger.warning("ElevenLabs does not support speech-to-text")
        return STTResponse(
            success=False,
            error="ElevenLabs does not support speech-to-text",
            engine_used=VoiceEngine.ELEVENLABS
        )
    
    async def get_available_voices(self) -> List[VoiceProfile]:
        """Get available ElevenLabs voices"""
        logger.debug("Getting ElevenLabs available voices")
        
        try:
            if not self.api_key:
                logger.warning("No API key, returning mock voices")
                return self._get_mock_voices()
            
            # Mock API call - in real implementation would call ElevenLabs API
            await asyncio.sleep(0.2)
            
            # Return mock voices for now
            voices = self._get_mock_voices()
            
            # Cache voices
            for voice in voices:
                self.voice_cache[voice.id] = voice
            
            logger.info(f"Retrieved {len(voices)} ElevenLabs voices")
            return voices
            
        except Exception as e:
            logger.error(f"Error getting ElevenLabs voices: {e}")
            return []
    
    def _get_mock_voices(self) -> List[VoiceProfile]:
        """Get mock voice profiles for testing"""
        return [
            VoiceProfile(
                id="elevenlabs_rachel",
                name="Rachel",
                gender=VoiceGender.FEMALE,
                language="en",
                description="American English, young adult female",
                engine=VoiceEngine.ELEVENLABS,
                sample_rate=22050
            ),
            VoiceProfile(
                id="elevenlabs_drew",
                name="Drew",
                gender=VoiceGender.MALE,
                language="en",
                description="American English, middle-aged male",
                engine=VoiceEngine.ELEVENLABS,
                sample_rate=22050
            ),
            VoiceProfile(
                id="elevenlabs_clyde",
                name="Clyde",
                gender=VoiceGender.MALE,
                language="en",
                description="American English, warm male voice",
                engine=VoiceEngine.ELEVENLABS,
                sample_rate=22050
            )
        ]
    
    def _generate_tts_cache_key(self, request: TTSRequest) -> str:
        """Generate cache key for TTS request"""
        key_data = f"{request.text}_{request.voice_profile.id}_{request.speed}_{request.pitch}_{request.volume}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _generate_mock_audio(self, text: str, sample_rate: int) -> bytes:
        """Generate mock audio data for testing"""
        # Create a simple sine wave based on text length
        import math
        
        duration_seconds = len(text) * 0.05  # ~50ms per character
        samples = int(sample_rate * duration_seconds)
        
        audio_data = []
        for i in range(samples):
            # Simple sine wave with some variation
            frequency = 440 + (hash(text) % 200)
            sample = math.sin(2 * math.pi * frequency * i / sample_rate)
            # Convert to 16-bit PCM
            sample_16bit = int(sample * 32767)
            audio_data.extend([sample_16bit & 0xFF, (sample_16bit >> 8) & 0xFF])
        
        return bytes(audio_data)


class OpenAIProcessor(VoiceProcessorInterface):
    """OpenAI voice processor implementation (Whisper + TTS)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.initialized = False
        self.request_cache: Dict[str, Union[TTSResponse, STTResponse]] = {}
        
        logger.info("OpenAI processor created")
    
    async def initialize(self) -> bool:
        """Initialize OpenAI processor"""
        logger.info("--- Initializing OpenAI Voice Processor ---")
        
        if not self.api_key:
            logger.error("OpenAI API key not provided")
            return False
        
        try:
            # Test API connection
            self.initialized = True
            logger.info("OpenAI processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing OpenAI processor: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown OpenAI processor"""
        logger.info("Shutting down OpenAI processor")
        self.initialized = False
        self.request_cache.clear()
    
    async def text_to_speech(self, request: TTSRequest) -> TTSResponse:
        """Convert text to speech using OpenAI TTS"""
        start_time = time.time()
        
        logger.info(f"--- OpenAI TTS Request ---")
        logger.info(f"Text length: {len(request.text)} characters")
        logger.info(f"Voice: {request.voice_profile.name}")
        
        try:
            if not self.initialized:
                raise Exception("OpenAI processor not initialized")
            
            # Mock API call for now
            await asyncio.sleep(0.3)
            
            # Generate mock audio data
            mock_audio_data = self._generate_mock_audio(request.text)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            response = TTSResponse(
                success=True,
                audio_data=mock_audio_data,
                duration_ms=len(request.text) * 60,  # Rough estimate
                engine_used=VoiceEngine.OPENAI,
                processing_time_ms=processing_time
            )
            
            logger.info(f"--- OpenAI TTS Completed Successfully ---")
            logger.info(f"Processing time: {processing_time}ms")
            
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"--- OpenAI TTS Failed ---")
            logger.error(f"Error: {e}")
            
            return TTSResponse(
                success=False,
                error=str(e),
                engine_used=VoiceEngine.OPENAI,
                processing_time_ms=processing_time
            )
    
    async def speech_to_text(self, request: STTRequest) -> STTResponse:
        """Convert speech to text using OpenAI Whisper"""
        start_time = time.time()
        
        logger.info(f"--- OpenAI Whisper STT Request ---")
        logger.info(f"Audio data size: {len(request.audio_data)} bytes")
        logger.info(f"Language: {request.language}")
        logger.info(f"Model: {request.model}")
        
        try:
            if not self.initialized:
                raise Exception("OpenAI processor not initialized")
            
            # Mock API call for now
            await asyncio.sleep(0.8)  # Whisper is slower
            
            # Generate mock transcription
            mock_text = f"[OpenAI Whisper STT] Transcribed {len(request.audio_data)} bytes of audio in {request.language}"
            
            processing_time = int((time.time() - start_time) * 1000)
            
            response = STTResponse(
                success=True,
                text=mock_text,
                confidence=0.95,
                language_detected=request.language,
                duration_ms=processing_time,
                engine_used=VoiceEngine.OPENAI,
                processing_time_ms=processing_time,
                segments=[
                    {
                        "start": 0.0,
                        "end": 2.5,
                        "text": mock_text,
                        "confidence": 0.95
                    }
                ]
            )
            
            logger.info(f"--- OpenAI Whisper STT Completed Successfully ---")
            logger.info(f"Transcription: '{mock_text[:100]}{'...' if len(mock_text) > 100 else ''}'")
            logger.info(f"Confidence: {response.confidence}")
            logger.info(f"Processing time: {processing_time}ms")
            
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"--- OpenAI Whisper STT Failed ---")
            logger.error(f"Error: {e}")
            
            return STTResponse(
                success=False,
                error=str(e),
                engine_used=VoiceEngine.OPENAI,
                processing_time_ms=processing_time
            )
    
    async def get_available_voices(self) -> List[VoiceProfile]:
        """Get available OpenAI TTS voices"""
        return [
            VoiceProfile(
                id="openai_alloy",
                name="Alloy",
                gender=VoiceGender.NEUTRAL,
                language="en",
                description="Neutral voice with balanced tone",
                engine=VoiceEngine.OPENAI,
                sample_rate=24000
            ),
            VoiceProfile(
                id="openai_echo",
                name="Echo",
                gender=VoiceGender.MALE,
                language="en",
                description="Male voice with clear articulation",
                engine=VoiceEngine.OPENAI,
                sample_rate=24000
            ),
            VoiceProfile(
                id="openai_nova",
                name="Nova",
                gender=VoiceGender.FEMALE,
                language="en",
                description="Female voice with warm tone",
                engine=VoiceEngine.OPENAI,
                sample_rate=24000
            )
        ]
    
    def _generate_mock_audio(self, text: str) -> bytes:
        """Generate mock audio data for testing"""
        # Simple mock audio data
        duration_ms = len(text) * 60
        sample_rate = 24000
        samples = int(sample_rate * duration_ms / 1000)
        
        # Generate simple audio data
        audio_data = b'\x00' * (samples * 2)  # 16-bit silence
        return audio_data


class WakeWordDetector:
    """Wake word detection using simple keyword matching (mock implementation)"""
    
    def __init__(self, config: WakeWordConfig):
        self.config = config
        self.is_listening = False
        self.detection_callback: Optional[Callable[[str], None]] = None
        self.audio_buffer = queue.Queue()
        self.detection_thread: Optional[threading.Thread] = None
        
        logger.info(f"Wake word detector created for words: {config.wake_words}")
    
    def start_listening(self, callback: Callable[[str], None]) -> bool:
        """Start listening for wake words"""
        try:
            if self.is_listening:
                logger.warning("Wake word detector already listening")
                return True
            
            self.detection_callback = callback
            self.is_listening = True
            
            # Start detection thread
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            
            logger.info(f"Wake word detector started, listening for: {self.config.wake_words}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting wake word detector: {e}")
            return False
    
    def stop_listening(self) -> None:
        """Stop listening for wake words"""
        if not self.is_listening:
            return
        
        self.is_listening = False
        self.detection_callback = None
        
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
        
        logger.info("Wake word detector stopped")
    
    def process_audio(self, audio_data: bytes) -> None:
        """Process audio data for wake word detection"""
        if self.is_listening:
            try:
                self.audio_buffer.put(audio_data, block=False)
            except queue.Full:
                # Remove oldest audio data
                try:
                    self.audio_buffer.get_nowait()
                    self.audio_buffer.put(audio_data, block=False)
                except queue.Empty:
                    pass
    
    def _detection_loop(self) -> None:
        """Main detection loop (mock implementation)"""
        logger.debug("Wake word detection loop started")
        
        last_detection = 0
        
        while self.is_listening:
            try:
                # Get audio data with timeout
                audio_data = self.audio_buffer.get(timeout=0.1)
                
                # Mock detection - simulate wake word detection every 10 seconds
                current_time = time.time()
                if current_time - last_detection > 10:  # 10 seconds
                    # Simulate wake word detection
                    detected_word = self.config.wake_words[0]
                    logger.info(f"Mock wake word detected: '{detected_word}'")
                    
                    if self.detection_callback:
                        self.detection_callback(detected_word)
                    
                    last_detection = current_time
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in wake word detection loop: {e}")
                break
        
        logger.debug("Wake word detection loop stopped")


class VoiceActivityDetector:
    """Voice Activity Detection using simple energy-based approach (mock implementation)"""
    
    def __init__(self, config: VADConfig):
        self.config = config
        self.is_active = False
        self.energy_threshold = 1000  # Mock threshold
        self.silence_counter = 0
        self.speech_counter = 0
        
        logger.info(f"Voice Activity Detector created with aggressiveness: {config.aggressiveness}")
    
    def process_frame(self, audio_frame: bytes) -> bool:
        """Process audio frame and return True if speech is detected"""
        try:
            # Mock VAD - calculate simple energy
            energy = sum(abs(b) for b in audio_frame)
            
            # Simple threshold-based detection
            is_speech = energy > self.energy_threshold
            
            if is_speech:
                self.speech_counter += 1
                self.silence_counter = 0
            else:
                self.silence_counter += 1
                self.speech_counter = max(0, self.speech_counter - 1)
            
            # Determine if currently in speech
            speech_active = self.speech_counter > 2  # Require multiple frames
            
            if speech_active != self.is_active:
                self.is_active = speech_active
                logger.debug(f"VAD state changed: {'SPEECH' if speech_active else 'SILENCE'}")
            
            return speech_active
            
        except Exception as e:
            logger.error(f"Error in VAD processing: {e}")
            return False
    
    def reset(self) -> None:
        """Reset VAD state"""
        self.is_active = False
        self.silence_counter = 0
        self.speech_counter = 0
        logger.debug("VAD state reset")


class UnifiedVoiceProcessor:
    """Unified voice processor that manages multiple engines and provides advanced features"""
    
    def __init__(self):
        self.processors: Dict[VoiceEngine, VoiceProcessorInterface] = {}
        self.wake_word_detector: Optional[WakeWordDetector] = None
        self.vad: Optional[VoiceActivityDetector] = None
        self.initialized = False
        self.default_tts_engine = VoiceEngine.ELEVENLABS
        self.default_stt_engine = VoiceEngine.OPENAI
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        
        logger.info("Unified voice processor created")
    
    async def initialize(self, 
                        elevenlabs_api_key: Optional[str] = None,
                        openai_api_key: Optional[str] = None) -> bool:
        """Initialize all voice processors"""
        logger.info("=== Initializing Unified Voice Processor ===")
        
        try:
            # Initialize ElevenLabs processor
            if elevenlabs_api_key or os.getenv('ELEVENLABS_API_KEY'):
                elevenlabs_processor = ElevenLabsProcessor(elevenlabs_api_key)
                if await elevenlabs_processor.initialize():
                    self.processors[VoiceEngine.ELEVENLABS] = elevenlabs_processor
                    logger.info("✓ ElevenLabs processor initialized")
                else:
                    logger.warning("✗ ElevenLabs processor initialization failed")
            
            # Initialize OpenAI processor
            if openai_api_key or os.getenv('OPENAI_API_KEY'):
                openai_processor = OpenAIProcessor(openai_api_key)
                if await openai_processor.initialize():
                    self.processors[VoiceEngine.OPENAI] = openai_processor
                    logger.info("✓ OpenAI processor initialized")
                else:
                    logger.warning("✗ OpenAI processor initialization failed")
            
            # Load all available voice profiles
            await self._load_voice_profiles()
            
            if self.processors:
                self.initialized = True
                logger.info(f"=== Unified Voice Processor Initialized Successfully ===")
                logger.info(f"Active engines: {list(self.processors.keys())}")
                logger.info(f"Available voices: {len(self.voice_profiles)}")
                return True
            else:
                logger.error("No voice processors initialized")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing unified voice processor: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown all processors"""
        logger.info("Shutting down unified voice processor")
        
        # Stop wake word detector
        if self.wake_word_detector:
            self.wake_word_detector.stop_listening()
        
        # Shutdown all processors
        for processor in self.processors.values():
            await processor.shutdown()
        
        self.processors.clear()
        self.voice_profiles.clear()
        self.initialized = False
        
        logger.info("Unified voice processor shutdown complete")
    
    async def text_to_speech(self, 
                            text: str,
                            voice_id: Optional[str] = None,
                            engine: Optional[VoiceEngine] = None,
                            **kwargs) -> TTSResponse:
        """Convert text to speech using specified or default engine"""
        if not self.initialized:
            return TTSResponse(success=False, error="Voice processor not initialized")
        
        # Determine engine to use
        engine = engine or self.default_tts_engine
        
        if engine not in self.processors:
            return TTSResponse(success=False, error=f"Engine {engine} not available")
        
        # Get voice profile
        voice_profile = self._get_voice_profile(voice_id, engine)
        
        # Create TTS request
        request = TTSRequest(
            text=text,
            voice_profile=voice_profile,
            speed=kwargs.get('speed', 1.0),
            pitch=kwargs.get('pitch', 1.0),
            volume=kwargs.get('volume', 1.0),
            output_format=kwargs.get('output_format', 'mp3'),
            quality=kwargs.get('quality', AudioQuality.MEDIUM)
        )
        
        # Process request
        return await self.processors[engine].text_to_speech(request)
    
    async def speech_to_text(self,
                            audio_data: bytes,
                            language: str = "en",
                            engine: Optional[VoiceEngine] = None,
                            **kwargs) -> STTResponse:
        """Convert speech to text using specified or default engine"""
        if not self.initialized:
            return STTResponse(success=False, error="Voice processor not initialized")
        
        # Determine engine to use
        engine = engine or self.default_stt_engine
        
        if engine not in self.processors:
            return STTResponse(success=False, error=f"Engine {engine} not available")
        
        # Create STT request
        request = STTRequest(
            audio_data=audio_data,
            language=language,
            model=kwargs.get('model', 'whisper-1'),
            temperature=kwargs.get('temperature', 0.0),
            engine=engine,
            enable_vad=kwargs.get('enable_vad', True),
            quality=kwargs.get('quality', AudioQuality.MEDIUM)
        )
        
        # Process request
        return await self.processors[engine].speech_to_text(request)
    
    def setup_wake_word_detection(self, config: WakeWordConfig, callback: Callable[[str], None]) -> bool:
        """Setup wake word detection"""
        try:
            self.wake_word_detector = WakeWordDetector(config)
            return self.wake_word_detector.start_listening(callback)
        except Exception as e:
            logger.error(f"Error setting up wake word detection: {e}")
            return False
    
    def setup_voice_activity_detection(self, config: VADConfig) -> bool:
        """Setup voice activity detection"""
        try:
            self.vad = VoiceActivityDetector(config)
            logger.info("Voice activity detection setup complete")
            return True
        except Exception as e:
            logger.error(f"Error setting up VAD: {e}")
            return False
    
    def process_audio_frame(self, audio_frame: bytes) -> Dict[str, Any]:
        """Process audio frame through VAD and wake word detection"""
        result = {
            'speech_detected': False,
            'wake_word_detected': False,
            'wake_word': None
        }
        
        try:
            # Process through VAD
            if self.vad:
                result['speech_detected'] = self.vad.process_frame(audio_frame)
            
            # Process through wake word detector
            if self.wake_word_detector:
                self.wake_word_detector.process_audio(audio_frame)
            
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
        
        return result
    
    def get_available_voices(self, engine: Optional[VoiceEngine] = None) -> List[VoiceProfile]:
        """Get available voice profiles"""
        if engine:
            return [v for v in self.voice_profiles.values() if v.engine == engine]
        else:
            return list(self.voice_profiles.values())
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about available engines"""
        return {
            'initialized': self.initialized,
            'available_engines': list(self.processors.keys()),
            'default_tts_engine': self.default_tts_engine,
            'default_stt_engine': self.default_stt_engine,
            'voice_count': len(self.voice_profiles),
            'wake_word_active': self.wake_word_detector is not None and self.wake_word_detector.is_listening,
            'vad_active': self.vad is not None
        }
    
    async def _load_voice_profiles(self) -> None:
        """Load voice profiles from all processors"""
        self.voice_profiles.clear()
        
        for engine, processor in self.processors.items():
            try:
                voices = await processor.get_available_voices()
                for voice in voices:
                    self.voice_profiles[voice.id] = voice
                logger.debug(f"Loaded {len(voices)} voices from {engine}")
            except Exception as e:
                logger.error(f"Error loading voices from {engine}: {e}")
    
    def _get_voice_profile(self, voice_id: Optional[str], engine: VoiceEngine) -> VoiceProfile:
        """Get voice profile by ID or return default for engine"""
        if voice_id and voice_id in self.voice_profiles:
            return self.voice_profiles[voice_id]
        
        # Return first voice for the engine
        for voice in self.voice_profiles.values():
            if voice.engine == engine:
                return voice
        
        # Fallback default voice
        return VoiceProfile(
            id="default",
            name="Default Voice",
            gender=VoiceGender.NEUTRAL,
            language="en",
            engine=engine
        )


# Example usage and testing
if __name__ == "__main__":
    async def test_voice_processing():
        """Test the unified voice processor"""
        logger.info("=== Starting Voice Processing Test ===")
        
        # Create and initialize processor
        processor = UnifiedVoiceProcessor()
        success = await processor.initialize()
        
        if not success:
            logger.error("Failed to initialize voice processor")
            return
        
        # Get engine info
        info = processor.get_engine_info()
        logger.info(f"Engine info: {info}")
        
        # Get available voices
        voices = processor.get_available_voices()
        logger.info(f"Available voices: {len(voices)}")
        for voice in voices[:5]:  # Show first 5
            logger.info(f"  {voice.name} ({voice.id}) - {voice.engine.value} - {voice.gender.value}")
        
        # Test TTS
        logger.info("\n--- Testing Text-to-Speech ---")
        tts_response = await processor.text_to_speech(
            "Hello, this is a test of the voice processing system.",
            speed=1.2
        )
        
        if tts_response.success:
            logger.info(f"TTS Success: {len(tts_response.audio_data)} bytes of audio")
            logger.info(f"Duration: {tts_response.duration_ms}ms")
            logger.info(f"Processing time: {tts_response.processing_time_ms}ms")
        else:
            logger.error(f"TTS Failed: {tts_response.error}")
        
        # Test STT
        logger.info("\n--- Testing Speech-to-Text ---")
        mock_audio = b'\x00' * 16000  # 1 second of silence at 16kHz
        stt_response = await processor.speech_to_text(mock_audio, language="en")
        
        if stt_response.success:
            logger.info(f"STT Success: '{stt_response.text}'")
            logger.info(f"Confidence: {stt_response.confidence}")
            logger.info(f"Processing time: {stt_response.processing_time_ms}ms")
        else:
            logger.error(f"STT Failed: {stt_response.error}")
        
        # Test wake word detection
        logger.info("\n--- Testing Wake Word Detection ---")
        wake_config = WakeWordConfig(
            wake_words=["hey assistant", "computer"],
            sensitivity=0.7
        )
        
        def wake_word_callback(word: str):
            logger.info(f"Wake word detected: '{word}'")
        
        wake_success = processor.setup_wake_word_detection(wake_config, wake_word_callback)
        logger.info(f"Wake word detection setup: {wake_success}")
        
        # Test VAD
        logger.info("\n--- Testing Voice Activity Detection ---")
        vad_config = VADConfig(aggressiveness=2)
        vad_success = processor.setup_voice_activity_detection(vad_config)
        logger.info(f"VAD setup: {vad_success}")
        
        # Test audio frame processing
        if vad_success:
            mock_frame = b'\x00' * 480  # 30ms frame at 16kHz
            result = processor.process_audio_frame(mock_frame)
            logger.info(f"Audio frame processing result: {result}")
        
        # Wait a bit to see wake word detection
        logger.info("Waiting 12 seconds to demonstrate wake word detection...")
        await asyncio.sleep(12)
        
        # Shutdown
        await processor.shutdown()
        logger.info("=== Voice Processing Test Complete ===")
    
    # Run test
    asyncio.run(test_voice_processing())