# MIA Universal - Quick Start Guide

**Get up and running in 10 minutes!**

## 🎯 What You'll Learn

In this guide, you'll:
1. Install MIA Universal
2. Run your first test
3. Start the core orchestrator
4. Send your first voice command
5. Explore the system

**Time Required**: 10-15 minutes

---

## 📋 Prerequisites

### Required
- **Operating System**: Linux, macOS, or Windows with WSL
- **Python**: 3.11 or higher
- **Git**: Latest version

### Optional (for full features)
- **Docker**: 20.10 or higher
- **Node.js**: 18 or higher (for web UI)
- **Android Studio**: For mobile app development

### Check Your System

```bash
# Check Python version
python3 --version  # Should be 3.11 or higher

# Check Git
git --version

# Optional: Check Docker
docker --version
```

---

## 🚀 Installation

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/sparesparrow/mia.git
cd mia
```

### Step 2: Choose Your Installation Method

#### Option A: Minimal Installation (Recommended for Getting Started)

```bash
# Install minimal dependencies
pip install -r requirements-minimal.txt

# Or just the essentials
pip install pyyaml python-dotenv
```

**What you get**:
- Core orchestrator NLP engine
- Configuration management
- Basic functionality

**What you don't get**:
- Build orchestrator features
- Performance monitoring
- Container management

#### Option B: Full Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# This includes: aiohttp, docker, psutil, and more
```

**What you get**:
- Everything in minimal installation
- Build orchestrator
- Performance monitoring
- Security scanning
- Full feature set

#### Option C: Docker (Easiest for Production)

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check services are running
docker-compose ps
```

---

## ✅ Verify Installation

### Test 1: Simple Orchestrator Test

```bash
# Run the simple test suite
python3 test_orchestrator_simple.py
```

**Expected Output**:
```
🎉 All tests passed! The Core Orchestrator NLP engine is working correctly.

Results: 4 passed, 0 failed
Total time: 0.04s
```

**If tests pass**: ✅ Your installation is working!

### Test 2: Check Configuration

```bash
# Verify configuration is valid
python3 -c "
import yaml
from pathlib import Path

config = yaml.safe_load(open('orchestrator-config.yaml'))
print(f'✅ Configuration loaded: {len(config.get(\"components\", []))} components')
"
```

**Expected Output**:
```
✅ Configuration loaded: 7 components
```

---

## 🎮 Your First Commands

### Start the Core Orchestrator

#### Method 1: Simple Python Script

Create a file called `test_commands.py`:

```python
#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('.')

# Import from test file
from test_orchestrator_simple import SimpleNLPProcessor

async def main():
    # Create NLP processor
    nlp = SimpleNLPProcessor()
    
    # Test commands
    commands = [
        "Play jazz music by Miles Davis",
        "Set volume to 75",
        "Turn on GPIO pin 18",
        "Switch to headphones"
    ]
    
    print("🎤 Testing Voice Commands\n")
    
    for cmd in commands:
        result = await nlp.parse_command(cmd)
        print(f"Command: '{cmd}'")
        print(f"  Intent: {result.intent}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Parameters: {result.parameters}\n")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python3 test_commands.py
```

**Expected Output**:
```
🎤 Testing Voice Commands

Command: 'Play jazz music by Miles Davis'
  Intent: play_music
  Confidence: 0.39
  Parameters: {'artist': 'miles davis', 'genre': 'jazz'}

Command: 'Set volume to 75'
  Intent: control_volume
  Confidence: 0.26
  Parameters: {'level': '75'}
...
```

### Try Different Commands

Edit `test_commands.py` and try your own commands:

```python
commands = [
    "Play rock music",
    "Make it louder",
    "Open Firefox browser",
    "Turn on living room lights",
    "Read sensor on pin 21"
]
```

---

## 🏗️ Explore the Architecture

### View Project Structure

```bash
# See all modules
ls -la modules/

# See platform components
ls -la platforms/

# View configuration
cat orchestrator-config.yaml

# Check documentation
ls -la docs/
```

### Key Directories

```
ai-servis/
├── modules/              # Python modules (MCP servers)
│   ├── core-orchestrator/
│   ├── ai-audio-assistant/
│   ├── ai-communications/
│   └── ...
├── platforms/            # Platform-specific code
│   ├── cpp/             # C++ components
│   └── ...
├── docs/                # Documentation
├── tests/               # Test suites
└── .github/workflows/   # CI/CD pipelines
```

---

## 📚 Next Steps

### Learn More

1. **Read the Architecture** → [`docs/architecture/overview.md`](../architecture/overview.md)
2. **Explore Modules** → [`docs/modules/`](../modules/)
3. **Check API Docs** → [`docs/api/`](../api/)
4. **Setup Development** → [`../DEVELOPMENT.md`](../../DEVELOPMENT.md)

### Try Advanced Features

#### 1. Run with Docker

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Check logs
docker-compose logs -f core-orchestrator

# Stop services
docker-compose down
```

#### 2. Build C++ Components

```bash
# Install Conan
pip install conan

# Build hardware server
./scripts/build-hardware-server.sh

# Or manually
cd platforms/cpp
conan install .. --build missing
cmake -S . -B build
cmake --build build
```

#### 3. Run Android App

```bash
# Navigate to Android directory
cd android

# Build debug APK
./gradlew assembleDebug

# Install on device
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Customize Configuration

Edit `orchestrator-config.yaml` to customize:

```yaml
# Add your own component
components:
  - name: my-custom-module
    path: ./modules/my-custom-module
    dependencies: []
    deploy:
      type: docker
      ports:
        - "8090:8090"
```

---

## 🐛 Troubleshooting

### Common Issues

#### Issue 1: Module Not Found

**Error**: `ModuleNotFoundError: No module named 'xyz'`

**Solution**:
```bash
# Install missing dependencies
pip install aiohttp docker psutil

# Or install full requirements
pip install -r requirements.txt
```

#### Issue 2: Configuration Error

**Error**: `Configuration file not found`

**Solution**:
```bash
# Make sure you're in the project root
cd /path/to/ai-servis

# Verify file exists
ls orchestrator-config.yaml
```

#### Issue 3: Import Errors

**Error**: `ImportError: attempted relative import with no known parent package`

**Solution**:
```bash
# Run from project root
cd /path/to/ai-servis

# Use python3 -m
python3 -m test_orchestrator_simple
```

#### Issue 4: Permission Denied

**Error**: `Permission denied: '/some/path'`

**Solution**:
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Or run with python
python3 script_name.py
```

### Getting Help

- **Documentation**: [`docs/`](../)
- **Troubleshooting Guide**: [`docs/troubleshooting.md`](../troubleshooting.md)
- **GitHub Issues**: [Create an issue](https://github.com/sparesparrow/mia/issues)
- **Discord**: [MIA Community](https://discord.gg/mia)

---

## 🎓 Learning Path

### Beginner

1. ✅ **Complete this Quick Start** ← You are here
2. 📖 Read [Architecture Overview](../architecture/overview.md)
3. 🧪 Run more tests: `python3 test_orchestrator.py`
4. 📝 Read [Module Documentation](../modules/)

### Intermediate

1. 🏗️ Explore module code in `modules/`
2. 🔧 Build C++ components
3. 🐳 Deploy with Docker
4. 🧩 Create a custom module

### Advanced

1. 🚀 Set up CI/CD pipeline
2. 📱 Build Android app
3. 🔌 Work with ESP32 firmware
4. 🌐 Deploy to production

---

## 📊 Quick Reference

### Useful Commands

```bash
# Run tests
python3 test_orchestrator_simple.py
python3 test_orchestrator.py

# Check configuration
python3 build_orchestrator.py orchestrator-config.yaml --help

# View logs (Docker)
docker-compose logs -f [service-name]

# Build C++ components
./scripts/build-hardware-server.sh

# Format code
black .
isort .

# Lint code
flake8 .
mypy .
```

### Important Files

| File | Purpose |
|------|---------|
| `orchestrator-config.yaml` | Main configuration |
| `requirements.txt` | Python dependencies |
| `requirements-minimal.txt` | Minimal dependencies |
| `docker-compose.yml` | Docker services |
| `test_orchestrator_simple.py` | Simple test suite |
| `build_orchestrator.py` | Build automation |

### Key Ports

| Port | Service |
|------|---------|
| 8080 | Core Orchestrator |
| 8081 | Audio Assistant |
| 8082 | Security Module |
| 5555 | Hardware Server |
| 1883 | MQTT Broker |
| 9090 | Prometheus |
| 3000 | Grafana |

---

## 🎉 Congratulations!

You've successfully:
- ✅ Installed MIA Universal
- ✅ Ran your first tests
- ✅ Tested voice commands
- ✅ Explored the architecture
- ✅ Learned the basics

### What's Next?

Choose your path:

**For Developers**:
→ Start with [Module Development](../modules/README.md)

**For DevOps**:
→ Continue to [Deployment Guide](../deployment/README.md)

**For Researchers**:
→ Explore [Architecture Deep Dive](../architecture/overview.md)

**For Contributors**:
→ Read [Contributing Guide](../../CONTRIBUTING.md) (coming soon)

---

## 🔗 Quick Links

- **Main README**: [README.md](../../README.md)
- **Architecture**: [docs/architecture/](../architecture/)
- **API Docs**: [docs/api/](../api/)
- **Modules**: [docs/modules/](../modules/)
- **Troubleshooting**: [docs/troubleshooting.md](../troubleshooting.md)
- **GitHub**: [github.com/sparesparrow/mia](https://github.com/sparesparrow/mia)

---

**Happy Coding! 🚀**

*Last Updated: October 1, 2025*
