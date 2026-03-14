# MIA Multi-Agent Orchestration System

## Overview

This directory contains the MIA multi-agent orchestration configuration for Claude Code. The system uses a **cost-optimized architecture** with a Sonnet 4.5 orchestrator coordinating 10 Haiku 3.5 specialist subagents across Android, Raspberry Pi, and ESP32 platforms.

**Cost Savings**: 85% reduction compared to all-Sonnet approach (~$1-2 per full system build vs $7-8)

## Quick Start

### Basic Usage

From the MIA project root directory:

```bash
cd /home/sparrow/projects/mia
claude --agents .claude/agents.json "your task here"
```

### Example Commands

**Build ESP32 firmware and start serial monitor:**
```bash
claude --agents .claude/agents.json "build ESP32 firmware and start serial monitor"
```

**Full system build and deploy:**
```bash
claude --agents .claude/agents.json "build and deploy entire MIA system"
```

**Add new feature across platforms:**
```bash
claude --agents .claude/agents.json "add voice command to control bedroom LED brightness"
```

**Fix and test:**
```bash
claude --agents .claude/agents.json "fix ESP32 WiFi reconnection bug and run integration tests"
```

**Non-interactive mode** (for scripts):
```bash
claude --agents .claude/agents.json -p "run integration tests"
```

## Architecture

### Orchestrator (Sonnet 4.5)

The `mia-orchestrator` is your high-level coordinator that:
- Analyzes tasks and identifies platforms affected
- Queries mcp-prompts for domain knowledge
- Automatically activates appropriate specialist agents
- Coordinates parallel/sequential execution
- Aggregates results from all specialists

**Cost**: ~10% of tokens (~$0.75 per major workflow)

### Specialists (ALL Haiku 3.5)

10 domain-specific agents handle focused work:

1. **kotlin-android-dev**: Android app, Gradle, voice UI, MQTT/HTTP
2. **cpp-rpi-dev**: RPi C++20, CMake, audio processing, hardware
3. **python-rpi-dev**: RPi Python, FastAPI, MQTT broker, systemd
4. **conan-pkg-manager**: Conan 2.0, Cloudsmith, cross-compilation
5. **multiplatform-builder**: Gradle/CMake/PlatformIO builds
6. **iot-deployer**: SSH, Docker Compose, systemd, ADB deployment
7. **integration-tester**: pytest, Android tests, MQTT validation
8. **test-validator**: Test analysis, coverage, quality gates
9. **platformio-esp32**: ESP32 firmware, serial debugging, FreeRTOS
10. **android-tester**: ADB automation, scrcpy, logcat analysis

**Cost**: ~90% of tokens (~$0.35 per major workflow)

## Common Workflows

### 1. ESP32 Firmware Development

**Scenario**: Update ESP32 firmware and test

```bash
claude --agents .claude/agents.json "update ESP32 LED control firmware and test with serial monitor"
```

**What happens**:
1. Orchestrator identifies ESP32 work
2. Queries mcp-prompts for ESP32 debugging patterns
3. Activates `platformio-esp32` specialist
4. Specialist builds firmware, uses `esp32_serial_monitor_start`
5. Reports results with serial logs

**Cost**: ~$0.30

### 2. Android App Feature

**Scenario**: Add voice command UI

```bash
claude --agents .claude/agents.json "add voice command for temperature sensor display"
```

**What happens**:
1. Orchestrator queries voice UI patterns from mcp-prompts
2. Activates `kotlin-android-dev` specialist
3. Specialist implements Compose UI, MQTT subscriber
4. Builds APK and runs tests
5. Reports completion with APK path

**Cost**: ~$0.40

### 3. Cross-Platform Feature

**Scenario**: Add feature spanning all platforms

```bash
claude --agents .claude/agents.json "add voice command to control bedroom LED brightness"
```

**What happens**:
1. Orchestrator analyzes cross-platform impact
2. Defines shared MQTT protocol
3. Activates **in parallel**:
   - `kotlin-android-dev`: Voice UI + MQTT publish
   - `python-rpi-dev`: MQTT routing logic
   - `platformio-esp32`: LED PWM control
4. Activates `integration-tester`: End-to-end validation
5. Reports feature completion

**Cost**: ~$0.80

### 4. Full System Build & Deploy

**Scenario**: Build everything and deploy to devices

```bash
claude --agents .claude/agents.json "build and deploy entire MIA system"
```

**What happens**:
1. Orchestrator queries build order knowledge
2. Activates `conan-pkg-manager`: Parallel package creation (Android ARM64 || RPi ARMv8 || ESP32)
3. Activates `multiplatform-builder`: Parallel builds (Android || RPi || ESP32)
4. Activates `iot-deployer`: Sequential deployment (ESP32 → RPi → Android)
5. Activates `integration-tester`: End-to-end tests
6. Activates `test-validator`: Quality gates
7. Reports complete status

**Cost**: ~$1.50

### 5. Test & Validate

**Scenario**: Run integration tests

```bash
claude --agents .claude/agents.json "run integration tests and enforce quality gates"
```

**What happens**:
1. Activates `integration-tester`: Executes pytest and Android tests
2. Monitors ESP32 serial and Android logcat
3. Activates `test-validator`: Analyzes results
4. Enforces quality gates (100% pass rate, >85% coverage)
5. Reports APPROVE or REJECT decision

**Cost**: ~$0.50

## Agent Responsibilities

### kotlin-android-dev
**When activated**: Android work needed
**Tools**: android_device_list, android_install_apk, android_logcat_start
**Scope**: /android/** directory
**Specialization**: Kotlin, Jetpack Compose, MQTT client, voice UI

### cpp-rpi-dev
**When activated**: RPi C++ services needed
**Tools**: Read, Write, Edit, Bash
**Scope**: /platforms/cpp/** directory
**Specialization**: C++20, CMake, audio FFT, libgpiod

### python-rpi-dev
**When activated**: RPi Python services needed
**Tools**: Read, Write, Edit, Bash
**Scope**: /rpi/**, /modules/** directories
**Specialization**: FastAPI, MQTT broker, systemd, pytest

### conan-pkg-manager
**When activated**: Dependency updates or cross-compilation needed
**Tools**: conan_create_package, conan_search_packages
**Scope**: conanfile.py files
**Specialization**: Conan 2.0, Cloudsmith publishing

### multiplatform-builder
**When activated**: Build orchestration needed
**Tools**: Bash (Gradle/CMake/PlatformIO)
**Scope**: All build systems
**Specialization**: Parallel builds, CI/CD

### iot-deployer
**When activated**: Deployment needed
**Tools**: unified_deploy, esp32_*, android_*
**Scope**: Deployment scripts, systemd services
**Specialization**: SSH, Docker, ADB, serial upload

### integration-tester
**When activated**: Testing needed
**Tools**: android_logcat_start, esp32_serial_monitor_start
**Scope**: /tests/** directory
**Specialization**: pytest, Android instrumented tests

### test-validator
**When activated**: Test analysis needed
**Tools**: Read (test reports)
**Scope**: Test output files
**Specialization**: Coverage analysis, quality gates

### platformio-esp32
**When activated**: ESP32 firmware work needed
**Tools**: esp32_serial_monitor_start/stop
**Scope**: /esp32/** directory (or platform-specific)
**Specialization**: FreeRTOS, WiFi, MQTT, FFT optimization

### android-tester
**When activated**: Android device testing needed
**Tools**: android_*, ADB shell commands
**Scope**: Android devices
**Specialization**: ADB automation, scrcpy, UI testing

## MCP Server Integration

### unified-dev-tools

The agents use `unified-dev-tools` MCP server for:
- **ESP32 tools**: esp32_serial_monitor_start/stop
- **Android tools**: android_device_list, android_install_apk, android_logcat_start
- **Conan tools**: conan_create_package, conan_search_packages
- **Deployment**: unified_deploy

**Configuration** (in Claude Desktop MCP settings):
```json
{
  "unified-dev-tools": {
    "command": "uv",
    "args": ["run", "--project", "/home/sparrow/mcp/servers/python/unified_dev_tools", "python", "unified_dev_tools_mcp_server.py"]
  }
}
```

### mcp-prompts

The orchestrator queries `mcp-prompts` for domain knowledge:
- ESP32 optimization guides (esp32-fft-configuration-guide)
- Voice UI patterns (voice-command-design-principles)
- Debugging workflows (esp32-platformio-serial-upload-debugging)

**Configuration**:
```json
{
  "mcp-prompts": {
    "command": "node",
    "args": ["/home/sparrow/projects/mcp/ai-mcp-monorepo/packages/mcp-prompts/dist/mcp-server-standalone.js"],
    "env": {"MODE": "mcp", "STORAGE_TYPE": "file"}
  }
}
```

## Cost Expectations

### Per-Workflow Estimates

| Workflow | Tokens | Cost | Time |
|----------|--------|------|------|
| ESP32 firmware update | ~100K | ~$0.30 | 3-5 min |
| Android feature add | ~120K | ~$0.40 | 5-7 min |
| RPi service update | ~80K | ~$0.25 | 3-5 min |
| Cross-platform feature | ~250K | ~$0.80 | 8-12 min |
| Full system build | ~500K | ~$1.50 | 15-20 min |
| Integration tests | ~150K | ~$0.50 | 5-8 min |

### Cost Breakdown

**Orchestrator (Sonnet 4.5)**: $15 per 1M tokens
- Task analysis, knowledge queries, coordination
- ~10% of total tokens
- High reasoning quality for complex decisions

**Specialists (Haiku 3.5)**: $0.80 per 1M tokens
- Focused domain work
- ~90% of total tokens
- Excellent quality for well-defined tasks

**Comparison**:
- All Sonnet: $7.50 per 500K tokens
- Sonnet + Haiku: $1.13 per 500K tokens
- **Savings**: 85%

## Quality Gates

The `test-validator` agent enforces these gates before deployment:

✅ **Test Pass Rate**: 100% required (0 failures)
✅ **Code Coverage**: >85% for core modules
✅ **Build Success**: All platforms (Android, RPi, ESP32)
✅ **Performance**: No critical regressions
✅ **Integration**: Cross-platform tests pass

**If gates fail**, the validator provides:
- Specific failures with diagnostics
- Coverage gaps to address
- Performance regression analysis
- Recommendations for fixes

## Troubleshooting

### Agent Not Activating

**Problem**: Orchestrator doesn't activate the right specialist

**Solution**: Be specific in your request
```bash
# Too vague
claude --agents .claude/agents.json "fix the app"

# Better
claude --agents .claude/agents.json "fix Android MQTT reconnection in kotlin code"
```

### Tool Access Denied

**Problem**: Specialist can't access needed tool

**Solution**: Check that the tool is in the specialist's `mcp_servers` list in `agents.json`. The orchestrator has full access; specialists have scoped access.

### Build Failures

**Problem**: Builds fail in multiplatform-builder

**Solution**:
1. Check Conan packages are published (conan-pkg-manager first)
2. Verify build tools installed (Gradle, CMake, PlatformIO)
3. Check disk space and permissions

### Serial Monitor Not Working

**Problem**: esp32_serial_monitor_start fails

**Solution**:
1. Check port: `ls /dev/ttyUSB* /dev/ttyACM*`
2. Verify permissions: `sudo usermod -a -G dialout $USER`
3. Disconnect other serial tools (Arduino IDE, etc)

### Cost Higher Than Expected

**Problem**: Workflow costs more than estimates

**Solution**:
1. Check if multiple specialists activated unnecessarily
2. Simplify task description to reduce orchestrator analysis
3. Break large tasks into smaller focused tasks

## Advanced Usage

### Custom Model Override

Use Sonnet for all agents (higher quality, higher cost):
```bash
claude --agents .claude/agents.json --model sonnet "complex refactoring task"
```

### Append System Prompt

Add extra context for all agents:
```bash
claude --agents .claude/agents.json \
  --append-system-prompt "Focus on performance optimization" \
  "optimize ESP32 FFT processing"
```

### Non-Interactive Mode

For CI/CD integration:
```bash
claude --agents .claude/agents.json -p "run integration tests" > test-results.txt
```

### Debug Mode

See detailed agent activation:
```bash
claude --agents .claude/agents.json --debug "build system"
```

## File Structure

```
/home/sparrow/projects/mia/.claude/
├── agents.json          # Agent configurations (this file defines all agents)
└── README.md            # This documentation
```

## Updating Agents

To modify agent behavior, edit `agents.json`:

1. **Change orchestrator prompt**: Edit `mia-orchestrator.prompt`
2. **Add specialist expertise**: Edit `{specialist}.prompt`
3. **Adjust tool access**: Edit `{specialist}.mcp_servers`
4. **Change model**: Edit `{specialist}.model` (sonnet/haiku)

**After changes**: Test with a simple task to validate

## Support

For issues or questions:
- Check orchestrator logic in `agents.json` → `mia-orchestrator.prompt`
- Review specialist prompts for domain-specific behavior
- Consult plan file: `/home/sparrow/.claude/plans/harmonic-doodling-pine.md`
- Ask Claude Code directly: "Explain how the MIA agents work"

## Examples by Use Case

### Debugging ESP32 Issue
```bash
claude --agents .claude/agents.json "debug ESP32 WiFi disconnection issue with serial monitor"
```

### Android UI Update
```bash
claude --agents .claude/agents.json "update Android voice command UI to use Material Design 3"
```

### RPi Service Enhancement
```bash
claude --agents .claude/agents.json "add new MQTT topic handler in Python RPi service"
```

### Package Management
```bash
claude --agents .claude/agents.json "update Conan packages for all platforms to sparetools-base 2.0.4"
```

### Performance Optimization
```bash
claude --agents .claude/agents.json "optimize ESP32 FFT processing using mcp-prompts knowledge"
```

### Full Cycle
```bash
# 1. Build
claude --agents .claude/agents.json "build all platforms"

# 2. Deploy
claude --agents .claude/agents.json "deploy to all devices"

# 3. Test
claude --agents .claude/agents.json "run integration tests"

# Or all at once
claude --agents .claude/agents.json "build, deploy, and test complete system"
```

---

**Built with**: Claude Code multi-agent orchestration
**Architecture**: Sonnet orchestrator + Haiku specialists
**Cost**: 85% savings through strategic model selection
