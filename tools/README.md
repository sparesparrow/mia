# MIA Tools & Development Scripts

Developer-focused utilities and helper scripts for building, testing, and deploying MIA.

## Directory Structure

### `tools/ci/`

Continuous Integration and build validation utilities.

- **`legacy/github-actions/`** - Archive of previous GitHub Actions workflows (now consolidated in `.github/workflows/`)

### `tools/local-dev/`

Local development scripts for rapid iteration.

- **`build-all.sh`** - Build all platforms (Android, ESP32, RPi C++, Python)
- **`start-car-assistant.sh`** - Launch the car assistant stack locally
- **`deploy-car-assistant.sh`** - Deploy assistant to RPi

## Common Tasks

### Build All Platforms
```bash
./tools/local-dev/build-all.sh
```

### Start Development Stack
```bash
./tools/local-dev/start-car-assistant.sh
```

### Run Tests
```bash
pytest tests/ -m "not hardware"                  # Skip hardware tests
pytest tests/unit/                               # Unit tests only
pytest tests/integration/scenarios/              # Integration scenarios
```

### Format & Lint Code
```bash
black . && isort . --profile black && flake8 .
```

## Contributing

When adding new development scripts:
1. Place in `tools/local-dev/` for local-only scripts
2. Place in `tools/ci/` for build/validation scripts
3. Ensure scripts are portable (handle both Linux and macOS)
4. Add description here when done
