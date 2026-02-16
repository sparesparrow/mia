# OBD Transport Agent

MCP-compatible tool for OBD-II communication with Android USB-OTG support, specifically designed for Citroën C4 integration.

## Features

- **Android USB-OTG Support**: Handles Android-specific USB permissions and device access
- **Citroën C4 PSA Protocol**: Implements manufacturer-specific CAN bus communication for PSA vehicles
- **Real-time Telemetry**: Streams vehicle data via ZeroMQ with FlatBuffers serialization
- **Remediation Matrix**: Automatic handling of connection failures and protocol issues
- **MCP Tool Interface**: Compatible with Model Context Protocol for AI agent integration

## Supported Vehicles

- Citroën C4 (2012 model year)
- PSA Group vehicles with EDC15/17 ECUs
- Any OBD-II compliant vehicle (with reduced feature set)

## Citroën C4 Specific Features

- **DPF Monitoring**: Soot mass, regeneration status, and efficiency
- **Eolys Additive Level**: Fluid level monitoring for diesel particulate filter
- **Differential Pressure**: DPF pressure differential monitoring
- **PSA PIDs**: Manufacturer-specific parameter IDs for enhanced diagnostics

## Installation

```bash
pip install -r requirements.txt
```

## Android Setup

1. **USB OTG Permissions**: Ensure Android device supports USB OTG and grant permissions
2. **Bootstrap MIA**: Run `complete-bootstrap.py` on Android (detects android-arm64 platform)
3. **USB Device Path**: Typically `/dev/bus/usb/*` or `/dev/ttyUSB0`

## Usage

### Standalone Mode

```bash
python main.py
```

### MCP Tool Mode

```bash
python main.py --mcp
```

## Configuration

```python
config = {
    "usb_device_path": "/dev/ttyUSB0",      # Android USB device path
    "baud_rate": 38400,                     # ELM327 baud rate
    "protocol": "6",                        # ISO 15765-4 CAN (11-bit, 500k)
    "vehicle_model": "citroen_c4_2012",     # Vehicle identification
    "psa_ecu_address": "7E0",               # Main ECU address
    "timeout_seconds": 5.0                  # Command timeout
}
```

## Telemetry Data

The agent streams the following data via ZeroMQ (port 5556):

- **Standard OBD**: RPM, speed, coolant temp, fuel level, battery voltage
- **Citroën Specific**: DPF soot mass, Eolys additive level, differential pressure
- **Engine Data**: Throttle position, engine load, intake temp, MAF sensor
- **Diagnostics**: DTC codes, sensor voltages

## Remediation Matrix

Automatic handling of common connection issues:

- **Category A (Critical)**: USB permission denied → User intervention required
- **Category B (Transient)**: Bus initialization errors → Automatic retry with delay
- **Category C (Environmental)**: ECU not responding → Poll voltage, wait for ignition
- **Category D (Configuration)**: Protocol mismatch → Fallback PID maps

## API Reference

### MCP Tools

- `connect_obd`: Initialize OBD connection
- `read_telemetry`: Get current vehicle data
- `get_status`: Agent status and diagnostics
- `send_raw_command`: Send custom OBD commands

### ZeroMQ Topics

- `telemetry`: Real-time vehicle data (JSON/FlatBuffers)
- `status`: Agent connection status
- `diagnostics`: Error and remediation information

## Troubleshooting

### Connection Issues

1. **USB Permissions**: Check Android USB debugging and OTG settings
2. **Device Path**: Verify `/dev/ttyUSB0` exists and is accessible
3. **Ignition**: Ensure vehicle ignition is ON (not just accessories)
4. **Eco Mode**: Citroën C4 may restrict OBD access in eco mode

### Protocol Issues

1. **CAN Protocol**: Verify ISO 15765-4 (protocol 6) is correct
2. **ECU Address**: Confirm 7E0 is the correct PSA ECU address
3. **Baud Rate**: Try 38400 or 115200 depending on adapter

### Android Specific

1. **OTG Power**: Ensure phone can power the ELM327 adapter
2. **USB Hubs**: Use powered USB hub if current is insufficient
3. **Termux**: Run in Termux with proper storage permissions

## Architecture

The agent implements a hexagonal architecture with clear separation of concerns:

- **Transport Layer**: pyserial communication with ELM327
- **Protocol Layer**: OBD-II and PSA-specific command handling
- **Data Layer**: FlatBuffers serialization for efficiency
- **Communication Layer**: ZeroMQ pub/sub for real-time streaming
- **Remediation Layer**: Automatic failure recovery and user guidance
