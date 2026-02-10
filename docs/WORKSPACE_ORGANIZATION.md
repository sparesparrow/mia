# Workspace Organization

This document describes the workspace organization and directory structure for the MIA project.

## Directory Structure

### Development Environment (`~/projects/mia/`)

The development repository contains the complete source code, documentation, and build tools:

```
~/projects/mia/
├── config/
│   └── paths.json          # Configurable path definitions
├── core/
│   └── paths.py            # Python path resolution utilities
├── docs/                   # Documentation
├── scripts/                # Build and deployment scripts
├── platforms/              # Platform-specific implementations
├── modules/                # Python modules
├── services/               # Systemd service definitions
├── rpi/                    # Raspberry Pi specific code
├── hardware/               # Hardware interfaces
├── arduino/                # Arduino sketches and tools
└── android/                # Android application
```

### Installation Environment (`/opt/mia/`)

The installation directory contains the deployed code for production use:

```
/opt/mia/
├── config/                 # Configuration files
├── core/                   # Core Python modules
├── rpi/                    # Raspberry Pi implementation
├── modules/                # Hardware and service modules
├── services/               # Runtime services
├── agents/                 # AI and automation agents
└── arduino/                # Arduino support files
```

### System Integration

System-wide components are installed in standard Linux locations:

```
/etc/systemd/system/
├── mia-broker.service
├── mia-api.service
├── mia-gpio-worker.service
├── mia-obd-worker.service
└── mia-citroen-bridge.service

/etc/mia/
└── config/                 # System configuration

/var/lib/mia/
├── logs/                   # Application logs
└── data/                   # Persistent data

/var/log/mia/               # System logs
```

## Path Configuration

### Configurable Paths (`config/paths.json`)

```json
{
  "project_root": ".",
  "install_prefix": "/opt/mia",
  "rpi_deploy_path": "/home/mia/mia-install"
}
```

### Path Resolution (`core/paths.py`)

The `PathConfig` class provides utilities for resolving paths across different environments:

```python
from core.paths import PathConfig

config = PathConfig()
project_root = config.get_path('project_root')
install_path = config.resolve_path('/opt/mia')
```

## Development Workflow

### Local Development
1. Clone repository to `~/projects/mia/`
2. Create symlink: `sudo ln -sf ~/projects/mia /opt/mia`
3. Use relative paths in code for environment independence
4. Run services with development paths

### Deployment
1. Copy code to `/opt/mia/` (or create symlink for development)
2. Install systemd services
3. Configure system paths in `/etc/mia/`
4. Enable and start services

### Testing
1. Use relative paths in test files
2. Configure test environments with path overrides
3. Validate path resolution across different environments

## Environment Variables

Services use environment variables for configuration:

- `PYTHONPATH`: Python module search path
- `WORKING_DIRECTORY`: Service working directory
- `RPI_PATH`: Deployment path (defaults to `/opt/mia`)

## Migration Notes

This workspace organization replaces the previous structure where development and installation used the same paths. Key changes:

- **Before**: Code in `~/ai-servis/` used for both development and deployment
- **After**: Development in `~/projects/mia/`, deployment to `/opt/mia/`

### Benefits
- Clean separation of development and production environments
- Environment-independent code using relative paths
- Proper system integration with standard Linux directories
- Simplified deployment and rollback procedures

### Migration Steps
1. Consolidate repositories (see consolidation plan)
2. Update hardcoded paths to use configurable paths
3. Create symlink for development environment
4. Update documentation and deployment scripts
5. Test in both development and deployment scenarios