"""
GPIO Controller

High-level interface for GPIO operations using the HardwareClient.
Provides convenient methods for common GPIO tasks.
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from .hardware_client import HardwareClient, GPIOConfig

logger = logging.getLogger(__name__)


class GPIOController:
    """High-level GPIO controller using HardwareClient"""

    def __init__(self, host: str = "localhost", port: int = 8081):
        self.client = HardwareClient(host, port)

    @contextmanager
    def connection(self):
        """Context manager for hardware connection"""
        try:
            if self.client.connect():
                yield self.client
            else:
                raise RuntimeError("Failed to connect to hardware server")
        finally:
            self.client.disconnect()

    def setup_output_pin(self, pin: int, initial_value: int = 0) -> bool:
        """Configure pin as output and set initial value"""
        with self.connection() as client:
            if client.configure_gpio(pin, "output"):
                return client.set_gpio_value(pin, initial_value)
        return False

    def setup_input_pin(self, pin: int) -> bool:
        """Configure pin as input"""
        with self.connection() as client:
            return client.configure_gpio(pin, "input")
        return False

    def set_pin_high(self, pin: int) -> bool:
        """Set output pin to high (1)"""
        with self.connection() as client:
            return client.set_gpio_value(pin, 1)
        return False

    def set_pin_low(self, pin: int) -> bool:
        """Set output pin to low (0)"""
        with self.connection() as client:
            return client.set_gpio_value(pin, 0)
        return False

    def get_pin_value(self, pin: int) -> Optional[int]:
        """Read input pin value"""
        with self.connection() as client:
            return client.get_gpio_value(pin)
        return None

    def toggle_pin(self, pin: int) -> Optional[int]:
        """Toggle output pin and return new value"""
        with self.connection() as client:
            current_value = client.get_gpio_value(pin)
            if current_value is not None:
                new_value = 1 - current_value
                if client.set_gpio_value(pin, new_value):
                    return new_value
        return None

    def blink_pin(self, pin: int, times: int = 3, duration: float = 0.5) -> bool:
        """Blink pin multiple times"""
        import time

        try:
            with self.connection() as client:
                for _ in range(times):
                    client.set_gpio_value(pin, 1)
                    time.sleep(duration)
                    client.set_gpio_value(pin, 0)
                    time.sleep(duration)
            return True
        except Exception as e:
            logger.error(f"Failed to blink pin {pin}: {e}")
            return False

    def get_all_pins_status(self) -> Optional[Dict[int, Any]]:
        """Get status of all configured pins"""
        with self.connection() as client:
            return client.get_gpio_status()
        return None

    # Convenience methods for common devices

    def control_led(self, pin: int, state: bool) -> bool:
        """Control LED connected to pin"""
        return self.set_pin_high(pin) if state else self.set_pin_low(pin)

    def read_button(self, pin: int) -> Optional[bool]:
        """Read button state (assuming active high)"""
        value = self.get_pin_value(pin)
        return value == 1 if value is not None else None

    def control_relay(self, pin: int, state: bool) -> bool:
        """Control relay module"""
        return self.control_led(pin, state)

    def read_sensor(self, pin: int) -> Optional[bool]:
        """Read digital sensor"""
        return self.read_button(pin)