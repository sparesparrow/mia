"""
MIA Universal: Audio Assistant MCP Server
Handles voice processing, music playback, and audio output management
"""

import asyncio
import logging
import os
import json
import subprocess
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import aiohttp
import websockets
from datetime import datetime

# Import our MCP framework
from mcp_framework import (
    MCPServer, MCPClient, MCPMessage, MCPTransport, 
    WebSocketTransport, Tool, create_tool
)


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Audio device information"""
    id: str
    name: str
    type: str  # speakers, headphones, bluetooth, rtsp
    is_active: bool = False


@dataclass
class AudioZone:
    """Audio zone configuration"""
    name: str
    devices: List[str]  # Device IDs
    volume: int = 50
    is_active: bool = False


class AudioManager:
    """Cross-platform audio management with enhanced error handling and debugging"""
    
    def __init__(self):
        self.devices: Dict[str, AudioDevice] = {}
        self.zones: Dict[str, AudioZone] = {}
        self.current_track: Optional[Dict[str, Any]] = None
        self.is_playing = False
        self.volume = 50
        self.platform = self._detect_platform()
        logger.info(f"AudioManager initializing on platform: {self.platform}")
        self._discover_devices()
        self._setup_default_zones()
        logger.info(f"AudioManager initialized with {len(self.devices)} devices and {len(self.zones)} zones")
    
    def _detect_platform(self) -> str:
        """Detect the current platform for audio system selection"""
        import platform
        system = platform.system().lower()
        if system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        elif system == "windows":
            return "windows"
        else:
            logger.warning(f"Unknown platform: {system}, defaulting to linux")
            return "linux"
    
    def _discover_devices(self):
        """Discover available audio devices with enhanced platform detection"""
        logger.info(f"Starting device discovery for platform: {self.platform}")
        try:
            if self.platform == "linux":
                self._discover_linux_devices()
            elif self.platform == "macos":
                self._discover_macos_devices()
            elif self.platform == "windows":
                self._discover_windows_devices()
            else:
                logger.warning(f"Unsupported platform: {self.platform}")
                self._add_fallback_device()
        except Exception as e:
            logger.error(f"Error discovering audio devices on {self.platform}: {e}")
            self._add_fallback_device()
        
        logger.info(f"Device discovery completed. Found devices: {list(self.devices.keys())}")
    
    def _add_fallback_device(self):
        """Add fallback default device when discovery fails"""
        logger.info("Adding fallback default audio device")
        self.devices["default"] = AudioDevice("default", "Default Audio", "speakers", True)
    
    def _discover_linux_devices(self):
        """Discover Linux audio devices using PipeWire/ALSA with enhanced error handling"""
        logger.info("Attempting Linux audio device discovery")
        pipewire_found = False
        alsa_found = False
        
        try:
            # Try PipeWire first
            logger.debug("Checking for PipeWire audio system")
            result = subprocess.run(['pw-cli', 'list-objects'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("PipeWire detected, parsing device list")
                pipewire_found = True
                # Enhanced PipeWire parsing would go here
                # For now, adding common device types
                self.devices["speakers"] = AudioDevice("speakers", "PipeWire Built-in Speakers", "speakers", True)
                self.devices["headphones"] = AudioDevice("headphones", "PipeWire Headphones", "headphones", False)
                logger.info("Added PipeWire audio devices")
            else:
                logger.debug(f"PipeWire not available, exit code: {result.returncode}")
        except FileNotFoundError:
            logger.debug("pw-cli command not found, PipeWire not installed")
        except subprocess.TimeoutExpired:
            logger.warning("PipeWire device discovery timed out")
        except Exception as e:
            logger.warning(f"PipeWire discovery error: {e}")
        
        if not pipewire_found:
            try:
                # Fallback to ALSA
                logger.debug("Checking for ALSA audio system")
                result = subprocess.run(['aplay', '-l'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info("ALSA detected, parsing device list")
                    alsa_found = True
                    # Parse ALSA output for actual devices
                    output_lines = result.stdout.split('\n')
                    device_count = 0
                    for line in output_lines:
                        if 'card' in line.lower() and ':' in line:
                            device_count += 1
                            logger.debug(f"Found ALSA device: {line.strip()}")
                    
                    if device_count > 0:
                        self.devices["default"] = AudioDevice("default", "ALSA Default", "speakers", True)
                        logger.info(f"Added ALSA default device (found {device_count} cards)")
                    else:
                        logger.warning("ALSA detected but no audio cards found")
                else:
                    logger.debug(f"ALSA not available, exit code: {result.returncode}")
            except FileNotFoundError:
                logger.debug("aplay command not found, ALSA not installed")
            except subprocess.TimeoutExpired:
                logger.warning("ALSA device discovery timed out")
            except Exception as e:
                logger.warning(f"ALSA discovery error: {e}")
        
        if not pipewire_found and not alsa_found:
            logger.warning("No Linux audio system detected (neither PipeWire nor ALSA)")
            self._add_fallback_device()
    
    def _discover_macos_devices(self):
        """Discover macOS audio devices using Core Audio"""
        logger.info("Attempting macOS audio device discovery")
        try:
            # Try to use system_profiler for device enumeration
            result = subprocess.run(['system_profiler', 'SPAudioDataType', '-json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("macOS audio devices detected via system_profiler")
                # Parse JSON output for actual devices
                import json
                try:
                    data = json.loads(result.stdout)
                    # Simplified parsing - in real implementation would parse full structure
                    self.devices["speakers"] = AudioDevice("speakers", "macOS Built-in Speakers", "speakers", True)
                    self.devices["headphones"] = AudioDevice("headphones", "macOS Headphones", "headphones", False)
                    logger.info("Added macOS Core Audio devices")
                except json.JSONDecodeError:
                    logger.warning("Could not parse system_profiler JSON output")
                    self._add_fallback_device()
            else:
                logger.warning(f"system_profiler failed with exit code: {result.returncode}")
                self._add_fallback_device()
        except FileNotFoundError:
            logger.debug("system_profiler command not found")
            self._add_fallback_device()
        except subprocess.TimeoutExpired:
            logger.warning("macOS device discovery timed out")
            self._add_fallback_device()
        except Exception as e:
            logger.warning(f"macOS device discovery error: {e}")
            self._add_fallback_device()
    
    def _discover_windows_devices(self):
        """Discover Windows audio devices with enhanced error handling"""
        logger.info("Attempting Windows audio device discovery")
        try:
            # Try PowerShell to get audio devices
            ps_command = "Get-WmiObject -Class Win32_SoundDevice | Select-Object Name, Status"
            result = subprocess.run(['powershell', '-Command', ps_command], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("Windows audio devices detected via PowerShell")
                # Parse PowerShell output
                output_lines = result.stdout.split('\n')
                device_count = 0
                for line in output_lines:
                    if line.strip() and not line.startswith('Name') and not line.startswith('----'):
                        device_count += 1
                        logger.debug(f"Found Windows audio device: {line.strip()}")
                
                if device_count > 0:
                    self.devices["speakers"] = AudioDevice("speakers", "Windows Default Speakers", "speakers", True)
                    self.devices["headphones"] = AudioDevice("headphones", "Windows Headphones", "headphones", False)
                    logger.info(f"Added Windows audio devices (found {device_count} devices)")
                else:
                    logger.warning("PowerShell executed but no audio devices found")
                    self._add_fallback_device()
            else:
                logger.warning(f"PowerShell command failed with exit code: {result.returncode}")
                self._add_fallback_device()
        except FileNotFoundError:
            logger.debug("PowerShell not found, trying fallback")
            # Fallback approach for Windows
            try:
                self.devices["speakers"] = AudioDevice("speakers", "Windows Default Speakers", "speakers", True)
                self.devices["headphones"] = AudioDevice("headphones", "Windows Headphones", "headphones", False)
                logger.info("Added Windows fallback audio devices")
            except Exception as e:
                logger.warning(f"Windows fallback device creation failed: {e}")
                self._add_fallback_device()
        except subprocess.TimeoutExpired:
            logger.warning("Windows device discovery timed out")
            self._add_fallback_device()
        except Exception as e:
            logger.warning(f"Windows device discovery error: {e}")
            self._add_fallback_device()
    
    def _setup_default_zones(self):
        """Setup default audio zones"""
        self.zones["kitchen"] = AudioZone("kitchen", ["speakers"], 60, False)
        self.zones["living_room"] = AudioZone("living_room", ["speakers"], 50, True)
        self.zones["bedroom"] = AudioZone("bedroom", ["headphones"], 30, False)
        self.zones["office"] = AudioZone("office", ["speakers"], 40, False)
    
    async def switch_output(self, device_type: str, zone: Optional[str] = None) -> bool:
        """Switch audio output to specified device with comprehensive error handling and debugging"""
        logger.info(f"--- Audio Output Switch Request ---")
        logger.info(f"Target device: {device_type}")
        logger.info(f"Target zone: {zone}")
        logger.info(f"Available devices: {list(self.devices.keys())}")
        logger.info(f"Available zones: {list(self.zones.keys())}")
        
        try:
            # Validate device exists
            if device_type not in self.devices:
                logger.error(f"Device '{device_type}' not found in available devices: {list(self.devices.keys())}")
                return False
            
            # Get current active device for logging
            current_device = self.get_active_device()
            if current_device:
                logger.info(f"Currently active device: {current_device.name} ({current_device.id})")
            else:
                logger.info("No currently active device")
            
            # Deactivate current devices
            deactivated_count = 0
            for device in self.devices.values():
                if device.is_active:
                    device.is_active = False
                    deactivated_count += 1
                    logger.debug(f"Deactivated device: {device.name}")
            
            logger.info(f"Deactivated {deactivated_count} devices")
            
            # Activate target device
            target_device = self.devices[device_type]
            target_device.is_active = True
            logger.info(f"Activated target device: {target_device.name} ({target_device.id})")
            
            # Handle zone configuration
            if zone:
                if zone not in self.zones:
                    logger.warning(f"Zone '{zone}' not found, available zones: {list(self.zones.keys())}")
                    # Create zone on-the-fly
                    self.zones[zone] = AudioZone(zone, [device_type], 50, True)
                    logger.info(f"Created new zone: {zone}")
                else:
                    target_zone = self.zones[zone]
                    
                    # Deactivate other zones
                    for zone_name, zone_obj in self.zones.items():
                        if zone_name != zone and zone_obj.is_active:
                            zone_obj.is_active = False
                            logger.debug(f"Deactivated zone: {zone_name}")
                    
                    # Activate target zone
                    target_zone.is_active = True
                    if device_type not in target_zone.devices:
                        target_zone.devices.append(device_type)
                        logger.info(f"Added device {device_type} to zone {zone}")
                    
                    logger.info(f"Activated zone: {zone} with devices: {target_zone.devices}")
            
            # Platform-specific audio switching would happen here
            await self._perform_platform_audio_switch(device_type, zone)
            
            logger.info(f"--- Audio Output Switch Completed Successfully ---")
            logger.info(f"Active device: {device_type}")
            logger.info(f"Active zone: {zone if zone else 'None'}")
            return True
            
        except Exception as e:
            logger.error(f"--- Audio Output Switch Failed ---")
            logger.error(f"Error switching audio output to {device_type}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return False
    
    async def _perform_platform_audio_switch(self, device_type: str, zone: Optional[str] = None):
        """Perform platform-specific audio switching"""
        logger.debug(f"Performing {self.platform} audio switch to {device_type}")
        
        if self.platform == "linux":
            await self._linux_audio_switch(device_type, zone)
        elif self.platform == "macos":
            await self._macos_audio_switch(device_type, zone)
        elif self.platform == "windows":
            await self._windows_audio_switch(device_type, zone)
        else:
            logger.warning(f"Audio switching not implemented for platform: {self.platform}")
    
    async def _linux_audio_switch(self, device_type: str, zone: Optional[str] = None):
        """Linux-specific audio switching"""
        try:
            # Try PipeWire first, then ALSA
            logger.debug("Attempting Linux audio switch")
            # In a real implementation, would use pw-cli or pactl commands
            logger.debug(f"Linux audio switch to {device_type} completed (mock)")
        except Exception as e:
            logger.warning(f"Linux audio switch error: {e}")
    
    async def _macos_audio_switch(self, device_type: str, zone: Optional[str] = None):
        """macOS-specific audio switching"""
        try:
            # Use Core Audio APIs or command line tools
            logger.debug("Attempting macOS audio switch")
            # In a real implementation, would use audiodevice command or Core Audio
            logger.debug(f"macOS audio switch to {device_type} completed (mock)")
        except Exception as e:
            logger.warning(f"macOS audio switch error: {e}")
    
    async def _windows_audio_switch(self, device_type: str, zone: Optional[str] = None):
        """Windows-specific audio switching"""
        try:
            # Use Windows Audio APIs
            logger.debug("Attempting Windows audio switch")
            # In a real implementation, would use WASAPI or PowerShell commands
            logger.debug(f"Windows audio switch to {device_type} completed (mock)")
        except Exception as e:
            logger.warning(f"Windows audio switch error: {e}")
    
    async def set_volume(self, level: int, zone: Optional[str] = None) -> bool:
        """Set volume level with comprehensive error handling and debugging"""
        logger.info(f"--- Volume Control Request ---")
        logger.info(f"Requested level: {level}")
        logger.info(f"Target zone: {zone}")
        
        try:
            # Validate and clamp volume to valid range
            original_level = level
            level = max(0, min(100, level))
            if original_level != level:
                logger.warning(f"Volume level clamped from {original_level} to {level}")
            
            if zone:
                if zone not in self.zones:
                    logger.error(f"Zone '{zone}' not found, available zones: {list(self.zones.keys())}")
                    return False
                
                old_volume = self.zones[zone].volume
                self.zones[zone].volume = level
                logger.info(f"Zone '{zone}' volume changed from {old_volume}% to {level}%")
                
                # Platform-specific zone volume setting
                await self._perform_platform_volume_set(level, zone)
            else:
                old_volume = self.volume
                self.volume = level
                logger.info(f"Global volume changed from {old_volume}% to {level}%")
                
                # Platform-specific global volume setting
                await self._perform_platform_volume_set(level, None)
            
            logger.info(f"--- Volume Control Completed Successfully ---")
            return True
            
        except Exception as e:
            logger.error(f"--- Volume Control Failed ---")
            logger.error(f"Error setting volume to {level}%: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return False
    
    async def _perform_platform_volume_set(self, level: int, zone: Optional[str] = None):
        """Perform platform-specific volume setting"""
        logger.debug(f"Performing {self.platform} volume set to {level}% for zone {zone}")
        
        if self.platform == "linux":
            await self._linux_volume_set(level, zone)
        elif self.platform == "macos":
            await self._macos_volume_set(level, zone)
        elif self.platform == "windows":
            await self._windows_volume_set(level, zone)
        else:
            logger.warning(f"Volume control not implemented for platform: {self.platform}")
    
    async def _linux_volume_set(self, level: int, zone: Optional[str] = None):
        """Linux-specific volume setting"""
        try:
            logger.debug("Attempting Linux volume set")
            # In a real implementation, would use pactl, amixer, or pw-cli commands
            logger.debug(f"Linux volume set to {level}% completed (mock)")
        except Exception as e:
            logger.warning(f"Linux volume set error: {e}")
    
    async def _macos_volume_set(self, level: int, zone: Optional[str] = None):
        """macOS-specific volume setting"""
        try:
            logger.debug("Attempting macOS volume set")
            # In a real implementation, would use osascript or Core Audio
            logger.debug(f"macOS volume set to {level}% completed (mock)")
        except Exception as e:
            logger.warning(f"macOS volume set error: {e}")
    
    async def _windows_volume_set(self, level: int, zone: Optional[str] = None):
        """Windows-specific volume setting"""
        try:
            logger.debug("Attempting Windows volume set")
            # In a real implementation, would use Windows Audio APIs or PowerShell
            logger.debug(f"Windows volume set to {level}% completed (mock)")
        except Exception as e:
            logger.warning(f"Windows volume set error: {e}")
    
    def get_active_device(self) -> Optional[AudioDevice]:
        """Get currently active audio device"""
        for device in self.devices.values():
            if device.is_active:
                return device
        return None
    
    def get_zone_info(self, zone_name: str) -> Optional[AudioZone]:
        """Get information about a specific zone"""
        return self.zones.get(zone_name)


class MusicService:
    """Enhanced music service interface with comprehensive error handling and debugging"""
    
    def __init__(self):
        self.current_track = None
        self.is_playing = False
        self.playlist = []
        self.supported_sources = ["local", "spotify", "apple", "youtube"]
        self.playback_history = []
        logger.info(f"MusicService initialized with supported sources: {self.supported_sources}")
    
    async def play(self, query: str, source: str = "local") -> Dict[str, Any]:
        """Play music based on query with enhanced error handling and debugging"""
        logger.info(f"--- Music Playback Request ---")
        logger.info(f"Query: '{query}'")
        logger.info(f"Source: {source}")
        logger.info(f"Current status: {'Playing' if self.is_playing else 'Stopped'}")
        
        try:
            # Validate source
            if source not in self.supported_sources:
                logger.warning(f"Unsupported source '{source}', falling back to 'local'")
                source = "local"
            
            # Stop current playback if any
            if self.is_playing and self.current_track:
                logger.info(f"Stopping current track: {self.current_track.get('title', 'Unknown')}")
                await self.stop()
            
            # Simulate music search and playback
            logger.debug(f"Searching for music: '{query}' in source: {source}")
            
            # Generate track info based on query and source
            track_info = await self._generate_track_info(query, source)
            
            # Update state
            self.current_track = track_info
            self.is_playing = True
            
            # Add to history
            self.playback_history.append({
                "query": query,
                "track": track_info,
                "timestamp": datetime.now().isoformat(),
                "source": source
            })
            
            # Keep history manageable
            if len(self.playback_history) > 100:
                self.playback_history = self.playback_history[-50:]
            
            result = {
                "status": "playing",
                "track": track_info,
                "message": f"Now playing: {track_info['title']} by {track_info['artist']}"
            }
            
            logger.info(f"--- Music Playback Started Successfully ---")
            logger.info(f"Track: {track_info['title']} by {track_info['artist']}")
            logger.info(f"Duration: {track_info['duration']}s")
            logger.info(f"Source: {source}")
            
            return result
            
        except Exception as e:
            logger.error(f"--- Music Playback Failed ---")
            logger.error(f"Error playing music '{query}' from {source}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            
            return {
                "status": "error",
                "track": None,
                "message": f"Error playing music: {str(e)}"
            }
    
    async def _generate_track_info(self, query: str, source: str) -> Dict[str, Any]:
        """Generate track information based on query and source"""
        logger.debug(f"Generating track info for query: '{query}', source: {source}")
        
        # Simulate different behavior based on source
        if source == "spotify":
            track_info = {
                "title": f"Spotify Track: {query}",
                "artist": "Spotify Artist",
                "album": "Spotify Album",
                "duration": 210,
                "source": source,
                "spotify_id": f"spotify:track:{hash(query) % 10000}",
                "quality": "320kbps"
            }
        elif source == "apple":
            track_info = {
                "title": f"Apple Music: {query}",
                "artist": "Apple Music Artist", 
                "album": "Apple Music Album",
                "duration": 195,
                "source": source,
                "apple_id": f"apple:{hash(query) % 10000}",
                "quality": "256kbps AAC"
            }
        elif source == "youtube":
            track_info = {
                "title": f"YouTube: {query}",
                "artist": "YouTube Creator",
                "album": "YouTube Video",
                "duration": 240,
                "source": source,
                "youtube_id": f"YT{hash(query) % 10000}",
                "quality": "128kbps"
            }
        else:  # local
            track_info = {
                "title": f"Local Track: {query}",
                "artist": "Local Artist",
                "album": "Local Album",
                "duration": 180,
                "source": source,
                "file_path": f"/music/{query.replace(' ', '_')}.mp3",
                "quality": "FLAC"
            }
        
        # Add common metadata
        track_info.update({
            "id": f"{source}_{hash(query)}",
            "query": query,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.debug(f"Generated track info: {track_info}")
        return track_info
    
    async def pause(self) -> Dict[str, Any]:
        """Pause playback with enhanced logging"""
        logger.info(f"--- Music Pause Request ---")
        logger.info(f"Current status: {'Playing' if self.is_playing else 'Already paused/stopped'}")
        
        try:
            if not self.is_playing:
                logger.warning("Attempted to pause when not playing")
                return {"status": "already_paused", "message": "Playback already paused or stopped"}
            
            if self.current_track:
                logger.info(f"Pausing track: {self.current_track.get('title', 'Unknown')}")
            
            self.is_playing = False
            logger.info("--- Music Pause Completed Successfully ---")
            return {"status": "paused", "message": "Playback paused"}
            
        except Exception as e:
            logger.error(f"--- Music Pause Failed ---")
            logger.error(f"Error pausing playback: {e}")
            return {"status": "error", "message": f"Error pausing playback: {str(e)}"}
    
    async def resume(self) -> Dict[str, Any]:
        """Resume playback with enhanced logging"""
        logger.info(f"--- Music Resume Request ---")
        logger.info(f"Current status: {'Already playing' if self.is_playing else 'Paused/stopped'}")
        
        try:
            if self.is_playing:
                logger.warning("Attempted to resume when already playing")
                return {"status": "already_playing", "message": "Playback already active"}
            
            if not self.current_track:
                logger.warning("Attempted to resume with no current track")
                return {"status": "no_track", "message": "No track to resume"}
            
            logger.info(f"Resuming track: {self.current_track.get('title', 'Unknown')}")
            self.is_playing = True
            
            logger.info("--- Music Resume Completed Successfully ---")
            return {"status": "playing", "message": "Playback resumed"}
            
        except Exception as e:
            logger.error(f"--- Music Resume Failed ---")
            logger.error(f"Error resuming playback: {e}")
            return {"status": "error", "message": f"Error resuming playback: {str(e)}"}
    
    async def stop(self) -> Dict[str, Any]:
        """Stop playback with enhanced logging"""
        logger.info(f"--- Music Stop Request ---")
        logger.info(f"Current status: {'Playing' if self.is_playing else 'Already stopped'}")
        
        try:
            if self.current_track:
                logger.info(f"Stopping track: {self.current_track.get('title', 'Unknown')}")
            else:
                logger.info("No current track to stop")
            
            self.is_playing = False
            self.current_track = None
            
            logger.info("--- Music Stop Completed Successfully ---")
            return {"status": "stopped", "message": "Playback stopped"}
            
        except Exception as e:
            logger.error(f"--- Music Stop Failed ---")
            logger.error(f"Error stopping playback: {e}")
            return {"status": "error", "message": f"Error stopping playback: {str(e)}"}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current playback status with comprehensive information"""
        logger.debug("--- Music Status Request ---")
        
        try:
            status = {
                "is_playing": self.is_playing,
                "current_track": self.current_track,
                "playlist_length": len(self.playlist),
                "supported_sources": self.supported_sources,
                "history_length": len(self.playback_history)
            }
            
            if self.current_track:
                status["current_track_info"] = {
                    "title": self.current_track.get("title", "Unknown"),
                    "artist": self.current_track.get("artist", "Unknown"),
                    "source": self.current_track.get("source", "Unknown"),
                    "duration": self.current_track.get("duration", 0)
                }
            
            logger.debug(f"Music status: Playing={self.is_playing}, Track={self.current_track.get('title', 'None') if self.current_track else 'None'}")
            return status
            
        except Exception as e:
            logger.error(f"Error getting music status: {e}")
            return {
                "error": str(e),
                "is_playing": False,
                "current_track": None,
                "playlist_length": 0
            }


class VoiceProcessor:
    """Enhanced voice processing with TTS/STT, comprehensive error handling and debugging"""
    
    def __init__(self):
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs default voice
        self.supported_languages = ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko"]
        self.tts_cache = {}  # Simple cache for TTS results
        self.stt_engines = ["elevenlabs", "openai-whisper", "mock"]
        
        logger.info(f"VoiceProcessor initialized")
        logger.info(f"ElevenLabs API: {'Configured' if self.elevenlabs_api_key else 'Not configured'}")
        logger.info(f"OpenAI API: {'Configured' if self.openai_api_key else 'Not configured'}")
        logger.info(f"Default voice ID: {self.default_voice_id}")
        logger.info(f"Supported languages: {len(self.supported_languages)}")
    
    async def text_to_speech(self, text: str, voice_id: Optional[str] = None, speed: float = 1.0, language: str = "en") -> str:
        """Convert text to speech with enhanced error handling and debugging"""
        logger.info(f"--- Text-to-Speech Request ---")
        logger.info(f"Text length: {len(text)} characters")
        logger.info(f"Text preview: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        logger.info(f"Voice ID: {voice_id or self.default_voice_id}")
        logger.info(f"Speed: {speed}")
        logger.info(f"Language: {language}")
        
        try:
            # Validate inputs
            if not text or not text.strip():
                logger.warning("Empty or whitespace-only text provided")
                return "[TTS Error] Empty text provided"
            
            # Clamp speed to reasonable range
            original_speed = speed
            speed = max(0.25, min(4.0, speed))
            if original_speed != speed:
                logger.warning(f"Speed clamped from {original_speed} to {speed}")
            
            # Validate language
            if language not in self.supported_languages:
                logger.warning(f"Unsupported language '{language}', falling back to 'en'")
                language = "en"
            
            voice_id = voice_id or self.default_voice_id
            
            # Check cache first
            cache_key = f"{hash(text)}_{voice_id}_{speed}_{language}"
            if cache_key in self.tts_cache:
                logger.debug("Using cached TTS result")
                return self.tts_cache[cache_key]
            
            # Determine TTS engine
            if self.elevenlabs_api_key:
                result = await self._elevenlabs_tts(text, voice_id, speed, language)
            elif self.openai_api_key:
                result = await self._openai_tts(text, voice_id, speed, language)
            else:
                logger.warning("No TTS API keys configured, using mock TTS")
                result = await self._mock_tts(text, voice_id, speed, language)
            
            # Cache result
            self.tts_cache[cache_key] = result
            if len(self.tts_cache) > 100:  # Keep cache manageable
                # Remove oldest entries
                keys_to_remove = list(self.tts_cache.keys())[:50]
                for key in keys_to_remove:
                    del self.tts_cache[key]
            
            logger.info(f"--- Text-to-Speech Completed Successfully ---")
            logger.info(f"Result length: {len(result)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"--- Text-to-Speech Failed ---")
            logger.error(f"Error in text-to-speech: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return f"[TTS Error] {str(e)}"
    
    async def _elevenlabs_tts(self, text: str, voice_id: str, speed: float, language: str) -> str:
        """ElevenLabs TTS implementation"""
        logger.debug("Using ElevenLabs TTS")
        try:
            # In a real implementation, you would call ElevenLabs API
            # This is a mock implementation
            await asyncio.sleep(0.1)  # Simulate API call
            return f"[ElevenLabs TTS] {text} (voice: {voice_id}, speed: {speed}, lang: {language})"
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            return await self._mock_tts(text, voice_id, speed, language)
    
    async def _openai_tts(self, text: str, voice_id: str, speed: float, language: str) -> str:
        """OpenAI TTS implementation"""
        logger.debug("Using OpenAI TTS")
        try:
            # In a real implementation, you would call OpenAI TTS API
            # This is a mock implementation
            await asyncio.sleep(0.1)  # Simulate API call
            return f"[OpenAI TTS] {text} (voice: {voice_id}, speed: {speed}, lang: {language})"
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            return await self._mock_tts(text, voice_id, speed, language)
    
    async def _mock_tts(self, text: str, voice_id: str, speed: float, language: str) -> str:
        """Mock TTS implementation"""
        logger.debug("Using Mock TTS")
        await asyncio.sleep(0.05)  # Simulate processing
        return f"[Mock TTS] {text} (voice: {voice_id}, speed: {speed}, lang: {language})"
    
    async def speech_to_text(self, audio_data: bytes, language: str = "en", engine: str = "auto") -> str:
        """Convert speech to text with enhanced error handling and debugging"""
        logger.info(f"--- Speech-to-Text Request ---")
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        logger.info(f"Language: {language}")
        logger.info(f"Engine: {engine}")
        
        try:
            # Validate inputs
            if not audio_data:
                logger.warning("Empty audio data provided")
                return "[STT Error] Empty audio data"
            
            if len(audio_data) < 1024:  # Minimum reasonable audio size
                logger.warning(f"Audio data very small: {len(audio_data)} bytes")
            
            # Validate language
            if language not in self.supported_languages:
                logger.warning(f"Unsupported language '{language}', falling back to 'en'")
                language = "en"
            
            # Determine STT engine
            if engine == "auto":
                if self.elevenlabs_api_key:
                    engine = "elevenlabs"
                elif self.openai_api_key:
                    engine = "openai-whisper"
                else:
                    engine = "mock"
            
            if engine not in self.stt_engines:
                logger.warning(f"Unknown STT engine '{engine}', falling back to 'mock'")
                engine = "mock"
            
            # Process audio
            if engine == "elevenlabs" and self.elevenlabs_api_key:
                result = await self._elevenlabs_stt(audio_data, language)
            elif engine == "openai-whisper" and self.openai_api_key:
                result = await self._openai_whisper_stt(audio_data, language)
            else:
                logger.warning("No STT API keys configured or engine unavailable, using mock STT")
                result = await self._mock_stt(audio_data, language)
            
            logger.info(f"--- Speech-to-Text Completed Successfully ---")
            logger.info(f"Transcription length: {len(result)} characters")
            logger.info(f"Transcription preview: '{result[:100]}{'...' if len(result) > 100 else ''}'")
            
            return result
            
        except Exception as e:
            logger.error(f"--- Speech-to-Text Failed ---")
            logger.error(f"Error in speech-to-text: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return f"[STT Error] {str(e)}"
    
    async def _elevenlabs_stt(self, audio_data: bytes, language: str) -> str:
        """ElevenLabs STT implementation"""
        logger.debug("Using ElevenLabs STT")
        try:
            # In a real implementation, you would call ElevenLabs STT API
            await asyncio.sleep(0.2)  # Simulate API call
            return f"[ElevenLabs STT] Transcribed audio in {language} ({len(audio_data)} bytes)"
        except Exception as e:
            logger.error(f"ElevenLabs STT error: {e}")
            return await self._mock_stt(audio_data, language)
    
    async def _openai_whisper_stt(self, audio_data: bytes, language: str) -> str:
        """OpenAI Whisper STT implementation"""
        logger.debug("Using OpenAI Whisper STT")
        try:
            # In a real implementation, you would call OpenAI Whisper API
            await asyncio.sleep(0.3)  # Simulate API call
            return f"[OpenAI Whisper STT] Transcribed audio in {language} ({len(audio_data)} bytes)"
        except Exception as e:
            logger.error(f"OpenAI Whisper STT error: {e}")
            return await self._mock_stt(audio_data, language)
    
    async def _mock_stt(self, audio_data: bytes, language: str) -> str:
        """Mock STT implementation"""
        logger.debug("Using Mock STT")
        await asyncio.sleep(0.1)  # Simulate processing
        return f"[Mock STT] Transcribed {len(audio_data)} bytes of audio in {language}"


class AudioAssistantMCP(MCPServer):
    """Enhanced AI Audio Assistant MCP Server with comprehensive debugging and error handling"""
    
    def __init__(self):
        logger.info("=== Initializing AI Audio Assistant MCP Server ===")
        super().__init__("ai-audio-assistant", "1.0.0")
        
        try:
            logger.info("Initializing AudioManager...")
            self.audio_manager = AudioManager()
            logger.info("AudioManager initialized successfully")
            
            logger.info("Initializing MusicService...")
            self.music_service = MusicService()
            logger.info("MusicService initialized successfully")
            
            logger.info("Initializing VoiceProcessor...")
            self.voice_processor = VoiceProcessor()
            logger.info("VoiceProcessor initialized successfully")
            
            logger.info("Setting up MCP tools...")
            self.setup_tools()
            logger.info(f"MCP tools setup completed - {len(self.tools)} tools available")
            
            logger.info("=== AI Audio Assistant MCP Server Initialization Complete ===")
            logger.info(f"Server name: {self.name}")
            logger.info(f"Server version: {self.version}")
            logger.info(f"Available tools: {list(self.tools.keys())}")
            
        except Exception as e:
            logger.error(f"=== AI Audio Assistant MCP Server Initialization Failed ===")
            logger.error(f"Initialization error: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            raise
    
    def setup_tools(self):
        """Setup audio assistant tools"""
        
        # Music playback tools
        play_music_tool = create_tool(
            name="play_music",
            description="Play music by artist, album, track, genre, or general query",
            schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for music (artist, song, genre, etc.)"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["spotify", "apple", "local", "youtube"],
                        "default": "local",
                        "description": "Music source service"
                    },
                    "zone": {
                        "type": "string",
                        "description": "Audio zone to play in (optional)"
                    }
                },
                "required": ["query"]
            },
            handler=self.handle_play_music
        )
        self.add_tool(play_music_tool)
        
        # Audio control tools
        pause_tool = create_tool(
            name="pause_playback",
            description="Pause current music playback",
            schema={"type": "object", "properties": {}},
            handler=self.handle_pause
        )
        self.add_tool(pause_tool)
        
        resume_tool = create_tool(
            name="resume_playback",
            description="Resume paused music playback",
            schema={"type": "object", "properties": {}},
            handler=self.handle_resume
        )
        self.add_tool(resume_tool)
        
        stop_tool = create_tool(
            name="stop_playback",
            description="Stop music playback",
            schema={"type": "object", "properties": {}},
            handler=self.handle_stop
        )
        self.add_tool(stop_tool)
        
        # Volume control
        volume_tool = create_tool(
            name="set_volume",
            description="Set audio volume level",
            schema={
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Volume level (0-100)"
                    },
                    "zone": {
                        "type": "string",
                        "description": "Audio zone (optional)"
                    }
                },
                "required": ["level"]
            },
            handler=self.handle_set_volume
        )
        self.add_tool(volume_tool)
        
        # Audio output switching
        switch_output_tool = create_tool(
            name="switch_audio_output",
            description="Switch audio output to different device",
            schema={
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "enum": ["speakers", "headphones", "bluetooth", "rtsp"],
                        "description": "Target audio device"
                    },
                    "zone": {
                        "type": "string",
                        "description": "Audio zone (optional)"
                    }
                },
                "required": ["device"]
            },
            handler=self.handle_switch_audio_output
        )
        self.add_tool(switch_output_tool)
        
        # Voice processing tools
        tts_tool = create_tool(
            name="text_to_speech",
            description="Convert text to speech",
            schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech"
                    },
                    "voice_id": {
                        "type": "string",
                        "description": "Voice ID for TTS (optional)"
                    },
                    "speed": {
                        "type": "number",
                        "minimum": 0.5,
                        "maximum": 2.0,
                        "default": 1.0,
                        "description": "Speech speed multiplier"
                    }
                },
                "required": ["text"]
            },
            handler=self.handle_text_to_speech
        )
        self.add_tool(tts_tool)
        
        # Status tools
        status_tool = create_tool(
            name="get_audio_status",
            description="Get current audio status and device information",
            schema={"type": "object", "properties": {}},
            handler=self.handle_get_status
        )
        self.add_tool(status_tool)
    
    async def handle_play_music(self, query: str, source: str = "local", zone: Optional[str] = None) -> str:
        """Handle music playback request"""
        try:
            result = await self.music_service.play(query, source)
            
            # Set zone if specified
            if zone:
                zone_info = self.audio_manager.get_zone_info(zone)
                if zone_info:
                    zone_info.is_active = True
                    logger.info(f"Activated audio zone: {zone}")
            
            return result["message"]
            
        except Exception as e:
            logger.error(f"Error playing music: {e}")
            return f"Error playing music: {str(e)}"
    
    async def handle_pause(self) -> str:
        """Handle pause request"""
        try:
            result = await self.music_service.pause()
            return result["message"]
        except Exception as e:
            return f"Error pausing playback: {str(e)}"
    
    async def handle_resume(self) -> str:
        """Handle resume request"""
        try:
            result = await self.music_service.resume()
            return result["message"]
        except Exception as e:
            return f"Error resuming playback: {str(e)}"
    
    async def handle_stop(self) -> str:
        """Handle stop request"""
        try:
            result = await self.music_service.stop()
            return result["message"]
        except Exception as e:
            return f"Error stopping playback: {str(e)}"
    
    async def handle_set_volume(self, level: int, zone: Optional[str] = None) -> str:
        """Handle volume change request"""
        try:
            success = await self.audio_manager.set_volume(level, zone)
            if success:
                zone_text = f" in zone {zone}" if zone else ""
                return f"Volume set to {level}%{zone_text}"
            else:
                return "Failed to set volume"
        except Exception as e:
            return f"Error setting volume: {str(e)}"
    
    async def handle_switch_audio_output(self, device: str, zone: Optional[str] = None) -> str:
        """Handle audio output switching"""
        try:
            success = await self.audio_manager.switch_output(device, zone)
            if success:
                zone_text = f" in zone {zone}" if zone else ""
                return f"Audio output switched to {device}{zone_text}"
            else:
                return f"Failed to switch to {device}"
        except Exception as e:
            return f"Error switching audio output: {str(e)}"
    
    async def handle_text_to_speech(self, text: str, voice_id: Optional[str] = None, speed: float = 1.0) -> str:
        """Handle text-to-speech request"""
        try:
            result = await self.voice_processor.text_to_speech(text, voice_id, speed)
            return f"TTS completed: {result}"
        except Exception as e:
            return f"Error in text-to-speech: {str(e)}"
    
    async def handle_get_status(self) -> Dict[str, Any]:
        """Handle status request"""
        try:
            music_status = await self.music_service.get_status()
            active_device = self.audio_manager.get_active_device()
            
            return {
                "music": music_status,
                "audio": {
                    "active_device": active_device.name if active_device else "None",
                    "global_volume": self.audio_manager.volume,
                    "available_devices": [d.name for d in self.audio_manager.devices.values()],
                    "zones": {name: {"volume": zone.volume, "active": zone.is_active} 
                             for name, zone in self.audio_manager.zones.items()}
                }
            }
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point for audio assistant"""
    logger.info("Starting AI Audio Assistant MCP Server")
    
    # Create audio assistant server
    audio_server = AudioAssistantMCP()
    
    # Start WebSocket server for MCP connections
    async def handle_websocket(websocket, path):
        """Handle WebSocket connections"""
        logger.info(f"New WebSocket connection: {websocket.remote_address}")
        transport = WebSocketTransport(websocket)
        
        try:
            await audio_server.serve(transport)
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
    
    # Start WebSocket server
    port = int(os.getenv('MCP_SERVER_PORT', 8082))
    start_server = websockets.serve(handle_websocket, "0.0.0.0", port)
    
    logger.info(f"Audio Assistant MCP Server listening on port {port}")
    
    try:
        await start_server
        # Keep the server running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Shutting down Audio Assistant MCP Server")


if __name__ == "__main__":
    asyncio.run(main())