"""Unit tests for GPIO controller simulation mode."""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


def load_gpio_module():
    """Import the gpio module directly for unit testing, bypassing relative imports."""
    module_path = Path(__file__).resolve().parents[2] / "apps" / "rpi-backend" / "py-api" / "hardware" / "gpio.py"
    source = module_path.read_text()
    # Patch out the relative import that requires the full package tree
    patched = source.replace(
        "from ..core.messaging.client import MessagingClient",
        "MessagingClient = None  # patched for test",
    )
    spec = importlib.util.spec_from_file_location("mia_gpio", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(patched, str(module_path), "exec"), module.__dict__)
    # Ensure MESSAGING_AVAILABLE is False since we patched the import
    module.MESSAGING_AVAILABLE = False
    return module


# ── SimulationGPIOClient unit tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_simulation_client_configure():
    """SimulationGPIOClient should track pin configuration."""
    module = load_gpio_module()
    client = module.SimulationGPIOClient()

    resp = await client.send_gpio_configure_request(17, "output")
    assert resp["success"] is True
    assert resp["pin"] == 17


@pytest.mark.asyncio
async def test_simulation_client_set_and_get():
    """SimulationGPIOClient should store and return pin values."""
    module = load_gpio_module()
    client = module.SimulationGPIOClient()

    await client.send_gpio_configure_request(17, "output")
    await client.send_gpio_set_request(17, True)
    resp = await client.send_gpio_get_request(17)

    assert resp["success"] is True
    assert resp["value"] is True


@pytest.mark.asyncio
async def test_simulation_client_status():
    """SimulationGPIOClient should report all configured pins."""
    module = load_gpio_module()
    client = module.SimulationGPIOClient()

    await client.send_gpio_configure_request(17, "output")
    await client.send_gpio_configure_request(18, "input")

    resp = await client.send_gpio_status_request()
    assert len(resp["pins"]) == 2


# ── GPIOController simulation integration tests ──────────────────────


@pytest.mark.asyncio
async def test_controller_connect_simulation_forced():
    """simulation=True should use SimulationGPIOClient."""
    module = load_gpio_module()
    gpio = module.GPIOController(simulation=True)

    await gpio.connect()

    assert gpio.simulation_mode is True
    assert isinstance(gpio._client, module.SimulationGPIOClient)

    await gpio.disconnect()


@pytest.mark.asyncio
async def test_controller_connect_auto_falls_back():
    """simulation=None should fall back to simulation when MessagingClient unavailable."""
    module = load_gpio_module()
    gpio = module.GPIOController(simulation=None)

    await gpio.connect()

    assert gpio.simulation_mode is True
    assert isinstance(gpio._client, module.SimulationGPIOClient)

    await gpio.disconnect()


@pytest.mark.asyncio
async def test_controller_configure_and_set_in_simulation():
    """Full GPIO workflow should work in simulation mode."""
    module = load_gpio_module()
    gpio = module.GPIOController(simulation=True)

    await gpio.connect()

    # Configure pin
    success = await gpio.configure_pin(17, module.GPIOMode.OUTPUT)
    assert success is True
    assert gpio.is_pin_configured(17)
    assert gpio.get_pin_mode(17) == module.GPIOMode.OUTPUT

    # Set pin
    success = await gpio.set_pin(17, True)
    assert success is True

    # Read pin
    value = await gpio.get_pin(17)
    assert value is True

    # Get status
    status = await gpio.get_status()
    assert len(status) == 1

    await gpio.disconnect()


@pytest.mark.asyncio
async def test_controller_bulk_operations_in_simulation():
    """Bulk configure and set should work in simulation mode."""
    module = load_gpio_module()
    gpio = module.GPIOController(simulation=True)

    await gpio.connect()

    # Bulk configure
    results = await gpio.bulk_configure({
        17: module.GPIOMode.OUTPUT,
        18: module.GPIOMode.OUTPUT,
        22: module.GPIOMode.INPUT,
    })
    assert all(results.values())

    # Bulk set
    results = await gpio.bulk_set({17: True, 18: False})
    assert all(results.values())

    assert gpio.get_configured_pins() == {
        17: module.GPIOMode.OUTPUT,
        18: module.GPIOMode.OUTPUT,
        22: module.GPIOMode.INPUT,
    }

    await gpio.disconnect()


@pytest.mark.asyncio
async def test_controller_context_manager_in_simulation():
    """Async context manager should work with simulation mode."""
    module = load_gpio_module()

    async with module.GPIOController(simulation=True) as gpio:
        assert gpio.simulation_mode is True
        await gpio.configure_pin(17, module.GPIOMode.OUTPUT)
        await gpio.set_pin(17, True)
        assert await gpio.get_pin(17) is True
