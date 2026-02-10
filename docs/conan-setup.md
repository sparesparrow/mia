# Conan Dependency Management Setup

This document describes how to use Conan for dependency management in the ai-servis project.

## Prerequisites

1. **Install Conan**:
   ```bash
   pip install conan
   ```

2. **Configure Conan** (first time only):
   ```bash
   conan profile detect --force
   ```

## Project Dependencies

The project uses the following dependencies managed by Conan:

- **libgpiod**: GPIO control library for Raspberry Pi
- **jsoncpp**: JSON parsing library
- **mosquitto**: MQTT client for ESP32 communication
- **libcurl**: HTTP client for LLM API calls

## Building with Conan

### Option 1: Using the Build Script

The easiest way is to use the provided build script:

```bash
./scripts/build-hardware-server.sh
```

### Option 2: Manual Build

1. **Install dependencies**:
   ```bash
   cd src/hardware/build
   conan install ../../.. --profile ../../../profiles/linux-release --build missing
   ```

2. **Configure CMake**:
   ```bash
   cmake ../.. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release
   ```

3. **Build**:
   ```bash
   make -j$(nproc)
   ```

## Conan Configuration Files

### conanfile.txt
Simple dependency declaration file for basic usage.

### conanfile.py
Advanced Conan recipe with build configuration.

### profiles/linux-release
Conan profile for Linux development with GCC 13.

## Troubleshooting

### Common Issues

1. **Missing Conan profiles**:
   ```bash
   conan profile detect --force
   ```

2. **Permission issues**:
   Make sure you have write permissions in the build directory.

3. **Missing dependencies**:
   Conan will automatically download and build missing dependencies.

### Checking Conan Status

```bash
# Check Conan version
conan --version

# List installed packages
conan list "*" -c

# Check profile
conan profile show
```

## Cross-Platform Development

To add support for other platforms (Windows, macOS, ARM), create additional profiles:

```bash
# Example for Raspberry Pi (ARM)
[settings]
os=Linux
arch=armv7
compiler=gcc
compiler.version=9
...

# Example for Windows
[settings]
os=Windows
arch=x86_64
compiler=msvc
compiler.version=193
...
```

## Advanced Usage

### Custom Package Options

You can override default package options:

```bash
conan install . --options libgpiod:shared=True --options jsoncpp:shared=True
```

### Local Development

For local package development:

```bash
# Create editable package
conan editable add . --name=ai-servis --version=1.0

# Build and test
conan build .

# Remove editable
conan editable remove ai-servis/1.0
```