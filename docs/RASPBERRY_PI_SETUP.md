# AI-SERVIS Raspberry Pi Setup Guide

This guide covers setting up the AI-SERVIS build environment on Raspberry Pi (and other Debian-based ARM systems) without requiring system-level pip installations.

The setup uses **sparetools-cpython** packages from Cloudsmith for zero-copy Python environment management via Conan.

## Quick Start (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/sparesparrow/ai-servis.git
cd ai-servis

# 2. Install system dependencies (requires sudo)
./tools/install-deps-rpi.sh

# 3. Bootstrap environment (downloads from Cloudsmith)
./tools/bootstrap.sh

# 4. Build
./tools/build.sh
```

## Alternative: Using init.sh

```bash
# 1. Clone the repository
git clone https://github.com/sparesparrow/ai-servis.git
cd ai-servis

# 2. Install system dependencies (requires sudo)
./tools/install-deps-rpi.sh

# 3. Initialize the environment (sets up everything)
./tools/init.sh

# 4. Activate and build
source tools/env.sh
ai-servis-build
```

## Detailed Setup

### Prerequisites

The setup requires:
- Raspberry Pi 3/4/5 or compatible ARM64/ARMv7 device
- Raspberry Pi OS (Bookworm or later) or Debian 12+
- At least 2GB RAM recommended for compilation
- Internet connection for downloading dependencies

### Step 1: Install System Dependencies

Run the dependency installer:

```bash
./tools/install-deps-rpi.sh
```

This installs:
- **Build tools**: cmake, ninja-build, g++
- **Python**: python3, python3-venv, python3-pip
- **Libraries**: libgpiod-dev, libmosquitto-dev, libcurl4-openssl-dev, etc.
- **Runtime**: mosquitto MQTT broker

For a minimal installation (build tools only):

```bash
./tools/install-deps-rpi.sh --minimal
```

### Step 2: Bootstrap Build Environment

The bootstrap script creates a self-contained Python environment with Conan, using the **sparetools** zero-copy approach:

```bash
./tools/bootstrap.sh
```

This:
1. Tries to install `sparetools-cpython/3.12.7` from Conan (Cloudsmith remote)
2. Creates zero-copy symlinks from Conan cache to `.buildenv/`
3. Falls back to system Python with venv if Conan CPython unavailable
4. Installs Conan, CMake, and other build tools
5. Configures Conan profiles for the project

The environment is isolated from system Python, avoiding PEP 668 issues.

### Cloudsmith Remote Integration

The project uses **sparetools-cpython** packages from Cloudsmith for zero-copy Python environments:

- **sparetools-cpython**: Portable CPython 3.12.7 via Conan
- **Zero-copy symlinks**: Saves disk space by linking to Conan cache
- **Cloudsmith remote**: Pre-built packages available at:
  `https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/`

The bootstrap scripts automatically configure the Conan remote. To manually set it up:

```bash
conan remote add sparesparrow-conan \
    https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/
```

### Step 3: Activate Environment (Optional)

For interactive development:

```bash
source tools/env.sh
```

This provides:
- Activated Python virtual environment
- `conan` and `cmake` on PATH
- Helper functions: `ai-servis-build`, `ai-servis-clean`, `ai-servis-info`

### Step 4: Build

Build all components:

```bash
./tools/build.sh
```

Build specific components:

```bash
./tools/build.sh hardware-server
./tools/build.sh mcp-server
```

Clean and rebuild:

```bash
./tools/build.sh --clean
```

Use a specific Conan profile:

```bash
./tools/build.sh --profile linux-arm64
```

## Directory Structure

After setup:

```
ai-servis/
├── .buildenv/              # Build environment (gitignored)
│   ├── venv/               # Python virtual environment
│   ├── conan/              # Conan home directory
│   ├── cache/              # Downloaded files cache
│   └── python/             # Standalone CPython (if used)
├── tools/
│   ├── bootstrap.sh        # Environment setup script
│   ├── build.sh            # Build wrapper
│   ├── env.sh              # Environment activation
│   └── install-deps-rpi.sh # System dependency installer
├── build-Release/          # Build output
└── ...
```

## Troubleshooting

### "externally-managed-environment" Error

This error means you're trying to use `pip install` directly on system Python. Use the bootstrap script instead:

```bash
./tools/bootstrap.sh
```

### CMake Can't Find Libraries

Make sure system dependencies are installed:

```bash
./tools/install-deps-rpi.sh
```

Then rebuild:

```bash
./tools/build.sh --clean
```

### Conan Profile Issues

Reset Conan configuration:

```bash
source tools/env.sh
conan profile detect --force
```

### Out of Memory During Build

Reduce parallel jobs:

```bash
./tools/build.sh --jobs 1
```

Or add swap space:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Updating the Build Environment

To update Conan and other tools:

```bash
./tools/bootstrap.sh --update
```

To completely reinstall:

```bash
./tools/bootstrap.sh --clean
```

## Cross-Compilation

To cross-compile for Raspberry Pi from x86_64:

1. Install the ARM toolchain on your build machine
2. Use the appropriate Conan profile:

```bash
./tools/build.sh --profile linux-arm64
```

## Available Conan Profiles

| Profile | Description |
|---------|-------------|
| `linux-arm64` | Raspberry Pi 4/5 (64-bit) |
| `linux-release` | x86_64 Linux |
| `linux-simulation` | For testing without hardware |

## Built Components

After a successful build:

| Component | Description | Port |
|-----------|-------------|------|
| `hardware-server` | GPIO control server | 8081 |
| `mcp-server` | MCP tools server | 8082 |
| `webgrab-client` | Download client | - |
| `webgrab-server` | Download server | 8083 |

## Running the Services

Start the hardware server:

```bash
./build-Release/hardware-server
```

Start with custom configuration:

```bash
./build-Release/hardware-server --port 8081 --config config.json
```

## Integration with Python Modules

The C++ hardware server communicates with Python modules via MQTT:

```bash
# Start MQTT broker
sudo systemctl start mosquitto

# Start hardware server
./build-Release/hardware-server &

# Run Python orchestrator
source tools/env.sh
pip install -r requirements.txt
python -m modules.core-orchestrator
```

## See Also

- [Main README](../README.md)
- [C++ Platform Documentation](../platforms/cpp/README.md)
- [Architecture Overview](architecture-overview.md)
