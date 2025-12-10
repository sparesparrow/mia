# PSA/Citroën Telemetry Agent

This agent bridges an ELM327 OBD-II adapter to the Mia system via ZeroMQ. It queries standard and PSA-specific PIDs (like DPF Soot Mass, Eolys Level) and publishes them as FlatBuffers messages.

## Setup

1.  **Dependencies**:
    The agent runs using the system Python. Required packages:
    - `pyserial`
    - `pyzmq`
    - `flatbuffers` (>= 23.5.26)

    If they are not installed, you can install them (note: on some systems this requires `--break-system-packages` or using apt):
    ```bash
    pip install --break-system-packages -r agents/requirements.txt
    ```

2.  **FlatBuffers Generation**:
    The agent expects the `Mia.Vehicle` python package to be generated from `protos/vehicle.fbs`.
    ```bash
    flatc --python -o . protos/vehicle.fbs
    ```
    (This is handled by the `conanfile.py` build step as well).

## Usage

Run the bridge script:

```bash
export ELM_SERIAL_PORT=/dev/ttyUSB0
export ELM_BAUD_RATE=38400
export ZMQ_PUB_PORT=5555
python3 agents/citroen_bridge.py
```

## Mock Mode

For testing without a vehicle/adapter, set `ELM_MOCK=1`:

```bash
ELM_MOCK=1 python3 agents/citroen_bridge.py
```

This will generate random telemetry data and publish it.

## Configuration

Commands are defined in `config/commands.json`.
Decoder logic is in `agents/psa_decoder.py`.
