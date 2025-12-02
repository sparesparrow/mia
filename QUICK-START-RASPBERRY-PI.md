# Quick Start Guide - Raspberry Pi Deployment

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config \
    libcurl4-openssl-dev libmosquitto-dev libgpiod-dev \
    libjsoncpp-dev libflatbuffers-dev espeak mosquitto mosquitto-clients
```

### Step 2: Build
```bash
./scripts/build-raspberry-pi.sh
```

### Step 3: Test
```bash
cd build-raspberry-pi
./tests
```

### Step 4: Deploy
```bash
sudo ./scripts/deploy-raspberry-pi.sh
```

### Step 5: Start Service
```bash
sudo systemctl start ai-servis
sudo systemctl enable ai-servis
```

### Step 6: Verify
```bash
# Check status
sudo systemctl status ai-servis

# Test web interface
curl http://localhost:8082/api/status

# Test GPIO (if available)
echo '{"pin": 18, "direction": "output", "value": 1}' | nc localhost 8081
```

## What's Running

- **Core Orchestrator**: Port 8080 - Main command processing
- **Hardware Server**: Port 8081 - GPIO control
- **Web UI**: Port 8082 - Browser interface
- **MQTT**: Port 1883 - Message queue

## Quick Test Commands

### Voice Commands (via Text Interface)
```bash
# Connect to text interface (if running)
echo "play jazz music" | nc localhost 8080
```

### GPIO Control
```bash
# Turn on GPIO pin 18
echo '{"pin": 18, "direction": "output", "value": 1}' | nc localhost 8081

# Read GPIO pin 18
echo '{"pin": 18}' | nc localhost 8081
```

### Web API
```bash
# Get status
curl http://localhost:8082/api/status

# Send command
curl -X POST http://localhost:8082/api/command -d "set volume to 50"
```

## Troubleshooting

**Service won't start?**
```bash
sudo journalctl -u ai-servis -n 50
```

**GPIO not working?**
```bash
# Check permissions
ls -l /dev/gpiochip*

# Run with sudo
sudo systemctl restart ai-servis
```

**Port already in use?**
```bash
sudo netstat -tulpn | grep -E "8080|8081|8082"
```

## Next Steps

1. Connect hardware (LEDs, sensors) to GPIO pins
2. Configure MQTT for remote access
3. Set up voice recognition (Whisper on ESP32)
4. Customize configuration in `/opt/ai-servis/config/ai-servis.conf`

For detailed documentation, see `platforms/cpp/core/README-RASPBERRY-PI.md`
