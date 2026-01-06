# MIA (Modular IoT Assistant)

MIA is a comprehensive IoT assistant platform supporting multiple hardware targets with AI-powered voice control, hardware monitoring, and automated deployment capabilities.

## Project Structure

This repository follows a modular architecture with separate directories for different platforms and components:

```
mia/
├── schemas/          # FlatBuffers schema definitions (shared interfaces)
├── rpi/             # Raspberry Pi orchestration and Python services
├── android/         # Android companion application
└── docs/           # Project documentation (inherited from main repo)
```

## Architecture Overview

### Communication Flow
```
Android App ↔ Raspberry Pi (WebSocket/REST/MQTT)
    ↓
Raspberry Pi ↔ ESP32 Devices (Serial/WiFi)
    ↓
Raspberry Pi ↔ Arduino Peripherals (Serial)
```

### Shared Interfaces
All components communicate using FlatBuffers schemas defined in `schemas/`:
- **Efficient serialization** for real-time data
- **Cross-platform compatibility** (Python, Java/Kotlin, C++)
- **Versioned interfaces** for API evolution

## Components

### 🎯 Schemas (`schemas/`)
- **FlatBuffers definitions** for all inter-component communication
- **Shared data structures** ensuring type safety across platforms
- **Schema evolution** support for backward/forward compatibility

### 🥧 Raspberry Pi (`rpi/`)
- **Central orchestration hub** running Python services
- **Hardware abstraction layer** for GPIO, sensors, cameras
- **REST/WebSocket APIs** for Android communication
- **ZeroMQ messaging** for internal service communication
- **Systemd services** for production deployment

### 🤖 Android App (`android/`)
- **Mobile companion interface** with Material Design 3
- **BLE device discovery** and OBD-II adapter communication
- **Real-time telemetry** visualization and control
- **Voice command processing** with AI assistance
- **Offline operation** with local data storage

## Development Setup

### Prerequisites
- **Python 3.9+** for Raspberry Pi development
- **Android Studio** for Android development
- **FlatBuffers compiler** for schema generation
- **Docker** for containerized development

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/sparesparrow/mia.git
   cd mia
   ```

2. **Set up FlatBuffers schemas**
   ```bash
   cd schemas
   # Generate code for target platforms
   flatc --python *.fbs
   flatc --java *.fbs
   ```

3. **Raspberry Pi development**
   ```bash
   cd rpi
   pip install -r requirements.txt
   python -m uvicorn api.main:app --reload
   ```

4. **Android development**
   ```bash
   cd android
   # Open in Android Studio
   ./gradlew build
   ```

## Building and Deployment

### Raspberry Pi
```bash
cd rpi
docker build -t mia-rpi .
docker run -p 8000:8000 mia-rpi
```

### Android
```bash
cd android
./gradlew assembleRelease
# Deploy to device or generate bundle for Play Store
```

### Multi-platform Development
```bash
# Use docker-compose for integrated development
docker-compose up
```

## Testing

### Unit Tests
```bash
# Python tests (Raspberry Pi)
cd rpi && python -m pytest tests/ -v

# Android tests
cd android && ./gradlew test
```

### Integration Tests
```bash
# End-to-end testing
cd rpi && python test_integration.py

# Hardware testing
cd rpi && python hardware/test_end_to_end.py
```

## Contributing

### Development Workflow
1. **Schema changes** → Update FlatBuffers definitions
2. **Code generation** → Regenerate platform-specific code
3. **Cross-platform testing** → Verify compatibility
4. **Documentation updates** → Keep READMEs synchronized

### Code Organization
- **schemas/**: Interface definitions only
- **rpi/**: Python orchestration code
- **android/**: Kotlin/Android application code
- **docs/**: Documentation and guides

### Commit Guidelines
- Use conventional commits
- Reference schema changes when updating interfaces
- Include platform-specific tags (rpi/, android/)

## Deployment Environments

### Development
- Local Docker Compose setup
- Hot reloading for rapid iteration
- Mock hardware interfaces

### Staging
- Raspberry Pi with real hardware
- Android emulator/device testing
- Integration test suites

### Production
- Systemd services on Raspberry Pi
- Signed Android APKs
- Monitoring and logging
- Automated updates

## Related Projects

- **BPM Detector**: ESP32-based heart rate monitoring with Arduino display client
- **OMS**: OpenSSL Management System (similar modular architecture)
- **SpareTools**: Pre-built components and dependency management

## License

See LICENSE file for details.

## Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and community support