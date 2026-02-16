#!/usr/bin/env python3
"""
Test script for AI Audio Assistant MCP Server
This version uses only standard library modules for testing
"""

import asyncio
import logging
import os
import json
import subprocess
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

# Setup logging
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


class TestAudioManager:
    """Test version of AudioManager with comprehensive error handling and debugging"""
    
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
            result = subprocess.run(['system_profiler', 'SPAudioDataType', '-json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("macOS audio devices detected via system_profiler")
                self.devices["speakers"] = AudioDevice("speakers", "macOS Built-in Speakers", "speakers", True)
                self.devices["headphones"] = AudioDevice("headphones", "macOS Headphones", "headphones", False)
                logger.info("Added macOS Core Audio devices")
            else:
                logger.warning(f"system_profiler failed with exit code: {result.returncode}")
                self._add_fallback_device()
        except FileNotFoundError:
            logger.debug("system_profiler command not found")
            self._add_fallback_device()
        except Exception as e:
            logger.warning(f"macOS device discovery error: {e}")
            self._add_fallback_device()
    
    def _discover_windows_devices(self):
        """Discover Windows audio devices with enhanced error handling"""
        logger.info("Attempting Windows audio device discovery")
        try:
            ps_command = "Get-WmiObject -Class Win32_SoundDevice | Select-Object Name, Status"
            result = subprocess.run(['powershell', '-Command', ps_command], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("Windows audio devices detected via PowerShell")
                self.devices["speakers"] = AudioDevice("speakers", "Windows Default Speakers", "speakers", True)
                self.devices["headphones"] = AudioDevice("headphones", "Windows Headphones", "headphones", False)
                logger.info("Added Windows audio devices")
            else:
                logger.warning(f"PowerShell command failed with exit code: {result.returncode}")
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
            if device_type not in self.devices:
                logger.error(f"Device '{device_type}' not found in available devices: {list(self.devices.keys())}")
                return False
            
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
            
            # Mock platform-specific audio switching
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
        """Mock platform-specific audio switching"""
        logger.debug(f"Performing {self.platform} audio switch to {device_type}")
        await asyncio.sleep(0.1)  # Simulate platform-specific operation
        logger.debug(f"{self.platform} audio switch to {device_type} completed (mock)")
    
    async def set_volume(self, level: int, zone: Optional[str] = None) -> bool:
        """Set volume level with comprehensive error handling and debugging"""
        logger.info(f"--- Volume Control Request ---")
        logger.info(f"Requested level: {level}")
        logger.info(f"Target zone: {zone}")
        
        try:
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
            else:
                old_volume = self.volume
                self.volume = level
                logger.info(f"Global volume changed from {old_volume}% to {level}%")
            
            # Mock platform-specific volume setting
            await self._perform_platform_volume_set(level, zone)
            
            logger.info(f"--- Volume Control Completed Successfully ---")
            return True
            
        except Exception as e:
            logger.error(f"--- Volume Control Failed ---")
            logger.error(f"Error setting volume to {level}%: {e}")
            return False
    
    async def _perform_platform_volume_set(self, level: int, zone: Optional[str] = None):
        """Mock platform-specific volume setting"""
        logger.debug(f"Performing {self.platform} volume set to {level}% for zone {zone}")
        await asyncio.sleep(0.05)  # Simulate platform-specific operation
        logger.debug(f"{self.platform} volume set to {level}% completed (mock)")
    
    def get_active_device(self) -> Optional[AudioDevice]:
        """Get currently active audio device"""
        for device in self.devices.values():
            if device.is_active:
                return device
        return None
    
    def get_zone_info(self, zone_name: str) -> Optional[AudioZone]:
        """Get information about a specific zone"""
        return self.zones.get(zone_name)


async def test_audio_manager():
    """Test the AudioManager functionality"""
    logger.info("=== Starting AudioManager Tests ===")
    
    # Initialize AudioManager
    audio_manager = TestAudioManager()
    
    # Test device switching
    logger.info("\n--- Testing Device Switching ---")
    result = await audio_manager.switch_output("speakers", "living_room")
    logger.info(f"Switch to speakers result: {result}")
    
    result = await audio_manager.switch_output("headphones", "bedroom")
    logger.info(f"Switch to headphones result: {result}")
    
    # Test invalid device
    result = await audio_manager.switch_output("invalid_device")
    logger.info(f"Switch to invalid device result: {result}")
    
    # Test volume control
    logger.info("\n--- Testing Volume Control ---")
    result = await audio_manager.set_volume(75, "living_room")
    logger.info(f"Set volume to 75% in living_room result: {result}")
    
    result = await audio_manager.set_volume(50)
    logger.info(f"Set global volume to 50% result: {result}")
    
    # Test invalid volume
    result = await audio_manager.set_volume(150)
    logger.info(f"Set volume to 150% (should clamp) result: {result}")
    
    # Test zone info
    logger.info("\n--- Testing Zone Information ---")
    zone_info = audio_manager.get_zone_info("living_room")
    if zone_info:
        logger.info(f"Living room zone: devices={zone_info.devices}, volume={zone_info.volume}, active={zone_info.is_active}")
    
    active_device = audio_manager.get_active_device()
    if active_device:
        logger.info(f"Active device: {active_device.name} ({active_device.id})")
    
    logger.info("=== AudioManager Tests Completed ===")


if __name__ == "__main__":
    asyncio.run(test_audio_manager())