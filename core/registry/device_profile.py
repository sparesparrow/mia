"""
Device Profile Definitions
Defines device types, capabilities, and status tracking.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class DeviceType(str, Enum):
    """Supported device types"""
    GPIO = "gpio"
    SERIAL = "serial"
    OBD = "obd"
    LED_STRIP = "led_strip"
    SENSOR = "sensor"
    SENSOR_DHT = "sensor_dht"
    SENSOR_HCSR04 = "sensor_hcsr04"
    SENSOR_BMP180 = "sensor_bmp180"
    SENSOR_ANALOG = "sensor_analog"
    MOTOR = "motor"
    RELAY = "relay"
    CAMERA = "camera"
    AUDIO = "audio"
    ARDUINO = "arduino"
    ESP32 = "esp32"
    UNKNOWN = "unknown"


class DeviceStatus(str, Enum):
    """Device connection status"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    INITIALIZING = "initializing"
    UNKNOWN = "unknown"


@dataclass
class DeviceProfile:
    """
    Device profile containing metadata and state.
    
    Attributes:
        device_id: Unique identifier for the device
        device_type: Type of device (GPIO, Serial, OBD, etc.)
        name: Human-readable name
        capabilities: List of supported commands/operations
        status: Current connection status
        last_seen: Timestamp of last communication
        metadata: Additional device-specific information
        error_message: Last error message if status is ERROR
    """
    device_id: str
    device_type: DeviceType
    name: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: DeviceStatus = DeviceStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.name:
            self.name = f"{self.device_type.value}_{self.device_id[:8]}"
        if self.last_seen is None:
            self.last_seen = datetime.now()
    
    def update_last_seen(self):
        """Update the last seen timestamp"""
        self.last_seen = datetime.now()
    
    def set_online(self):
        """Mark device as online"""
        self.status = DeviceStatus.ONLINE
        self.error_message = None
        self.update_last_seen()
    
    def set_offline(self):
        """Mark device as offline"""
        self.status = DeviceStatus.OFFLINE
    
    def set_error(self, message: str):
        """Mark device as error with message"""
        self.status = DeviceStatus.ERROR
        self.error_message = message
    
    def is_healthy(self, timeout_seconds: float = 30.0) -> bool:
        """
        Check if device is healthy (online and recently seen).
        
        Args:
            timeout_seconds: Maximum seconds since last_seen to be considered healthy
            
        Returns:
            True if device is online and was seen within timeout
        """
        if self.status != DeviceStatus.ONLINE:
            return False
        if self.last_seen is None:
            return False
        elapsed = (datetime.now() - self.last_seen).total_seconds()
        return elapsed < timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for JSON serialization"""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "name": self.name,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "is_healthy": self.is_healthy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceProfile':
        """Create profile from dictionary"""
        return cls(
            device_id=data["device_id"],
            device_type=DeviceType(data.get("device_type", "unknown")),
            name=data.get("name", ""),
            capabilities=data.get("capabilities", []),
            status=DeviceStatus(data.get("status", "unknown")),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            metadata=data.get("metadata", {}),
            error_message=data.get("error_message")
        )


# Predefined device profiles for common hardware
DEVICE_PROFILES = {
    "led_strip_ws2812": DeviceProfile(
        device_id="led_strip_default",
        device_type=DeviceType.LED_STRIP,
        name="WS2812 LED Strip",
        capabilities=["set_color", "set_brightness", "set_animation", "set_mode"],
        metadata={"protocol": "ws2812", "num_leds": 60}
    ),
    "gpio_relay_4ch": DeviceProfile(
        device_id="relay_4ch_default",
        device_type=DeviceType.RELAY,
        name="4-Channel Relay Module",
        capabilities=["set_relay", "get_relay_status", "toggle_relay"],
        metadata={"channels": 4, "active_low": True}
    ),
    "obd_elm327": DeviceProfile(
        device_id="obd_elm327_default",
        device_type=DeviceType.OBD,
        name="ELM327 OBD-II Adapter",
        capabilities=["query_pid", "get_dtc", "clear_dtc", "get_vin"],
        metadata={"protocol": "elm327", "baud_rate": 38400}
    ),
    "serial_arduino": DeviceProfile(
        device_id="arduino_default",
        device_type=DeviceType.SERIAL,
        name="Arduino Controller",
        capabilities=["send_command", "get_telemetry", "firmware_info"],
        metadata={"baud_rate": 115200}
    )
}
