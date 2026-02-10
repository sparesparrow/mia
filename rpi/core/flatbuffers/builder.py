"""
FlatBuffers Message Builder
Creates FlatBuffers messages for ZeroMQ communication.
"""

import flatbuffers
from typing import List, Optional, Dict, Any
from datetime import datetime

# Import generated classes (these would be generated from the .fbs schema)
# For now, we'll create mock implementations until the Python bindings are generated


class MessageBuilder:
    """
    Builder for creating FlatBuffers messages.

    This class provides high-level methods for creating different types of messages
    that can be sent over ZeroMQ.
    """

    def __init__(self):
        self.builder = flatbuffers.Builder(1024)

    def build_download_request(self, url: str) -> bytes:
        """Build a download request message."""
        # This would use the actual generated FlatBuffers classes
        # For now, return a placeholder
        return self._build_json_fallback({
            "type": "DOWNLOAD_REQUEST",
            "url": url
        })

    def build_download_status_request(self, session_id: int) -> bytes:
        """Build a download status request message."""
        return self._build_json_fallback({
            "type": "DOWNLOAD_STATUS_REQUEST",
            "session_id": session_id
        })

    def build_download_abort_request(self, session_id: int) -> bytes:
        """Build a download abort request message."""
        return self._build_json_fallback({
            "type": "DOWNLOAD_ABORT_REQUEST",
            "session_id": session_id
        })

    def build_shutdown_request(self) -> bytes:
        """Build a shutdown request message."""
        return self._build_json_fallback({
            "type": "SHUTDOWN_REQUEST"
        })

    def build_gpio_configure_request(self, pin: int, direction: str) -> bytes:
        """Build a GPIO configure request message."""
        return self._build_json_fallback({
            "type": "GPIO_CONFIGURE_REQUEST",
            "pin": pin,
            "direction": direction
        })

    def build_gpio_set_request(self, pin: int, value: bool) -> bytes:
        """Build a GPIO set request message."""
        return self._build_json_fallback({
            "type": "GPIO_SET_REQUEST",
            "pin": pin,
            "value": value
        })

    def build_gpio_get_request(self, pin: int) -> bytes:
        """Build a GPIO get request message."""
        return self._build_json_fallback({
            "type": "GPIO_GET_REQUEST",
            "pin": pin
        })

    def build_gpio_status_request(self) -> bytes:
        """Build a GPIO status request message."""
        return self._build_json_fallback({
            "type": "GPIO_STATUS_REQUEST"
        })

    def build_system_status_request(self) -> bytes:
        """Build a system status request message."""
        return self._build_json_fallback({
            "type": "SYSTEM_STATUS_REQUEST"
        })

    def build_device_discovery_request(self, device_type: Optional[str] = None) -> bytes:
        """Build a device discovery request message."""
        message = {"type": "DEVICE_DISCOVERY_REQUEST"}
        if device_type:
            message["device_type"] = device_type
        return self._build_json_fallback(message)

    def build_telemetry_request(self, device_id: Optional[str] = None,
                               sensor_type: Optional[str] = None) -> bytes:
        """Build a telemetry request message."""
        message = {"type": "TELEMETRY_REQUEST"}
        if device_id:
            message["device_id"] = device_id
        if sensor_type:
            message["sensor_type"] = sensor_type
        return self._build_json_fallback(message)

    def build_health_check_request(self, service_name: Optional[str] = None) -> bytes:
        """Build a health check request message."""
        message = {"type": "HEALTH_CHECK_REQUEST"}
        if service_name:
            message["service_name"] = service_name
        return self._build_json_fallback(message)

    def _build_json_fallback(self, message: Dict[str, Any]) -> bytes:
        """
        Fallback JSON serialization until FlatBuffers Python bindings are available.

        This allows the system to work while the FlatBuffers Python code generation
        is being set up.
        """
        import json
        return json.dumps(message).encode('utf-8')

    def finish(self) -> bytes:
        """Finish building and return the buffer."""
        # This would be the actual FlatBuffers finish() call
        # For now, return empty bytes since we're using JSON fallback
        return b""