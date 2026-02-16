# Citroën C4 Vehicle Bridge

Hexagonal architecture adapter specifically designed for Citroën C4 (2012) integration with Android USB-OTG connections. Provides PSA manufacturer-specific diagnostics, DPF monitoring, and real-time telemetry processing.

## Features

- **PSA Protocol Support**: Implements Citroën/Peugeot manufacturer-specific OBD commands
- **DPF Monitoring**: Comprehensive Diesel Particulate Filter monitoring and regeneration
- **Eolys Additive Tracking**: Fluid level monitoring for DPF additive system
- **Android Integration**: Optimized for Android USB-OTG with Termux compatibility
- **Hexagonal Architecture**: Clean separation of concerns with adapter pattern
- **ZeroMQ Integration**: Real-time telemetry streaming with FlatBuffers serialization

## Supported Citroën C4 Models

- **Model Year**: 2012
- **Engine Types**: HDi (diesel), petrol variants
- **Transmission**: Manual, ETG (Electronic Gearbox), automatic
- **Equipment Levels**: VTi, VTR, VTR+, Exclusive

## PSA-Specific Features

### DPF (Diesel Particulate Filter) System
- **Soot Mass Monitoring**: Real-time particulate accumulation tracking
- **Regeneration Control**: Automatic and manual regeneration cycle management
- **Eolys Additive Level**: SCR (Selective Catalytic Reduction) fluid monitoring
- **Differential Pressure**: Filter restriction monitoring
- **Efficiency Calculation**: Filter performance percentage

### Engine Management (EDC15/17)
- **Temperature Monitoring**: Engine, transmission, and oil temperatures
- **Fuel System**: Injection timing, rail pressure, fuel consumption
- **Turbo Control**: Boost pressure, wastegate operation
- **Emission Control**: EGR (Exhaust Gas Recirculation) monitoring

### BSI (Body Control Interface)
- **Vehicle Modes**: Eco, Sport, and maintenance mode detection
- **Security Systems**: Central locking, alarm, and immobilizer status
- **Comfort Systems**: Climate control, lighting, and wiper controls

## Installation

```bash
pip install -r requirements.txt
```

### Android Setup

1. **Termux Installation**:
   ```bash
   pkg install python
   pip install pyserial flatbuffers pyzmq
   ```

2. **USB Permissions**:
   ```bash
   termux-setup-storage
   # Grant USB permissions when prompted
   ```

3. **MIA Bootstrap**:
   ```bash
   python complete-bootstrap.py  # Detects android-arm64 automatically
   ```

## Configuration

```python
config = {
    "model_year": 2012,
    "engine_type": "HDi",           # HDi, VTi, etc.
    "transmission_type": "manual",  # manual, etg, automatic
    "equipment_level": "VTi",       # VTi, VTR, Exclusive
    "usb_device_path": "/dev/ttyUSB0",
    "baud_rate": 38400
}
```

## Usage

### Standalone Mode

```python
from citroen_c4_bridge import CitroenC4Bridge

config = {
    "model_year": 2012,
    "engine_type": "HDi"
}

bridge = CitroenC4Bridge(config)
await bridge.initialize()

# Get vehicle status
status = await bridge.get_vehicle_status()
print(f"DPF Status: {status['telemetry']['dpf_status']}")

# Get diagnostics report
report = await bridge.get_diagnostics_report()
print(f"DTC Codes: {report['dtc_codes']}")
```

### Integration with Automotive MCP Bridge

The Citroën C4 Bridge integrates with the existing Automotive MCP Bridge to provide:

```python
# Voice commands for DPF
"Check DPF status" -> Returns soot mass, regeneration status
"Initiate DPF regeneration" -> Starts regeneration cycle
"Check additive level" -> Returns Eolys fluid level

# Emergency monitoring
"Engine temperature high" -> Triggers warning if coolant > 110°C
"Battery voltage low" -> Alerts if voltage < 11.5V
```

## Telemetry Data

The bridge provides comprehensive telemetry including:

### Standard OBD-II
- Engine RPM, speed, coolant temperature
- Fuel level, battery voltage
- Throttle position, engine load

### Citroën PSA Specific
- **DPF Soot Mass** (grams): Particulate accumulation
- **DPF Status**: OK, Soot High, Regeneration Needed, Error
- **Eolys Level** (liters): Additive fluid remaining
- **Differential Pressure** (kPa): Filter restriction
- **Filter Efficiency** (%): Performance indicator

### System Status
- **Vehicle Mode**: Eco, Sport, Regeneration, Maintenance
- **Transmission Temp**: EDC transmission temperature
- **AC Pressure**: Climate control system pressure
- **DTC Codes**: PSA-specific diagnostic trouble codes

## DPF Management

### Automatic Monitoring
- Continuous soot mass tracking
- Regeneration cycle detection
- Additive level monitoring
- Filter efficiency calculation

### Manual Regeneration
```python
result = await bridge.perform_dpf_regeneration()
if result["success"]:
    print(f"Regeneration started, duration: {result['estimated_duration_min']} min")
```

### Health Assessment
- Filter condition evaluation
- Regeneration history tracking
- Maintenance interval prediction
- Failure mode detection

## Diagnostics & Maintenance

### DTC Code Mapping
PSA-specific DTC codes are mapped to descriptions:
- `P2452`: Diesel Particulate Filter Pressure Sensor Circuit
- `P242F`: DPF Restriction - Ash Accumulation
- `P2000`: NOx Trap Efficiency Below Threshold

### Maintenance Recommendations
- Service interval tracking
- Fluid level monitoring
- Filter replacement scheduling
- Component health assessment

## Architecture

### Hexagonal Design
- **Core Domain**: Citroën C4 specific business logic
- **Input Adapters**: OBD transport agent, ZeroMQ subscribers
- **Output Adapters**: MCP tools, telemetry publishers
- **Infrastructure**: Android USB, FlatBuffers serialization

### Component Integration
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Automotive MCP  │────│ Citroën C4       │────│ OBD Transport   │
│ Bridge          │    │ Bridge           │    │ Agent           │
│ (Voice Control) │    │ (PSA Logic)      │    │ (ELM327)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────────────┐
                    │ Android USB-OTG    │
                    │ Hardware Interface │
                    └────────────────────┘
```

## Troubleshooting

### Connection Issues

1. **USB Device Not Found**:
   ```bash
   ls /dev/ttyUSB*  # Check device enumeration
   lsusb            # Verify USB device detection
   ```

2. **Permission Denied**:
   ```bash
   # Grant USB permissions in Android settings
   # Or use termux-usb for direct access
   termux-usb -r /dev/bus/usb/001/002
   ```

3. **Protocol Mismatch**:
   - Ensure correct PSA CAN protocol (6)
   - Verify ECU address (7E0)
   - Check baud rate (38400)

### DPF Issues

1. **Regeneration Fails**:
   - Check engine temperature (>80°C)
   - Verify vehicle speed (>60 km/h)
   - Ensure adequate fuel level (>15%)

2. **Additive Level Low**:
   - Refill Eolys fluid at service center
   - Check for additive system leaks
   - Monitor consumption rate

### Performance Issues

1. **High Latency**: Reduce telemetry frequency
2. **Battery Drain**: Implement sleep modes
3. **Memory Usage**: Monitor FlatBuffers allocation

## Testing

### Unit Tests
```bash
pytest tests/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v --android-device
```

### Hardware Simulation
```bash
python main.py --simulation-mode
```

## API Reference

### Core Classes

- `CitroenC4Bridge`: Main bridge implementation
- `CitroenC4Telemetry`: Telemetry data structure
- `DPFStatus`: DPF condition enumeration

### Key Methods

- `initialize()`: Setup bridge and connections
- `get_vehicle_status()`: Comprehensive vehicle status
- `get_diagnostics_report()`: Detailed diagnostics
- `perform_dpf_regeneration()`: Manual regeneration

### ZeroMQ Topics

- `citroen_c4/telemetry`: Real-time telemetry data
- `citroen_c4/status`: Bridge status updates
- `citroen_c4/alerts`: Critical condition alerts

## Contributing

1. Follow hexagonal architecture principles
2. Add PSA-specific DTC codes to mapping
3. Implement additional manufacturer PIDs
4. Update Android compatibility testing

## License

MIT License - see LICENSE file for details
