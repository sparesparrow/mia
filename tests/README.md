# MIA Test Suite

Comprehensive test coverage for MIA's multi-platform architecture.

## Directory Structure

### `tests/unit/`

Fast, isolated unit tests for individual components.

- **`rpi-backend/`** - Python API, hardware drivers, messaging layer
  - `test_messaging.py` - ZeroMQ broker and message routing
  - `test_hardware.py` - GPIO, sensors, serial communication
  - `test_hardware_manager.py` - Hardware abstraction layer
  - `test_arduino_protocol.py` - Arduino serial protocol
  - `test_sensors_i2c.py` - I2C sensor drivers
  - `test_api.py` - FastAPI endpoints and auth
- **`orchestration/`** - MCP framework and agents (future)
- **`android/`** - Android app unit tests (future)
- **`esp32/`** - Firmware unit tests (future)

### `tests/integration/`

Integration and end-to-end tests verifying system interactions.

#### `tests/integration/scenarios/`

Named by business flow (not technology):

- **`rpi-backend/`**
  - `test_hardware_e2e.py` - End-to-end hardware control
  - `test_led_integration.py` - LED control integration
  - `test_led_controller.py` - LED controller integration

- **`test_mia_mcp_integration.py`** - MCP module integration
- **`test_orchestrator.py`** - Core orchestrator routing

#### `tests/integration/fixtures/`

Shared test fixtures and test data:
- Mock hardware, sensors, databases
- Sample telemetry and command payloads

## Running Tests

### All Tests (excluding hardware)
```bash
pytest tests/ -m "not hardware"
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Specific Component
```bash
pytest tests/unit/rpi-backend/test_messaging.py -v
pytest tests/integration/scenarios/test_led_integration.py -v
```

### With Coverage
```bash
pytest tests/ --cov=apps --cov=orchestration --cov-report=html
```

## Test Markers

Available pytest markers:

- `@pytest.mark.unit` - Unit test (default)
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.hardware` - Requires physical hardware (skipped in CI)
- `@pytest.mark.slow` - Long-running test
- `@pytest.mark.automotive` - Automotive-specific tests

### Example: Skip Hardware Tests
```bash
pytest tests/ -m "not hardware"
```

## Test Naming Conventions

- Unit test files: `test_<component>.py` (e.g., `test_messaging.py`)
- Integration test files: `test_<scenario>.py` or `test_<scenario>_integration.py`
- Test functions: `test_<what_is_tested>()` or `test_<scenario>_<expected_result>()`

## Adding New Tests

1. **Unit test:** Create in `tests/unit/<component>/test_<name>.py`
2. **Integration test:** Create in `tests/integration/scenarios/test_<scenario>.py`
3. **Use fixtures:** Import from `tests/integration/fixtures/`
4. **Mark appropriately:** Add `@pytest.mark.<marker>` decorator
5. **Documentation:** Add docstring explaining test purpose

## Coverage Goals

- Unit tests: ≥80% per component
- Integration tests: All critical flows covered
- Hardware tests: CI skipped (run locally on RPi)

## Debugging Tests

### Run with detailed output
```bash
pytest tests/ -vv -s
```

### Debug a specific test
```bash
pytest tests/unit/rpi-backend/test_messaging.py::test_broker_initialization -vv --tb=short
```

### Use pdb debugger
```bash
pytest tests/ --pdb  # Drop into debugger on failure
```
