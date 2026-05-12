"""
GPIO Controller
Python abstraction for GPIO operations using the C++ hardware server.

This module provides a clean Python interface for GPIO control that communicates
with the C++ hardware server via ZeroMQ messaging.

When the hardware server is unreachable, the controller falls back to simulation
mode that tracks pin state in-memory so CI and development flows are not blocked.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import the real messaging client; degrade gracefully if unavailable
try:
    from ..core.messaging.client import MessagingClient
    MESSAGING_AVAILABLE = True
except (ImportError, SystemError):
    MessagingClient = None  # type: ignore[assignment,misc]
    MESSAGING_AVAILABLE = False
    logger.warning("MessagingClient not available. GPIO controller can only run in simulation mode.")


class GPIOMode(Enum):
    """GPIO pin modes."""
    INPUT = "input"
    OUTPUT = "output"


class SimulationGPIOClient:
    """In-memory GPIO client for testing when the C++ hardware server is unavailable.

    Tracks pin configuration and values locally so the full GPIOController
    API works without a broker or hardware server.
    """

    def __init__(self):
        self._pin_configs: Dict[int, str] = {}
        self._pin_values: Dict[int, bool] = {}

    async def connect(self):
        logger.info("SimulationGPIOClient connected (no-op)")

    async def disconnect(self):
        logger.info("SimulationGPIOClient disconnected (no-op)")

    async def send_gpio_configure_request(self, pin: int, mode: str) -> dict:
        self._pin_configs[pin] = mode
        self._pin_values.setdefault(pin, False)
        return {"success": True, "pin": pin, "mode": mode}

    async def send_gpio_set_request(self, pin: int, value: bool) -> dict:
        self._pin_values[pin] = value
        return {"success": True, "pin": pin, "value": value}

    async def send_gpio_get_request(self, pin: int) -> dict:
        value = self._pin_values.get(pin, False)
        return {"success": True, "pin": pin, "value": value}

    async def send_gpio_status_request(self) -> dict:
        pins = [
            {"pin": p, "mode": self._pin_configs.get(p, "unknown"), "value": self._pin_values.get(p, False)}
            for p in sorted(self._pin_configs)
        ]
        return {"pins": pins}


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

    def __init__(self, broker_url: str = "tcp://localhost:5555", simulation: Optional[bool] = None):
        """
        Initialize GPIO controller.

        Args:
            broker_url: ZeroMQ broker URL for hardware server communication
            simulation: Tri-state control.
                ``None``  (default) – try hardware server, fall back to simulation on failure.
                ``True``  – force simulation mode.
                ``False`` – hardware only, raise on failure.
        """
        self.broker_url = broker_url
        self._simulation_requested = simulation
        self.simulation_mode = simulation is True
        self._client = None
        self._configured_pins: Dict[int, GPIOMode] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to the hardware server via ZeroMQ, or enter simulation mode."""
        if self._simulation_requested is True or not MESSAGING_AVAILABLE:
            self._client = SimulationGPIOClient()
            await self._client.connect()
            self.simulation_mode = True
            logger.warning("GPIO controller running in simulation mode")
            return

        try:
            self._client = MessagingClient(self.broker_url)
            await self._client.connect()
            logger.info("GPIO controller connected to hardware server")
        except Exception as e:
            if self._simulation_requested is None:
                logger.warning(f"Hardware server unavailable ({e}). Falling back to simulation mode.")
                self._client = SimulationGPIOClient()
                await self._client.connect()
                self.simulation_mode = True
            else:
                raise

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