# Citroën Testing Checklist

## Pre-Test Setup
- [ ] ELM327 adapter connected to OBD-II port
- [ ] Raspberry Pi powered and connected
- [ ] All services started: `systemctl status mia-*`

## Basic Connectivity Tests

### 1. Verify ELM327 Connection
```bash
# Check serial port
ls -l /dev/ttyUSB*

# Test AT commands manually
screen /dev/ttyUSB0 38400
> ATZ      # Reset - should return "ELM327 v1.5"
> ATE0     # Echo off
> ATSP0    # Auto protocol
```

### 2. Test Mock Mode
```bash
ELM_MOCK=1 python3 agents/citroen_bridge.py
```
**Expected**: ZMQ publisher starts, publishes random telemetry every 0.5s

### 3. Test Real Vehicle Connection
- Start engine
- Run: `sudo systemctl start mia-citroen-bridge`
- Check logs: `journalctl -u mia-citroen-bridge -f`
- **Expected**: RPM, speed, coolant temp readings

## Standard OBD-II PIDs Test
- [ ] Engine RPM (PID 010C) - Range: 0-6500 RPM
- [ ] Vehicle Speed (PID 010D) - Range: 0-255 km/h
- [ ] Coolant Temperature (PID 0105) - Range: -40 to 215°C
- [ ] Throttle Position (PID 0111) - Range: 0-100%

## PSA-Specific PIDs Test
- [ ] DPF Soot Mass (Mode 21)
- [ ] DPF Regeneration Status
- [ ] Oil Temperature
- [ ] Eolys Additive Level (C5 HDi only)

## Safety Checklist
- [ ] **NEVER** use `force_regen` while stationary
- [ ] Do not run continuous tests for >30 minutes
- [ ] Monitor coolant temperature (stop if >105°C)
- [ ] Test in safe environment (empty parking lot)
- [ ] Have backup OBD scanner available

## ZMQ Subscriber Test
```python
import zmq
ctx = zmq.Context()
sock = ctx.socket(zmq.SUB)
sock.connect('tcp://localhost:5557')
sock.subscribe('')
while True:
    data = sock.recv()
    print(f"Received {len(data)} bytes")
```
