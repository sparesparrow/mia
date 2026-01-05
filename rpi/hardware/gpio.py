"""
GPIO Controller
Python abstraction for GPIO operations using the C++ hardware server.

This module provides a clean Python interface for GPIO control that communicates
with the C++ hardware server via ZeroMQ messaging.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

from ..core.messaging.client import MessagingClient

logger = logging.getLogger(__name__)


class GPIOMode(Enum):
    """GPIO pin modes."""
    INPUT = "input"
    OUTPUT = "output"


class GPIOController:
    """
    GPIO Controller using C++ hardware server backend.

    Features:
    - Pin configuration (input/output)
    - Digital I/O operations
    - Bulk operations
    - Error handling and timeouts
    - Async/await support

    Usage:
        async with GPIOController() as gpio:
            await gpio.configure_pin(17, GPIOMode.OUTPUT)
            await gpio.set_pin(17, True)
            value = await gpio.get_pin(18)
    """

    def __init__(self, broker_url: str = "tcp://localhost:5555"):
        """
        Initialize GPIO controller.

        Args:
            broker_url: ZeroMQ broker URL for hardware server communication
        """
        self.broker_url = broker_url
        self._client: Optional[MessagingClient] = None
        self._configured_pins: Dict[int, GPIOMode] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to the hardware server via ZeroMQ."""
        self._client = MessagingClient(self.broker_url)
        await self._client.connect()
        logger.info("GPIO controller connected to hardware server")

    async def disconnect(self):
        """Disconnect from the hardware server."""
        if self._client:
            await self._client.disconnect()
            self._client = None
        logger.info("GPIO controller disconnected")

    async def configure_pin(self, pin: int, mode: GPIOMode) -> bool:
        """
        Configure a GPIO pin as input or output.

        Args:
            pin: GPIO pin number (0-40)
            mode: GPIO mode (INPUT or OUTPUT)

        Returns:
            True if configuration successful

        Raises:
            RuntimeError: If not connected or configuration fails
        """
        if not self._client:
            raise RuntimeError("GPIO controller not connected")

        try:
            response = await self._client.send_gpio_configure_request(pin, mode.value)

            if response.get("success", False):
                self._configured_pins[pin] = mode
                logger.debug(f"Configured GPIO pin {pin} as {mode.value}")
                return True
            else:
                error = response.get("error", "Unknown error")
                logger.error(f"Failed to configure GPIO pin {pin}: {error}")
                return False

        except Exception as e:
            logger.error(f"Error configuring GPIO pin {pin}: {e}")
            raise

    async def set_pin(self, pin: int, value: bool) -> bool:
        """
        Set the value of an output GPIO pin.

        Args:
            pin: GPIO pin number
            value: Boolean value to set

        Returns:
            True if successful

        Raises:
            RuntimeError: If pin not configured as output or operation fails
        """
        if not self._client:
            raise RuntimeError("GPIO controller not connected")

        if pin not in self._configured_pins:
            raise RuntimeError(f"GPIO pin {pin} not configured")

        if self._configured_pins[pin] != GPIOMode.OUTPUT:
            raise RuntimeError(f"GPIO pin {pin} not configured as output")

        try:
            response = await self._client.send_gpio_set_request(pin, value)

            if response.get("success", False):
                logger.debug(f"Set GPIO pin {pin} to {value}")
                return True
            else:
                error = response.get("error", "Unknown error")
                logger.error(f"Failed to set GPIO pin {pin}: {error}")
                return False

        except Exception as e:
            logger.error(f"Error setting GPIO pin {pin}: {e}")
            raise

    async def get_pin(self, pin: int) -> bool:
        """
        Get the value of a GPIO pin.

        Args:
            pin: GPIO pin number

        Returns:
            Boolean value of the pin

        Raises:
            RuntimeError: If pin not configured or operation fails
        """
        if not self._client:
            raise RuntimeError("GPIO controller not connected")

        if pin not in self._configured_pins:
            raise RuntimeError(f"GPIO pin {pin} not configured")

        try:
            response = await self._client.send_gpio_get_request(pin)

            if response.get("success", False):
                value = response.get("value", False)
                logger.debug(f"Read GPIO pin {pin}: {value}")
                return bool(value)
            else:
                error = response.get("error", "Unknown error")
                logger.error(f"Failed to read GPIO pin {pin}: {error}")
                raise RuntimeError(f"Failed to read GPIO pin {pin}: {error}")

        except Exception as e:
            logger.error(f"Error reading GPIO pin {pin}: {e}")
            raise

    async def get_status(self) -> List[Dict]:
        """
        Get status of all configured GPIO pins.

        Returns:
            List of pin status dictionaries
        """
        if not self._client:
            raise RuntimeError("GPIO controller not connected")

        try:
            response = await self._client.send_gpio_status_request()
            pins = response.get("pins", [])
            logger.debug(f"Retrieved GPIO status for {len(pins)} pins")
            return pins

        except Exception as e:
            logger.error(f"Error getting GPIO status: {e}")
            raise

    async def bulk_configure(self, pins: Dict[int, GPIOMode]) -> Dict[int, bool]:
        """
        Configure multiple GPIO pins at once.

        Args:
            pins: Dictionary mapping pin numbers to modes

        Returns:
            Dictionary mapping pin numbers to success status
        """
        results = {}
        for pin, mode in pins.items():
            try:
                success = await self.configure_pin(pin, mode)
                results[pin] = success
            except Exception as e:
                logger.error(f"Failed to configure pin {pin}: {e}")
                results[pin] = False

        return results

    async def bulk_set(self, values: Dict[int, bool]) -> Dict[int, bool]:
        """
        Set multiple GPIO pins at once.

        Args:
            values: Dictionary mapping pin numbers to boolean values

        Returns:
            Dictionary mapping pin numbers to success status
        """
        results = {}
        for pin, value in values.items():
            try:
                success = await self.set_pin(pin, value)
                results[pin] = success
            except Exception as e:
                logger.error(f"Failed to set pin {pin}: {e}")
                results[pin] = False

        return results

    def get_configured_pins(self) -> Dict[int, GPIOMode]:
        """Get dictionary of configured pins and their modes."""
        return self._configured_pins.copy()

    def is_pin_configured(self, pin: int) -> bool:
        """Check if a pin is configured."""
        return pin in self._configured_pins

    def get_pin_mode(self, pin: int) -> Optional[GPIOMode]:
        """Get the mode of a configured pin."""
        return self._configured_pins.get(pin)