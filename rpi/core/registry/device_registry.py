"""
Device Registry
Central registry for tracking and managing hardware devices.
"""
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable

from .device_profile import DeviceProfile, DeviceType, DeviceStatus

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """
    Thread-safe device registry for hardware abstraction.
    
    Features:
    - Device registration and deregistration
    - Health monitoring with configurable timeouts
    - Event callbacks for device state changes
    - Optional persistence to JSON file
    - Device lookup by ID, type, or capability
    
    Usage:
        registry = DeviceRegistry()
        registry.start()
        
        # Register a device
        profile = DeviceProfile(
            device_id="gpio_worker_1",
            device_type=DeviceType.GPIO,
            capabilities=["GPIO_SET", "GPIO_GET"]
        )
        registry.register(profile)
        
        # Find devices
        gpio_devices = registry.get_by_type(DeviceType.GPIO)
        
        # Cleanup
        registry.stop()
    """
    
    def __init__(
        self,
        health_check_interval: float = 5.0,
        device_timeout: float = 30.0,
        persistence_path: Optional[str] = None
    ):
        """
        Initialize the device registry.
        
        Args:
            health_check_interval: Seconds between health checks
            device_timeout: Seconds before device is considered offline
            persistence_path: Optional path to JSON file for persistence
        """
        self._devices: Dict[str, DeviceProfile] = {}
        self._lock = threading.RLock()
        self._health_check_interval = health_check_interval
        self._device_timeout = device_timeout
        self._persistence_path = Path(persistence_path) if persistence_path else None
        
        # Health monitoring thread
        self._running = False
        self._health_thread: Optional[threading.Thread] = None
        
        # Event callbacks
        self._on_device_online: List[Callable[[DeviceProfile], None]] = []
        self._on_device_offline: List[Callable[[DeviceProfile], None]] = []
        self._on_device_error: List[Callable[[DeviceProfile, str], None]] = []
        
        # Load persisted state if available
        if self._persistence_path and self._persistence_path.exists():
            self._load_state()
    
    def start(self):
        """Start the registry and health monitoring"""
        self._running = True
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()
        logger.info("Device registry started")
    
    def stop(self):
        """Stop the registry and save state"""
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=2.0)
        if self._persistence_path:
            self._save_state()
        logger.info("Device registry stopped")
    
    def register(self, profile: DeviceProfile) -> bool:
        """
        Register a device with the registry.
        
        Args:
            profile: Device profile to register
            
        Returns:
            True if registration successful, False if device already exists
        """
        with self._lock:
            if profile.device_id in self._devices:
                # Update existing device
                existing = self._devices[profile.device_id]
                existing.capabilities = profile.capabilities
                existing.metadata.update(profile.metadata)
                existing.set_online()
                logger.info(f"Updated device: {profile.device_id}")
                return True
            
            profile.set_online()
            self._devices[profile.device_id] = profile
            logger.info(f"Registered device: {profile.device_id} ({profile.device_type.value})")
            
            # Fire callbacks
            for callback in self._on_device_online:
                try:
                    callback(profile)
                except Exception as e:
                    logger.error(f"Error in on_device_online callback: {e}")
            
            return True
    
    def unregister(self, device_id: str) -> bool:
        """
        Unregister a device from the registry.
        
        Args:
            device_id: ID of device to unregister
            
        Returns:
            True if device was found and removed
        """
        with self._lock:
            if device_id in self._devices:
                profile = self._devices.pop(device_id)
                logger.info(f"Unregistered device: {device_id}")
                
                # Fire callbacks
                for callback in self._on_device_offline:
                    try:
                        callback(profile)
                    except Exception as e:
                        logger.error(f"Error in on_device_offline callback: {e}")
                
                return True
            return False
    
    def heartbeat(self, device_id: str) -> bool:
        """
        Update device last_seen timestamp (heartbeat).
        
        Args:
            device_id: ID of device sending heartbeat
            
        Returns:
            True if device exists and was updated
        """
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].update_last_seen()
                if self._devices[device_id].status != DeviceStatus.ONLINE:
                    self._devices[device_id].set_online()
                return True
            return False
    
    def get(self, device_id: str) -> Optional[DeviceProfile]:
        """Get device profile by ID"""
        with self._lock:
            return self._devices.get(device_id)
    
    def get_all(self) -> List[DeviceProfile]:
        """Get all registered devices"""
        with self._lock:
            return list(self._devices.values())
    
    def get_by_type(self, device_type: DeviceType) -> List[DeviceProfile]:
        """Get all devices of a specific type"""
        with self._lock:
            return [d for d in self._devices.values() if d.device_type == device_type]
    
    def get_by_capability(self, capability: str) -> List[DeviceProfile]:
        """Get all devices that have a specific capability"""
        with self._lock:
            return [d for d in self._devices.values() if capability in d.capabilities]
    
    def get_healthy(self) -> List[DeviceProfile]:
        """Get all healthy (online and recently seen) devices"""
        with self._lock:
            return [d for d in self._devices.values() if d.is_healthy(self._device_timeout)]
    
    def get_status_summary(self) -> Dict:
        """Get summary of registry status"""
        with self._lock:
            devices = list(self._devices.values())
            return {
                "total_devices": len(devices),
                "online": sum(1 for d in devices if d.status == DeviceStatus.ONLINE),
                "offline": sum(1 for d in devices if d.status == DeviceStatus.OFFLINE),
                "error": sum(1 for d in devices if d.status == DeviceStatus.ERROR),
                "healthy": sum(1 for d in devices if d.is_healthy(self._device_timeout)),
                "by_type": {
                    dtype.value: sum(1 for d in devices if d.device_type == dtype)
                    for dtype in DeviceType
                    if any(d.device_type == dtype for d in devices)
                },
                "timestamp": datetime.now().isoformat()
            }
    
    def set_device_error(self, device_id: str, error_message: str):
        """Mark a device as having an error"""
        with self._lock:
            if device_id in self._devices:
                profile = self._devices[device_id]
                profile.set_error(error_message)
                
                # Fire callbacks
                for callback in self._on_device_error:
                    try:
                        callback(profile, error_message)
                    except Exception as e:
                        logger.error(f"Error in on_device_error callback: {e}")
    
    # Event subscription methods
    def on_device_online(self, callback: Callable[[DeviceProfile], None]):
        """Subscribe to device online events"""
        self._on_device_online.append(callback)
    
    def on_device_offline(self, callback: Callable[[DeviceProfile], None]):
        """Subscribe to device offline events"""
        self._on_device_offline.append(callback)
    
    def on_device_error(self, callback: Callable[[DeviceProfile, str], None]):
        """Subscribe to device error events"""
        self._on_device_error.append(callback)
    
    # Health monitoring
    def _health_check_loop(self):
        """Background thread for health monitoring"""
        while self._running:
            try:
                self._check_device_health()
                time.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1.0)
    
    def _check_device_health(self):
        """Check health of all devices"""
        with self._lock:
            for device_id, profile in self._devices.items():
                if profile.status == DeviceStatus.ONLINE:
                    if not profile.is_healthy(self._device_timeout):
                        profile.set_offline()
                        logger.warning(f"Device {device_id} went offline (timeout)")
                        
                        # Fire callbacks
                        for callback in self._on_device_offline:
                            try:
                                callback(profile)
                            except Exception as e:
                                logger.error(f"Error in on_device_offline callback: {e}")
    
    # Persistence
    def _save_state(self):
        """Save registry state to JSON file"""
        if not self._persistence_path:
            return
        
        try:
            with self._lock:
                data = {
                    "devices": [d.to_dict() for d in self._devices.values()],
                    "saved_at": datetime.now().isoformat()
                }
            
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved registry state to {self._persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save registry state: {e}")
    
    def _load_state(self):
        """Load registry state from JSON file"""
        if not self._persistence_path or not self._persistence_path.exists():
            return
        
        try:
            with open(self._persistence_path, 'r') as f:
                data = json.load(f)
            
            with self._lock:
                for device_data in data.get("devices", []):
                    try:
                        profile = DeviceProfile.from_dict(device_data)
                        # Mark as offline since we're loading from persistence
                        profile.set_offline()
                        self._devices[profile.device_id] = profile
                    except Exception as e:
                        logger.error(f"Failed to load device profile: {e}")
            
            logger.info(f"Loaded {len(self._devices)} devices from {self._persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load registry state: {e}")


# Singleton instance for global access
_registry_instance: Optional[DeviceRegistry] = None


def get_registry() -> DeviceRegistry:
    """Get the global device registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = DeviceRegistry()
    return _registry_instance


def init_registry(**kwargs) -> DeviceRegistry:
    """Initialize the global device registry with custom settings"""
    global _registry_instance
    _registry_instance = DeviceRegistry(**kwargs)
    return _registry_instance
