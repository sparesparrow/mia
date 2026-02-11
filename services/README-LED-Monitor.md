# MIA LED Monitor Service

The LED Monitor Service integrates the Arduino AI Service LED Monitor with the MIA ZeroMQ architecture, providing real-time visual feedback for AI states, service health, and vehicle data.

## Overview

The LED Monitor Service:
- Monitors health of all MIA services via ZeroMQ broker
- Controls 23-LED WS2812B strip for visual status indication
- Subscribes to telemetry data for OBD visualization
- Provides AI state animations and emergency override

## LED Zone Allocation

```
LED Index:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22
Function:  [P][S][S][S][S][A][A][A][A][A][A][A][A][A][A][A][B][B][B][N][N][N][N]

Legend:
[P]rivacy/Recording (LED 0)
[S]ervice Health (LEDs 1-4)
[A]I Communication Zone (LEDs 5-16)
[B]ackground Tasks/Sensors (LEDs 17-19)
[N]otification Zone (LEDs 20-22)
```

## Service Architecture

### Components

1. **Arduino LED Controller** (`arduino/led_strip_controller/`)
   - Enhanced firmware with AI state commands
   - Priority-based animation system
   - Emergency override capability

2. **Python LED Controller** (`rpi/hardware/led_controller.py`)
   - High-level interface for LED control
   - JSON serial communication
   - Mock mode for testing

3. **LED Monitor Service** (`rpi/services/led_monitor_service.py`)
   - ZeroMQ integration
   - Service health monitoring
   - Telemetry data processing

## Installation

### Arduino Setup

1. Install required libraries:
   ```bash
   arduino-cli lib install "FastLED"
   arduino-cli lib install "ArduinoJson"
   ```

2. Upload firmware:
   ```bash
   cd arduino/led_strip_controller
   ./upload.sh
   ```

### Service Installation

1. Copy service files:
   ```bash
   sudo cp rpi/services/mia-led-monitor.service /etc/systemd/system/
   sudo cp rpi/services/mia-broker.service /etc/systemd/system/
   ```

2. Reload systemd:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable and start services:
   ```bash
   sudo systemctl enable mia-broker
   sudo systemctl enable mia-led-monitor
   sudo systemctl start mia-broker
   sudo systemctl start mia-led-monitor
   ```

## Usage

### Manual Testing

1. Start broker:
   ```bash
   python3 rpi/core/messaging/broker.py
   ```

2. Start LED monitor:
   ```bash
   python3 rpi/services/led_monitor_service.py
   ```

3. Test LED control:
   ```python
   from rpi.hardware.led_controller import create_controller
   controller = create_controller('/dev/ttyUSB0')
   controller.ai_listening()
   controller.service_error('obd')
   controller.disconnect()
   ```

### API Integration

The LED monitor integrates with existing MIA services:

- **GPIO Worker**: Monitors GPIO pin status
- **OBD Worker**: Visualizes RPM, speed, temperature
- **Serial Bridge**: Receives MCU telemetry data
- **AI Services**: Shows listening/speaking states

## Commands

### AI State Commands

```json
{"cmd": "ai_state", "state": "listening", "priority": 1}
{"cmd": "ai_state", "state": "speaking", "priority": 1}
{"cmd": "ai_state", "state": "thinking", "priority": 2}
{"cmd": "ai_state", "state": "recording", "priority": 0}
{"cmd": "ai_state", "state": "error", "priority": 0}
```

### Service Status Commands

```json
{"cmd": "service_status", "service": "gpio", "status": "running", "priority": 3}
{"cmd": "service_status", "service": "obd", "status": "error", "priority": 0}
{"cmd": "service_status", "service": "api", "status": "warning", "priority": 2}
```

### OBD Data Commands

```json
{"cmd": "obd_data", "type": "rpm", "value": 75}
{"cmd": "obd_data", "type": "speed", "value": 50}
{"cmd": "obd_data", "type": "temp", "value": 90}
```

### Mode Commands

```json
{"cmd": "set_mode", "mode": "drive"}
{"cmd": "set_mode", "mode": "parked"}
{"cmd": "set_mode", "mode": "night"}
{"cmd": "set_mode", "mode": "service"}
```

### Emergency Commands

```json
{"cmd": "emergency", "action": "activate"}
{"cmd": "emergency", "action": "deactivate"}
```

## Configuration

### Service Configuration

Edit `rpi/services/mia-led-monitor.service`:

```ini
Environment=PYTHONPATH=/home/mia/ai-servis/rpi
ExecStart=/usr/bin/python3 led_monitor_service.py \
  --broker-url tcp://localhost:5555 \
  --telemetry-url tcp://localhost:5556 \
  --led-port /dev/ttyUSB0
```

### Arduino Configuration

Edit `arduino/led_strip_controller/led_strip_controller.ino`:

```cpp
#define LED_PIN 6           // LED strip data pin
#define NUM_LEDS 23         // Number of LEDs
#define LED_TYPE WS2812B    // LED type
#define COLOR_ORDER GRB     // Color order
```

## Testing

### Unit Tests

Run LED controller tests:
```bash
cd rpi/hardware
python3 test_led_controller.py
```

### Integration Tests

Run full integration tests:
```bash
cd rpi/hardware
python3 test_led_integration.py
```

### Hardware Tests

1. Verify Arduino connection:
   ```bash
   arduino-cli board list
   ```

2. Test LED strip:
   ```bash
   python3 -c "
   from rpi.hardware.led_controller import create_controller
   c = create_controller()
   c.set_color(255, 0, 0)  # Red test
   time.sleep(2)
   c.clear_all()
   c.disconnect()
   "
   ```

## Troubleshooting

### LED Strip Not Working

1. Check power supply (5V, adequate amperage)
2. Verify LED strip connections (Data, 5V, GND)
3. Check LED_PIN definition in Arduino code
4. Test with known working LED strip

### Serial Communication Issues

1. Check Arduino port: `ls /dev/ttyUSB*`
2. Verify permissions: `sudo chmod 666 /dev/ttyUSB0`
3. Check baud rate (115200)
4. Test serial connection manually

### Service Health Issues

1. Check broker is running: `systemctl status mia-broker`
2. Check LED monitor: `systemctl status mia-led-monitor`
3. Check ZeroMQ ports: `netstat -tlnp | grep 5555`
4. Check logs: `journalctl -u mia-led-monitor -f`

### Animation Priority Issues

1. Verify priority levels (0=highest, 4=lowest)
2. Check emergency override clears animations
3. Test mode switching affects brightness

## Performance Metrics

- **Command Response**: <50ms end-to-end
- **Animation FPS**: 60 FPS smooth animations
- **Memory Usage**: <2KB Arduino RAM
- **Telemetry Rate**: 10Hz OBD updates
- **Service Health**: 30-second check intervals

## Future Enhancements

- **Phase 3**: Music reactive animations, user profiles
- **Phase 4**: Gesture control, multi-strip support
- **Android App**: Remote LED control interface