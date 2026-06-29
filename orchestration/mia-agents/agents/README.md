# PSA/Citroën Telemetry Agent

> Legacy bridge: Citroën/PSA diagnostics are maintained for compatibility. New MIA automotive development targets the Audi A4 B3 read-only path first.

This agent bridges an ELM327 OBD-II adapter to the Mia system via ZeroMQ. It queries standard and PSA-specific PIDs (like DPF Soot Mass, Eolys Level) and publishes them as FlatBuffers messages.

## Setup

1.  **Dependencies**:
    The agent runs using the system Python. Required packages:
    - `pyserial`
    - `pyzmq`
    - `flatbuffers` (>= 23.5.26)

    If they are not installed, you can install them (note: on some systems this requires `--break-system-packages` or using apt):
    ```bash
    pip install --break-system-packages -r orchestration/mia-agents/agents/requirements.txt
    ```

2.  **FlatBuffers Generation**:
    The agent expects the canonical `Mia.VehicleTelemetry` bindings plus the vehicle wire wrapper validation generated from `schemas/vehicle_telemetry.fbs` and `protos/vehicle.fbs`.
    ```bash
    python3 schemas/generate.py --all --no-cpp
    ```
    (This is handled by the `conanfile.py` build step as well).

## Usage

Run the bridge script from the repository root:

```bash
export ELM_SERIAL_PORT=/dev/ttyUSB0
export ELM_BAUD_RATE=38400
export ZMQ_PUB_PORT=5556
python3 orchestration/mia-agents/agents/citroen_bridge.py
```

`ZMQ_PUB_PORT` defaults to `5556`, matching the MIA telemetry PUB/SUB path.

## Mock Mode

For testing without a vehicle/adapter, set `ELM_MOCK=1`:

```bash
ELM_MOCK=1 python3 orchestration/mia-agents/agents/citroen_bridge.py
```

This will generate random telemetry data and publish it.

## Configuration

Commands are defined in `config/commands.json`.
Decoder logic is in `orchestration/mia-agents/agents/psa_decoder.py`.
