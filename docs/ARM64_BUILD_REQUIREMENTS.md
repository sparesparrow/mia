# ARM64 Build Requirements and Setup Guide

This document outlines the specific requirements and procedures for building the MIA project on ARM64 platforms (Raspberry Pi 4/5, Apple Silicon Macs, ARM servers).

## Overview

The MIA project supports ARM64 architecture with both native compilation and cross-compilation workflows. The build system uses Conan for dependency management and CMake for build configuration.

## Supported ARM64 Platforms

### Primary Target: Raspberry Pi
- **Raspberry Pi 4B/5**: Primary deployment target
- **Architecture**: ARMv8-A (aarch64)
- **OS**: Raspberry Pi OS (Bookworm) or Debian 12+
- **Compiler**: GCC 11+ (system default)

### Development Platforms
- **Apple Silicon Macs**: M1/M2/M3 chips (aarch64)
- **AWS Graviton**: ARM64 cloud instances
- **Cross-compilation**: x86_64 → ARM64

## System Requirements

### Minimum Hardware
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 5GB free space for build artifacts
- **Network**: Internet connection for dependency downloads

### Software Dependencies

#### Required System Packages
```bash
# Ubuntu/Debian/Raspberry Pi OS
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    ninja-build \
    python3 \
    python3-pip \
    git \
    pkg-config \
    libgpiod-dev \
    libmosquitto-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    zlib1g-dev
```

#### Conan Package Manager
```bash
# Install Conan
pip3 install conan

# Configure for ARM64
conan profile detect --force
conan remote add sparesparrow-conan \
    https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/
```

## Conan Profile Configuration

### Native ARM64 Profile (`profiles/linux-arm64`)

```ini
[settings]
os=Linux
arch=armv8
compiler=gcc
compiler.version=11
compiler.libcxx=libstdc++11
compiler.cppstd=17
build_type=Release

[options]
libgpiod/*:shared=False
jsoncpp/*:shared=False
mosquitto/*:shared=False
libcurl/*:shared=False
openssl/*:shared=False

[conf]
tools.cmake.cmaketoolchain:generator=Ninja
tools.cmake.cmaketoolchain:system_processor=aarch64
tools.system.package_manager:mode=install
tools.system.package_manager:sudo=True
```

### Cross-Compilation Profile (`profiles/linux-x86_64`)

For building ARM64 binaries on x86_64 hosts:

```ini
[settings]
os=Linux
arch=x86_64
compiler=gcc
compiler.version=13
compiler.libcxx=libstdc++11
compiler.cppstd=17
build_type=Release

[conf]
tools.cmake.cmaketoolchain:generator=Unix Makefiles
```

## Build Procedures

### Native ARM64 Build (Raspberry Pi)

1. **Clone and setup**:
```bash
git clone https://github.com/sparesparrow/mia.git
cd mia
```

2. **Install dependencies**:
```bash
./tools/install-deps-rpi.sh
./tools/bootstrap.sh
```

3. **Configure build**:
```bash
cd platforms/cpp
conan install ../.. -pr:h=../../profiles/linux-arm64 -pr:b=../../profiles/linux-arm64 --build=missing
```

4. **Build**:
```bash
mkdir -p build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=../conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release -DWITH_HARDWARE=ON
make -j$(nproc)
```

### Cross-Compilation (x86_64 → ARM64)

1. **Setup cross-compilation environment**:
```bash
# Install ARM64 toolchain (Ubuntu/Debian)
sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
```

2. **Configure Conan**:
```bash
cd platforms/cpp
conan install ../.. -pr:h=../../profiles/linux-arm64 -pr:b=../../profiles/linux-x86_64 --build=missing
```

3. **Cross-compile**:
```bash
mkdir -p build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=../conan_toolchain.cmake \
         -DCMAKE_BUILD_TYPE=Release \
         -DWITH_HARDWARE=ON \
         -DCMAKE_SYSTEM_PROCESSOR=aarch64
make -j$(nproc)
```

### Automated Build Script

Use the provided build script for simplified builds:

```bash
# Native ARM64 build
./tools/build.sh --profile linux-arm64

# Cross-compilation
./tools/build.sh --profile linux-arm64 --cross-compile

# Clean rebuild
./tools/build.sh --clean --profile linux-arm64
```

## Architecture-Specific Considerations

### GPIO Library Compatibility

The project uses **libgpiod v2.x** API for GPIO control:

- **API Changes**: v2.x simplified the API compared to v1.x
- **Direct Line Access**: Uses `gpiod_chip_get_line()` and `gpiod_line_request_*()` functions
- **No Complex Configs**: Eliminated settings/config structs for simpler code

### Compiler Optimizations

ARM64-specific compiler flags:
- **`-mcpu=cortex-a72`**: Raspberry Pi 4 optimization
- **`-mcpu=cortex-a76`**: Raspberry Pi 5 optimization
- **`-fPIC`**: Required for shared libraries
- **`-O2`**: Recommended optimization level

### Memory Considerations

ARM64 builds may require:
- **Swap space**: Add 2GB swap for low-memory devices
- **Reduced parallelism**: Use `make -j2` instead of `-j$(nproc)`
- **Linker optimization**: Use gold linker for faster linking

## Troubleshooting

### Common ARM64 Build Issues

#### 1. "relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used when making a shared object"
**Cause**: Static library compiled without `-fPIC`
**Fix**: Ensure `POSITION_INDEPENDENT_CODE TRUE` in CMakeLists.txt

#### 2. "libgpiod function not declared in scope"
**Cause**: Using v1.x API with v2.x library
**Fix**: Update code to use v2.x API (see HardwareControlServer.cpp changes)

#### 3. "ARM aarch64 architecture not detected"
**Cause**: Running on x86_64 emulation
**Fix**: Ensure native ARM64 environment (check with `uname -m`)

#### 4. Out of Memory Errors
**Fix**:
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Build with reduced parallelism
make -j2
```

### Verification Commands

Verify ARM64 build correctness:

```bash
# Check architecture
file hardware-server
# Should show: "ELF 64-bit LSB pie executable, ARM aarch64"

# Verify library dependencies
ldd hardware-server
# Should show ARM64 libraries

# Test basic functionality
./hardware-server --help
```

## CI/CD Integration

### GitHub Actions ARM64 Builds

The project includes ARM64 CI builds using:
- **Native ARM64 runners**: `ubuntu-20.04-arm` (if available)
- **Emulated ARM64**: QEMU-based cross-compilation
- **Architecture validation**: Automatic binary architecture checks

### Build Matrix Configuration

```yaml
strategy:
  matrix:
    include:
      - { runner: ubuntu-latest, arch: x86_64, host_profile: linux-x86_64, build_profile: linux-x86_64 }
      - { runner: ubuntu-20.04, arch: arm64, host_profile: linux-arm64, build_profile: linux-arm64 }
      - { runner: ubuntu-latest, arch: arm64-cross, host_profile: linux-arm64, build_profile: linux-x86_64 }
```

## Performance Optimization

### ARM64-Specific Optimizations

1. **NEON Instructions**: Vector processing for data-intensive operations
2. **Cache Alignment**: 64-byte cache lines on ARM64
3. **Branch Prediction**: Optimize conditional code patterns
4. **Memory Access**: Use aligned memory access patterns

### Benchmarking

Monitor ARM64 performance:

```bash
# Build time measurement
time ./tools/build.sh --profile linux-arm64

# Runtime performance
perf stat ./hardware-server --benchmark
```

## Migration Guide

### From x86_64 Development

1. **Update profiles**: Switch from `linux-release` to `linux-arm64`
2. **Cross-compile first**: Test builds before native ARM64 deployment
3. **Validate binaries**: Always check `file` output for ARM64 architecture
4. **Test on target**: Deploy and test on actual Raspberry Pi hardware

### API Compatibility

- **FlatBuffers**: Architecture-independent serialization
- **ZeroMQ**: Cross-platform messaging
- **MQTT**: Protocol-level compatibility
- **HTTP APIs**: RESTful design works across architectures

## Support and Resources

### Documentation Links
- [Raspberry Pi Setup Guide](RASPBERRY_PI_SETUP.md)
- [Conan Setup Guide](conan-setup.md)
- [CI/CD Setup](ci-cd-setup.md)

### Community Resources
- [Conan Documentation](https://docs.conan.io/)
- [CMake ARM64 Guide](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html)
- [libgpiod Documentation](https://libgpiod.readthedocs.io/)

### Issue Reporting

For ARM64-specific issues:
1. Include `uname -m` output (should be `aarch64`)
2. Provide Conan profile: `conan profile show linux-arm64`
3. Include build logs with verbose output: `make VERBOSE=1`
4. Specify Raspberry Pi model and OS version

---

*Last updated: December 2025 - ARM64 support fully implemented with hardware integration*