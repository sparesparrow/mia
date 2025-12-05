# MIA Universal Development Guide

## Quick Start

1. Clone the repository
2. Run the setup script: `./scripts/dev-setup.sh`
3. Copy `.env.example` to `.env` and update configuration
4. Start development environment: `docker-compose -f docker-compose.dev.yml up`

## Architecture

The system follows a modular MCP (Model Context Protocol) architecture:

- **Core Orchestrator**: Main MCP host that routes commands
- **Audio Assistant**: Handles voice processing and music playback
- **Platform Controllers**: System-specific integrations
- **Service Discovery**: Automatic service registration and health checking

## Development Workflow

1. Create feature branch
2. Implement changes with tests
3. Run tests: `pytest tests/`
4. Check code quality: `black . && flake8 .`
5. Submit pull request

## Testing

- Unit tests: `pytest tests/unit/`
- Integration tests: `pytest tests/integration/`
- System tests: `./scripts/system-tests.sh`

## Docker Development

All services run in containers for consistent development experience:

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# View logs
docker-compose logs -f ai-servis-core

# Run tests in container
docker-compose exec ai-servis-core pytest tests/
```
