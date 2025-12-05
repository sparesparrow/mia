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
    """Cross-platform audio management"""
    
    def __init__(self):
        self.devices: Dict[str, AudioDevice] = {}
        self.zones: Dict[str, AudioZone] = {}
        self.current_track: Optional[Dict[str, Any]] = None
        self.is_playing = False
        self.volume = 50
        self._discover_devices()
        self._setup_default_zones()
    
    def _discover_devices(self):
        """Discover available audio devices"""
        try:
            if os.name == 'posix':  # Linux/macOS
                self._discover_linux_devices()
            elif os.name == 'nt':  # Windows
                self._discover_windows_devices()
        except Exception as e:
            logger.error(f"Error discovering audio devices: {e}")
            # Add fallback default device
            self.devices["default"] = AudioDevice("default", "Default Audio", "speakers", True)
    
    def _discover_linux_devices(self):
        """Discover Linux audio devices using PipeWire/ALSA"""
        try:
            # Try PipeWire first
            result = subprocess.run(['pw-cli', 'list-objects'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse PipeWire output (simplified)
                self.devices["speakers"] = AudioDevice("speakers", "Built-in Speakers", "speakers", True)
                self.devices["headphones"] = AudioDevice("headphones", "Headphones", "headphones", False)
            else:
                # Fallback to ALSA
                result = subprocess.run(['aplay', '-l'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.devices["default"] = AudioDevice("default", "ALSA Default", "speakers", True)
        except Exception as e:
            logger.warning(f"Could not discover Linux audio devices: {e}")
    
    def _discover_windows_devices(self):
        """Discover Windows audio devices"""
        try:
            # In a real implementation, you would use Windows APIs
            self.devices["speakers"] = AudioDevice("speakers", "Default Speakers", "speakers", True)
            self.devices["headphones"] = AudioDevice("headphones", "Default Headphones", "headphones", False)
        except Exception as e:
            logger.warning(f"Could not discover Windows audio devices: {e}")
    
    def _setup_default_zones(self):
        """Setup default audio zones"""
        self.zones["kitchen"] = AudioZone("kitchen", ["speakers"], 60, False)
        self.zones["living_room"] = AudioZone("living_room", ["speakers"], 50, True)
        self.zones["bedroom"] = AudioZone("bedroom", ["headphones"], 30, False)
        self.zones["office"] = AudioZone("office", ["speakers"], 40, False)
    
    async def switch_output(self, device_type: str, zone: Optional[str] = None) -> bool:
        """Switch audio output to specified device"""
        try:
            logger.info(f"Switching audio output to {device_type} in zone {zone}")
            
            if device_type not in self.devices:
                logger.error(f"Device {device_type} not found")
                return False
            
            # Deactivate current devices
            for device in self.devices.values():
                device.is_active = False
            
            # Activate target device
            self.devices[device_type].is_active = True
            
            # Update zone if specified
            if zone and zone in self.zones:
                self.zones[zone].is_active = True
                if device_type not in self.zones[zone].devices:
                    self.zones[zone].devices.append(device_type)
            
            # In a real implementation, you would call system APIs to switch audio
            logger.info(f"Audio output switched to {device_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching audio output: {e}")
            return False
    
    async def set_volume(self, level: int, zone: Optional[str] = None) -> bool:
        """Set volume level"""
        try:
            # Clamp volume to valid range
            level = max(0, min(100, level))
            
            if zone and zone in self.zones:
                self.zones[zone].volume = level
                logger.info(f"Set volume to {level}% in zone {zone}")
            else:
                self.volume = level
                logger.info(f"Set global volume to {level}%")
            
            # In a real implementation, you would call system volume APIs
            return True
            
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
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
    """Abstract music service interface"""
    
    def __init__(self):
        self.current_track = None
        self.is_playing = False
        self.playlist = []
    
    async def play(self, query: str, source: str = "local") -> Dict[str, Any]:
        """Play music based on query"""
        logger.info(f"Playing music: {query} from {source}")
        
        # Simulate music playback
        track_info = {
            "title": f"Track for '{query}'",
            "artist": "AI Assistant",
            "album": "Generated Music",
            "duration": 180,
            "source": source
        }
        
        self.current_track = track_info
        self.is_playing = True
        
        return {
            "status": "playing",
            "track": track_info,
            "message": f"Now playing: {track_info['title']} by {track_info['artist']}"
        }
    
    async def pause(self) -> Dict[str, Any]:
        """Pause playback"""
        self.is_playing = False
        return {"status": "paused", "message": "Playback paused"}
    
    async def resume(self) -> Dict[str, Any]:
        """Resume playback"""
        self.is_playing = True
        return {"status": "playing", "message": "Playback resumed"}
    
    async def stop(self) -> Dict[str, Any]:
        """Stop playback"""
        self.is_playing = False
        self.current_track = None
        return {"status": "stopped", "message": "Playback stopped"}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        return {
            "is_playing": self.is_playing,
            "current_track": self.current_track,
            "playlist_length": len(self.playlist)
        }


class VoiceProcessor:
    """Voice processing with TTS/STT"""
    
    def __init__(self):
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs default voice
    
    async def text_to_speech(self, text: str, voice_id: Optional[str] = None, speed: float = 1.0) -> str:
        """Convert text to speech"""
        try:
            if not self.elevenlabs_api_key:
                logger.warning("ElevenLabs API key not configured, using mock TTS")
                return f"[TTS] {text}"
            
            voice_id = voice_id or self.default_voice_id
            
            # In a real implementation, you would call ElevenLabs API
            logger.info(f"Converting to speech: {text[:50]}...")
            
            # Mock response
            return f"[TTS Generated] {text}"
            
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return f"[TTS Error] {text}"
    
    async def speech_to_text(self, audio_data: bytes) -> str:
        """Convert speech to text"""
        try:
            # In a real implementation, you would use Whisper or ElevenLabs STT
            logger.info("Processing speech to text...")
            
            # Mock response
            return "[STT] Converted speech to text"
            
        except Exception as e:
            logger.error(f"Error in speech-to-text: {e}")
            return "[STT Error] Could not process audio"


class AudioAssistantMCP(MCPServer):
    """AI Audio Assistant MCP Server"""
    
    def __init__(self):
        super().__init__("ai-audio-assistant", "1.0.0")
        self.audio_manager = AudioManager()
        self.music_service = MusicService()
        self.voice_processor = VoiceProcessor()
        self.setup_tools()
    
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