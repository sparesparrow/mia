#!/usr/bin/env python3
"""
MIA Universal: Cross-Platform Audio Engine
Provides unified interface for PipeWire (Linux), WASAPI (Windows), and Core Audio (macOS)
"""

import asyncio
import logging
import os
import platform
import subprocess
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import threading
import time

# Setup logging
logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """Supported audio formats"""
    PCM_16 = "pcm_s16le"
    PCM_24 = "pcm_s24le" 
    PCM_32 = "pcm_s32le"
    FLOAT_32 = "pcm_f32le"
    FLOAT_64 = "pcm_f64le"


class DeviceType(Enum):
    """Audio device types"""
    PLAYBACK = "playback"
    CAPTURE = "capture"
    DUPLEX = "duplex"


class DeviceState(Enum):
    """Audio device states"""
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


@dataclass
class AudioDeviceInfo:
    """Comprehensive audio device information"""
    id: str
    name: str
    description: str
    device_type: DeviceType
    state: DeviceState
    is_default: bool = False
    sample_rates: List[int] = None
    formats: List[AudioFormat] = None
    channels: int = 2
    latency_ms: float = 0.0
    driver: str = "unknown"
    
    def __post_init__(self):
        if self.sample_rates is None:
            self.sample_rates = [44100, 48000]
        if self.formats is None:
            self.formats = [AudioFormat.PCM_16, AudioFormat.FLOAT_32]


@dataclass
class AudioStreamConfig:
    """Audio stream configuration"""
    device_id: str
    sample_rate: int = 48000
    format: AudioFormat = AudioFormat.FLOAT_32
    channels: int = 2
    buffer_size: int = 1024
    latency_ms: float = 10.0


class AudioEngineInterface(ABC):
    """Abstract interface for cross-platform audio engines"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the audio engine"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the audio engine"""
        pass
    
    @abstractmethod
    async def enumerate_devices(self, device_type: Optional[DeviceType] = None) -> List[AudioDeviceInfo]:
        """Enumerate available audio devices"""
        pass
    
    @abstractmethod
    async def get_default_device(self, device_type: DeviceType) -> Optional[AudioDeviceInfo]:
        """Get default device for specified type"""
        pass
    
    @abstractmethod
    async def set_default_device(self, device_id: str) -> bool:
        """Set default audio device"""
        pass
    
    @abstractmethod
    async def set_device_volume(self, device_id: str, volume: float) -> bool:
        """Set device volume (0.0 to 1.0)"""
        pass
    
    @abstractmethod
    async def get_device_volume(self, device_id: str) -> Optional[float]:
        """Get device volume (0.0 to 1.0)"""
        pass
    
    @abstractmethod
    async def create_stream(self, config: AudioStreamConfig) -> Optional[str]:
        """Create audio stream, returns stream ID"""
        pass
    
    @abstractmethod
    async def destroy_stream(self, stream_id: str) -> bool:
        """Destroy audio stream"""
        pass


class PipeWireEngine(AudioEngineInterface):
    """PipeWire audio engine for Linux"""
    
    def __init__(self):
        self.initialized = False
        self.devices: Dict[str, AudioDeviceInfo] = {}
        self.streams: Dict[str, Any] = {}
        logger.info("PipeWire audio engine created")
    
    async def initialize(self) -> bool:
        """Initialize PipeWire engine"""
        logger.info("--- Initializing PipeWire Audio Engine ---")
        
        try:
            # Check if PipeWire is available
            result = await asyncio.create_subprocess_exec(
                'pw-cli', 'info',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info("PipeWire daemon detected and accessible")
                self.initialized = True
                
                # Initial device enumeration
                await self.enumerate_devices()
                logger.info(f"PipeWire engine initialized with {len(self.devices)} devices")
                return True
            else:
                logger.error(f"PipeWire not accessible, return code: {result.returncode}")
                logger.error(f"stderr: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            logger.error("PipeWire tools not found (pw-cli missing)")
            return False
        except Exception as e:
            logger.error(f"Error initializing PipeWire: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown PipeWire engine"""
        logger.info("Shutting down PipeWire audio engine")
        
        # Destroy all streams
        for stream_id in list(self.streams.keys()):
            await self.destroy_stream(stream_id)
        
        self.initialized = False
        self.devices.clear()
        logger.info("PipeWire engine shutdown complete")
    
    async def enumerate_devices(self, device_type: Optional[DeviceType] = None) -> List[AudioDeviceInfo]:
        """Enumerate PipeWire devices"""
        logger.debug("Enumerating PipeWire devices")
        
        try:
            # Get device list from PipeWire
            result = await asyncio.create_subprocess_exec(
                'pw-cli', 'list-objects', 'Node',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to enumerate PipeWire devices: {stderr.decode()}")
                return []
            
            # Parse PipeWire output
            devices = await self._parse_pipewire_devices(stdout.decode())
            
            # Filter by device type if specified
            if device_type:
                devices = [d for d in devices if d.device_type == device_type]
            
            # Update internal device cache
            self.devices.clear()
            for device in devices:
                self.devices[device.id] = device
            
            logger.info(f"Found {len(devices)} PipeWire devices")
            return devices
            
        except Exception as e:
            logger.error(f"Error enumerating PipeWire devices: {e}")
            return []
    
    async def _parse_pipewire_devices(self, output: str) -> List[AudioDeviceInfo]:
        """Parse PipeWire device list output"""
        devices = []
        
        try:
            # Simplified parsing - in real implementation would parse full PipeWire protocol
            lines = output.split('\n')
            current_device = None
            
            for line in lines:
                line = line.strip()
                
                # Look for device nodes
                if 'object.serial' in line and 'Node' in line:
                    if current_device:
                        devices.append(current_device)
                    
                    # Extract device ID from line
                    device_id = f"pipewire_node_{len(devices)}"
                    current_device = AudioDeviceInfo(
                        id=device_id,
                        name="PipeWire Audio Device",
                        description="PipeWire managed audio device",
                        device_type=DeviceType.PLAYBACK,
                        state=DeviceState.ACTIVE,
                        driver="pipewire"
                    )
                
                # Extract device properties
                elif current_device and 'node.name' in line:
                    # Extract node name
                    if '"' in line:
                        name = line.split('"')[1]
                        current_device.name = name
                
                elif current_device and 'media.class' in line:
                    # Determine device type from media class
                    if 'Audio/Sink' in line:
                        current_device.device_type = DeviceType.PLAYBACK
                    elif 'Audio/Source' in line:
                        current_device.device_type = DeviceType.CAPTURE
            
            # Add last device
            if current_device:
                devices.append(current_device)
            
            logger.debug(f"Parsed {len(devices)} devices from PipeWire output")
            
        except Exception as e:
            logger.error(f"Error parsing PipeWire device list: {e}")
        
        return devices
    
    async def get_default_device(self, device_type: DeviceType) -> Optional[AudioDeviceInfo]:
        """Get default PipeWire device"""
        try:
            # Query default sink/source
            if device_type == DeviceType.PLAYBACK:
                cmd = ['pw-cli', 'info', '0']
            else:
                cmd = ['pw-cli', 'info', '1']
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Parse default device info
                # Simplified - return first available device of correct type
                for device in self.devices.values():
                    if device.device_type == device_type:
                        logger.debug(f"Default {device_type.value} device: {device.name}")
                        return device
            
        except Exception as e:
            logger.error(f"Error getting default PipeWire device: {e}")
        
        return None
    
    async def set_default_device(self, device_id: str) -> bool:
        """Set default PipeWire device"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return False
            
            device = self.devices[device_id]
            
            # Use pactl if available for setting default
            if device.device_type == DeviceType.PLAYBACK:
                cmd = ['pactl', 'set-default-sink', device.name]
            else:
                cmd = ['pactl', 'set-default-source', device.name]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            success = result.returncode == 0
            if success:
                logger.info(f"Set default {device.device_type.value} device to {device.name}")
            else:
                logger.error(f"Failed to set default device to {device.name}")
            
            return success
            
        except FileNotFoundError:
            logger.warning("pactl not available, cannot set default device")
            return False
        except Exception as e:
            logger.error(f"Error setting default PipeWire device: {e}")
            return False
    
    async def set_device_volume(self, device_id: str, volume: float) -> bool:
        """Set PipeWire device volume"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return False
            
            device = self.devices[device_id]
            volume_percent = max(0, min(100, int(volume * 100)))
            
            # Use pactl for volume control
            if device.device_type == DeviceType.PLAYBACK:
                cmd = ['pactl', 'set-sink-volume', device.name, f'{volume_percent}%']
            else:
                cmd = ['pactl', 'set-source-volume', device.name, f'{volume_percent}%']
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            success = result.returncode == 0
            if success:
                logger.debug(f"Set {device.name} volume to {volume_percent}%")
            else:
                logger.error(f"Failed to set volume for {device.name}")
            
            return success
            
        except FileNotFoundError:
            logger.warning("pactl not available, cannot set volume")
            return False
        except Exception as e:
            logger.error(f"Error setting PipeWire device volume: {e}")
            return False
    
    async def get_device_volume(self, device_id: str) -> Optional[float]:
        """Get PipeWire device volume"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return None
            
            device = self.devices[device_id]
            
            # Use pactl to get volume
            if device.device_type == DeviceType.PLAYBACK:
                cmd = ['pactl', 'get-sink-volume', device.name]
            else:
                cmd = ['pactl', 'get-source-volume', device.name]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Parse volume from output
                output = stdout.decode()
                if '%' in output:
                    # Extract percentage
                    for part in output.split():
                        if '%' in part:
                            volume_str = part.replace('%', '')
                            try:
                                volume_percent = int(volume_str)
                                return volume_percent / 100.0
                            except ValueError:
                                continue
            
            logger.error(f"Failed to get volume for {device.name}")
            return None
            
        except FileNotFoundError:
            logger.warning("pactl not available, cannot get volume")
            return None
        except Exception as e:
            logger.error(f"Error getting PipeWire device volume: {e}")
            return None
    
    async def create_stream(self, config: AudioStreamConfig) -> Optional[str]:
        """Create PipeWire audio stream"""
        try:
            stream_id = f"pipewire_stream_{len(self.streams)}"
            
            # In a real implementation, would create actual PipeWire stream
            # For now, just track the configuration
            self.streams[stream_id] = {
                'config': config,
                'created_at': time.time(),
                'active': True
            }
            
            logger.info(f"Created PipeWire stream {stream_id} for device {config.device_id}")
            return stream_id
            
        except Exception as e:
            logger.error(f"Error creating PipeWire stream: {e}")
            return None
    
    async def destroy_stream(self, stream_id: str) -> bool:
        """Destroy PipeWire audio stream"""
        try:
            if stream_id in self.streams:
                del self.streams[stream_id]
                logger.info(f"Destroyed PipeWire stream {stream_id}")
                return True
            else:
                logger.error(f"Stream {stream_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error destroying PipeWire stream: {e}")
            return False


class WASAPIEngine(AudioEngineInterface):
    """WASAPI audio engine for Windows"""
    
    def __init__(self):
        self.initialized = False
        self.devices: Dict[str, AudioDeviceInfo] = {}
        self.streams: Dict[str, Any] = {}
        logger.info("WASAPI audio engine created")
    
    async def initialize(self) -> bool:
        """Initialize WASAPI engine"""
        logger.info("--- Initializing WASAPI Audio Engine ---")
        
        try:
            # Check if we're on Windows
            if platform.system() != "Windows":
                logger.error("WASAPI engine can only run on Windows")
                return False
            
            # Try to enumerate devices to test WASAPI availability
            devices = await self.enumerate_devices()
            
            if devices:
                self.initialized = True
                logger.info(f"WASAPI engine initialized with {len(devices)} devices")
                return True
            else:
                logger.error("No WASAPI devices found")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing WASAPI: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown WASAPI engine"""
        logger.info("Shutting down WASAPI audio engine")
        
        # Destroy all streams
        for stream_id in list(self.streams.keys()):
            await self.destroy_stream(stream_id)
        
        self.initialized = False
        self.devices.clear()
        logger.info("WASAPI engine shutdown complete")
    
    async def enumerate_devices(self, device_type: Optional[DeviceType] = None) -> List[AudioDeviceInfo]:
        """Enumerate WASAPI devices using PowerShell"""
        logger.debug("Enumerating WASAPI devices")
        
        try:
            # Use PowerShell to get audio devices
            ps_script = """
            Get-WmiObject -Class Win32_SoundDevice | ForEach-Object {
                [PSCustomObject]@{
                    Name = $_.Name
                    DeviceID = $_.DeviceID
                    Status = $_.Status
                    Manufacturer = $_.Manufacturer
                }
            } | ConvertTo-Json
            """
            
            result = await asyncio.create_subprocess_exec(
                'powershell', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to enumerate WASAPI devices: {stderr.decode()}")
                return []
            
            # Parse PowerShell JSON output
            devices = await self._parse_wasapi_devices(stdout.decode())
            
            # Filter by device type if specified
            if device_type:
                devices = [d for d in devices if d.device_type == device_type]
            
            # Update internal device cache
            self.devices.clear()
            for device in devices:
                self.devices[device.id] = device
            
            logger.info(f"Found {len(devices)} WASAPI devices")
            return devices
            
        except FileNotFoundError:
            logger.error("PowerShell not available")
            return []
        except Exception as e:
            logger.error(f"Error enumerating WASAPI devices: {e}")
            return []
    
    async def _parse_wasapi_devices(self, json_output: str) -> List[AudioDeviceInfo]:
        """Parse WASAPI device JSON output"""
        devices = []
        
        try:
            if json_output.strip():
                device_data = json.loads(json_output)
                
                # Handle single device vs array
                if not isinstance(device_data, list):
                    device_data = [device_data]
                
                for i, device_info in enumerate(device_data):
                    device_id = f"wasapi_{i}"
                    device = AudioDeviceInfo(
                        id=device_id,
                        name=device_info.get('Name', f'WASAPI Device {i}'),
                        description=f"WASAPI device - {device_info.get('Manufacturer', 'Unknown')}",
                        device_type=DeviceType.PLAYBACK,  # Assume playback for now
                        state=DeviceState.ACTIVE if device_info.get('Status') == 'OK' else DeviceState.UNKNOWN,
                        driver="wasapi"
                    )
                    devices.append(device)
            
            logger.debug(f"Parsed {len(devices)} WASAPI devices")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing WASAPI JSON: {e}")
        except Exception as e:
            logger.error(f"Error parsing WASAPI devices: {e}")
        
        return devices
    
    async def get_default_device(self, device_type: DeviceType) -> Optional[AudioDeviceInfo]:
        """Get default WASAPI device"""
        # Return first device of specified type
        for device in self.devices.values():
            if device.device_type == device_type:
                logger.debug(f"Default {device_type.value} device: {device.name}")
                return device
        return None
    
    async def set_default_device(self, device_id: str) -> bool:
        """Set default WASAPI device"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return False
            
            # In a real implementation, would use Windows APIs
            logger.info(f"Mock: Set default WASAPI device to {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting default WASAPI device: {e}")
            return False
    
    async def set_device_volume(self, device_id: str, volume: float) -> bool:
        """Set WASAPI device volume"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return False
            
            # In a real implementation, would use Windows Volume APIs
            volume_percent = max(0, min(100, int(volume * 100)))
            logger.debug(f"Mock: Set WASAPI device {device_id} volume to {volume_percent}%")
            return True
            
        except Exception as e:
            logger.error(f"Error setting WASAPI device volume: {e}")
            return False
    
    async def get_device_volume(self, device_id: str) -> Optional[float]:
        """Get WASAPI device volume"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return None
            
            # In a real implementation, would query Windows Volume APIs
            # Return mock volume
            return 0.75  # 75%
            
        except Exception as e:
            logger.error(f"Error getting WASAPI device volume: {e}")
            return None
    
    async def create_stream(self, config: AudioStreamConfig) -> Optional[str]:
        """Create WASAPI audio stream"""
        try:
            stream_id = f"wasapi_stream_{len(self.streams)}"
            
            # In a real implementation, would create actual WASAPI stream
            self.streams[stream_id] = {
                'config': config,
                'created_at': time.time(),
                'active': True
            }
            
            logger.info(f"Created WASAPI stream {stream_id} for device {config.device_id}")
            return stream_id
            
        except Exception as e:
            logger.error(f"Error creating WASAPI stream: {e}")
            return None
    
    async def destroy_stream(self, stream_id: str) -> bool:
        """Destroy WASAPI audio stream"""
        try:
            if stream_id in self.streams:
                del self.streams[stream_id]
                logger.info(f"Destroyed WASAPI stream {stream_id}")
                return True
            else:
                logger.error(f"Stream {stream_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error destroying WASAPI stream: {e}")
            return False


class CoreAudioEngine(AudioEngineInterface):
    """Core Audio engine for macOS"""
    
    def __init__(self):
        self.initialized = False
        self.devices: Dict[str, AudioDeviceInfo] = {}
        self.streams: Dict[str, Any] = {}
        logger.info("Core Audio engine created")
    
    async def initialize(self) -> bool:
        """Initialize Core Audio engine"""
        logger.info("--- Initializing Core Audio Engine ---")
        
        try:
            # Check if we're on macOS
            if platform.system() != "Darwin":
                logger.error("Core Audio engine can only run on macOS")
                return False
            
            # Try to enumerate devices to test Core Audio availability
            devices = await self.enumerate_devices()
            
            if devices:
                self.initialized = True
                logger.info(f"Core Audio engine initialized with {len(devices)} devices")
                return True
            else:
                logger.error("No Core Audio devices found")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Core Audio: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown Core Audio engine"""
        logger.info("Shutting down Core Audio engine")
        
        # Destroy all streams
        for stream_id in list(self.streams.keys()):
            await self.destroy_stream(stream_id)
        
        self.initialized = False
        self.devices.clear()
        logger.info("Core Audio engine shutdown complete")
    
    async def enumerate_devices(self, device_type: Optional[DeviceType] = None) -> List[AudioDeviceInfo]:
        """Enumerate Core Audio devices"""
        logger.debug("Enumerating Core Audio devices")
        
        try:
            # Use system_profiler to get audio device info
            result = await asyncio.create_subprocess_exec(
                'system_profiler', 'SPAudioDataType', '-json',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to enumerate Core Audio devices: {stderr.decode()}")
                return []
            
            # Parse system_profiler JSON output
            devices = await self._parse_coreaudio_devices(stdout.decode())
            
            # Filter by device type if specified
            if device_type:
                devices = [d for d in devices if d.device_type == device_type]
            
            # Update internal device cache
            self.devices.clear()
            for device in devices:
                self.devices[device.id] = device
            
            logger.info(f"Found {len(devices)} Core Audio devices")
            return devices
            
        except FileNotFoundError:
            logger.error("system_profiler not available")
            return []
        except Exception as e:
            logger.error(f"Error enumerating Core Audio devices: {e}")
            return []
    
    async def _parse_coreaudio_devices(self, json_output: str) -> List[AudioDeviceInfo]:
        """Parse Core Audio device JSON output"""
        devices = []
        
        try:
            if json_output.strip():
                data = json.loads(json_output)
                
                # Extract audio devices from system profiler data
                audio_data = data.get('SPAudioDataType', [])
                
                for i, device_info in enumerate(audio_data):
                    device_id = f"coreaudio_{i}"
                    device_name = device_info.get('_name', f'Core Audio Device {i}')
                    
                    device = AudioDeviceInfo(
                        id=device_id,
                        name=device_name,
                        description=f"Core Audio device: {device_name}",
                        device_type=DeviceType.PLAYBACK,  # Assume playback for now
                        state=DeviceState.ACTIVE,
                        driver="coreaudio"
                    )
                    devices.append(device)
            
            logger.debug(f"Parsed {len(devices)} Core Audio devices")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Core Audio JSON: {e}")
        except Exception as e:
            logger.error(f"Error parsing Core Audio devices: {e}")
        
        return devices
    
    async def get_default_device(self, device_type: DeviceType) -> Optional[AudioDeviceInfo]:
        """Get default Core Audio device"""
        # Return first device of specified type
        for device in self.devices.values():
            if device.device_type == device_type:
                logger.debug(f"Default {device_type.value} device: {device.name}")
                return device
        return None
    
    async def set_default_device(self, device_id: str) -> bool:
        """Set default Core Audio device"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return False
            
            # In a real implementation, would use Core Audio APIs
            logger.info(f"Mock: Set default Core Audio device to {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting default Core Audio device: {e}")
            return False
    
    async def set_device_volume(self, device_id: str, volume: float) -> bool:
        """Set Core Audio device volume"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return False
            
            # Use osascript for volume control
            volume_percent = max(0, min(100, int(volume * 100)))
            
            result = await asyncio.create_subprocess_exec(
                'osascript', '-e', f'set volume output volume {volume_percent}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            success = result.returncode == 0
            if success:
                logger.debug(f"Set Core Audio device {device_id} volume to {volume_percent}%")
            else:
                logger.error(f"Failed to set Core Audio volume")
            
            return success
            
        except FileNotFoundError:
            logger.warning("osascript not available, cannot set volume")
            return False
        except Exception as e:
            logger.error(f"Error setting Core Audio device volume: {e}")
            return False
    
    async def get_device_volume(self, device_id: str) -> Optional[float]:
        """Get Core Audio device volume"""
        try:
            if device_id not in self.devices:
                logger.error(f"Device {device_id} not found")
                return None
            
            # Use osascript to get volume
            result = await asyncio.create_subprocess_exec(
                'osascript', '-e', 'output volume of (get volume settings)',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                try:
                    volume_percent = int(stdout.decode().strip())
                    return volume_percent / 100.0
                except ValueError:
                    logger.error("Failed to parse volume from osascript output")
                    return None
            else:
                logger.error("Failed to get Core Audio volume")
                return None
            
        except FileNotFoundError:
            logger.warning("osascript not available, cannot get volume")
            return None
        except Exception as e:
            logger.error(f"Error getting Core Audio device volume: {e}")
            return None
    
    async def create_stream(self, config: AudioStreamConfig) -> Optional[str]:
        """Create Core Audio stream"""
        try:
            stream_id = f"coreaudio_stream_{len(self.streams)}"
            
            # In a real implementation, would create actual Core Audio stream
            self.streams[stream_id] = {
                'config': config,
                'created_at': time.time(),
                'active': True
            }
            
            logger.info(f"Created Core Audio stream {stream_id} for device {config.device_id}")
            return stream_id
            
        except Exception as e:
            logger.error(f"Error creating Core Audio stream: {e}")
            return None
    
    async def destroy_stream(self, stream_id: str) -> bool:
        """Destroy Core Audio stream"""
        try:
            if stream_id in self.streams:
                del self.streams[stream_id]
                logger.info(f"Destroyed Core Audio stream {stream_id}")
                return True
            else:
                logger.error(f"Stream {stream_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error destroying Core Audio stream: {e}")
            return False


class CrossPlatformAudioEngine:
    """Unified cross-platform audio engine that automatically selects the appropriate backend"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.engine: Optional[AudioEngineInterface] = None
        self.initialized = False
        
        logger.info(f"CrossPlatformAudioEngine created for platform: {self.platform}")
    
    async def initialize(self) -> bool:
        """Initialize the appropriate audio engine for the current platform"""
        logger.info("=== Initializing Cross-Platform Audio Engine ===")
        
        try:
            # Select appropriate engine based on platform
            if self.platform == "linux":
                self.engine = PipeWireEngine()
            elif self.platform == "windows":
                self.engine = WASAPIEngine()
            elif self.platform == "darwin":  # macOS
                self.engine = CoreAudioEngine()
            else:
                logger.error(f"Unsupported platform: {self.platform}")
                return False
            
            # Initialize the selected engine
            success = await self.engine.initialize()
            
            if success:
                self.initialized = True
                logger.info(f"=== Cross-Platform Audio Engine Initialized Successfully ===")
                logger.info(f"Active engine: {type(self.engine).__name__}")
                return True
            else:
                logger.error("=== Cross-Platform Audio Engine Initialization Failed ===")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing cross-platform audio engine: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the audio engine"""
        if self.engine and self.initialized:
            await self.engine.shutdown()
        self.initialized = False
        logger.info("Cross-Platform Audio Engine shutdown complete")
    
    def _ensure_initialized(self) -> bool:
        """Ensure engine is initialized before operations"""
        if not self.initialized or not self.engine:
            logger.error("Audio engine not initialized")
            return False
        return True
    
    async def enumerate_devices(self, device_type: Optional[DeviceType] = None) -> List[AudioDeviceInfo]:
        """Enumerate available audio devices"""
        if not self._ensure_initialized():
            return []
        return await self.engine.enumerate_devices(device_type)
    
    async def get_default_device(self, device_type: DeviceType) -> Optional[AudioDeviceInfo]:
        """Get default device for specified type"""
        if not self._ensure_initialized():
            return None
        return await self.engine.get_default_device(device_type)
    
    async def set_default_device(self, device_id: str) -> bool:
        """Set default audio device"""
        if not self._ensure_initialized():
            return False
        return await self.engine.set_default_device(device_id)
    
    async def set_device_volume(self, device_id: str, volume: float) -> bool:
        """Set device volume (0.0 to 1.0)"""
        if not self._ensure_initialized():
            return False
        return await self.engine.set_device_volume(device_id, volume)
    
    async def get_device_volume(self, device_id: str) -> Optional[float]:
        """Get device volume (0.0 to 1.0)"""
        if not self._ensure_initialized():
            return None
        return await self.engine.get_device_volume(device_id)
    
    async def create_stream(self, config: AudioStreamConfig) -> Optional[str]:
        """Create audio stream, returns stream ID"""
        if not self._ensure_initialized():
            return None
        return await self.engine.create_stream(config)
    
    async def destroy_stream(self, stream_id: str) -> bool:
        """Destroy audio stream"""
        if not self._ensure_initialized():
            return False
        return await self.engine.destroy_stream(stream_id)
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about the current audio engine"""
        if not self.initialized or not self.engine:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "platform": self.platform,
            "engine_type": type(self.engine).__name__,
            "device_count": len(getattr(self.engine, 'devices', {})),
            "stream_count": len(getattr(self.engine, 'streams', {}))
        }


# Example usage and testing
if __name__ == "__main__":
    async def test_cross_platform_audio():
        """Test the cross-platform audio engine"""
        logger.info("=== Starting Cross-Platform Audio Engine Test ===")
        
        # Create and initialize engine
        engine = CrossPlatformAudioEngine()
        success = await engine.initialize()
        
        if not success:
            logger.error("Failed to initialize audio engine")
            return
        
        # Get engine info
        info = engine.get_engine_info()
        logger.info(f"Engine info: {info}")
        
        # Enumerate devices
        devices = await engine.enumerate_devices()
        logger.info(f"Found {len(devices)} audio devices:")
        for device in devices:
            logger.info(f"  {device.name} ({device.id}) - {device.device_type.value} - {device.state.value}")
        
        # Test volume control on first device
        if devices:
            test_device = devices[0]
            logger.info(f"Testing volume control on {test_device.name}")
            
            # Get current volume
            current_volume = await engine.get_device_volume(test_device.id)
            if current_volume is not None:
                logger.info(f"Current volume: {current_volume * 100:.1f}%")
                
                # Set volume to 75%
                success = await engine.set_device_volume(test_device.id, 0.75)
                if success:
                    logger.info("Volume set to 75%")
                    
                    # Get new volume
                    new_volume = await engine.get_device_volume(test_device.id)
                    if new_volume is not None:
                        logger.info(f"New volume: {new_volume * 100:.1f}%")
        
        # Test stream creation
        if devices:
            config = AudioStreamConfig(
                device_id=devices[0].id,
                sample_rate=48000,
                format=AudioFormat.FLOAT_32,
                channels=2
            )
            
            stream_id = await engine.create_stream(config)
            if stream_id:
                logger.info(f"Created audio stream: {stream_id}")
                
                # Destroy stream
                success = await engine.destroy_stream(stream_id)
                if success:
                    logger.info(f"Destroyed audio stream: {stream_id}")
        
        # Shutdown
        await engine.shutdown()
        logger.info("=== Cross-Platform Audio Engine Test Complete ===")
    
    # Run test
    asyncio.run(test_cross_platform_audio())