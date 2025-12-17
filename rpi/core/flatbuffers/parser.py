"""
FlatBuffers Message Parser
Parses FlatBuffers messages received over ZeroMQ.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime


class MessageParser:
    """
    Parser for FlatBuffers messages received over ZeroMQ.

    This class provides methods to parse different types of response messages.
    """

    def parse_message(self, data: bytes) -> Dict[str, Any]:
        """
        Parse a message buffer into a dictionary.

        Currently uses JSON fallback until FlatBuffers Python bindings are available.
        """
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # If it's not JSON, assume it's raw FlatBuffers data
            # This would need the actual FlatBuffers parsing logic
            return {"error": "Unable to parse message", "raw_data": data.hex()}

    def parse_download_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a download response message."""
        return self.parse_message(data)

    def parse_download_status_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a download status response message."""
        return self.parse_message(data)

    def parse_error_response(self, data: bytes) -> Dict[str, Any]:
        """Parse an error response message."""
        return self.parse_message(data)

    def parse_gpio_configure_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a GPIO configure response message."""
        return self.parse_message(data)

    def parse_gpio_set_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a GPIO set response message."""
        return self.parse_message(data)

    def parse_gpio_get_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a GPIO get response message."""
        return self.parse_message(data)

    def parse_gpio_status_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a GPIO status response message."""
        return self.parse_message(data)

    def parse_system_status_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a system status response message."""
        return self.parse_message(data)

    def parse_device_discovery_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a device discovery response message."""
        return self.parse_message(data)

    def parse_telemetry_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a telemetry response message."""
        return self.parse_message(data)

    def parse_command_ack_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a command acknowledgment response message."""
        return self.parse_message(data)

    def parse_health_check_response(self, data: bytes) -> Dict[str, Any]:
        """Parse a health check response message."""
        return self.parse_message(data)

    # ------------------------------------------------------------------
    # Helper methods for extracting specific data from responses
    # ------------------------------------------------------------------

    def extract_error_message(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract error message from a response."""
        return response.get("error")

    def extract_gpio_pin_value(self, response: Dict[str, Any]) -> Optional[bool]:
        """Extract GPIO pin value from a response."""
        return response.get("value")

    def extract_download_session_id(self, response: Dict[str, Any]) -> Optional[int]:
        """Extract download session ID from a response."""
        return response.get("session_id")

    def extract_system_status(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract system status information from a response."""
        return {
            "uptime_seconds": response.get("uptime_seconds", 0),
            "memory_used_mb": response.get("memory_used_mb", 0),
            "memory_total_mb": response.get("memory_total_mb", 0),
            "cpu_usage_percent": response.get("cpu_usage_percent", 0.0),
            "active_devices": response.get("active_devices", 0),
            "timestamp": response.get("timestamp", 0)
        }

    def extract_devices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract device list from a device discovery response."""
        return response.get("devices", [])

    def extract_telemetry_readings(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract telemetry readings from a response."""
        device_readings = []
        readings = response.get("readings", [])
        for reading in readings:
            device_readings.append({
                "sensor_id": reading.get("sensor_id", ""),
                "sensor_type": reading.get("sensor_type", ""),
                "value": reading.get("value", 0.0),
                "unit": reading.get("unit", ""),
                "timestamp": reading.get("timestamp", 0),
                "metadata": reading.get("metadata", [])
            })
        return device_readings

    def extract_service_health(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract service health information from a response."""
        services = []
        service_list = response.get("services", [])
        for service in service_list:
            services.append({
                "service_name": service.get("service_name", ""),
                "status": service.get("status", "unknown"),
                "uptime_seconds": service.get("uptime_seconds", 0),
                "last_check": service.get("last_check", 0),
                "error_message": service.get("error_message", "")
            })
        return services

    def is_success_response(self, response: Dict[str, Any]) -> bool:
        """Check if a response indicates success."""
        success = response.get("success", True)
        return success and response.get("type", "").endswith("_RESPONSE")