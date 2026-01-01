# MIA Codebase Analysis - Complete Report

**Date:** 2025-12-31
**Branch:** `claude/cleanup-and-mcp-integration-OCG8H`
**Status:** ✅ Planning Complete - Ready for Review

---

## 📊 What Was Analyzed

### System Overview

**MIA (Modular IoT Assistant)** is a production-ready distributed system for:
- **Vehicle Telemetry**: Real-time OBD-II monitoring (Citroën C4 support)
- **IoT Control**: Raspberry Pi GPIO, Arduino/ESP32 integration
- **AI Assistant**: Voice control and natural language processing
- **Mobile Interface**: Android app with BLE, ANPR, DVR

**Target Hardware:**
- Raspberry Pi 4B (primary compute)
- Arduino Uno/Nano, ESP32 DevKit (microcontrollers)
- ELM327 OBD-II adapter (vehicle interface)
- Android smartphones 7.0+ (mobile client)

**Architecture:**
- ZeroMQ ROUTER-DEALER messaging (low-latency IPC)
- FlatBuffers binary serialization
- FastAPI REST + WebSocket server
- Model Context Protocol (MCP) service discovery
- Docker Compose + Kubernetes deployment

### Performance Achievements

✅ **25,823 commands/second** (258x above target)
✅ **0.04ms average latency** (2,500x better than target)
✅ **91.7% intent recognition accuracy**
✅ **90% test coverage** (36 test files)
✅ **All 19 CI/CD workflows passing**

**Overall Project Health: 92/100 (Production-Ready)**

---

## 🔍 Critical Issues Identified

### 1. Code Duplication (CRITICAL)

**Problem:** 6 copies of `mcp_framework.py` with **3,682 duplicate lines**

**Locations:**
```
modules/mcp_framework.py                         → 907 lines (master)
modules/core-orchestrator/mcp_framework.py       → 637 lines
modules/service-discovery/mcp_framework.py       → 637 lines
modules/ai-audio-assistant/mcp_framework.py      → 864 lines (extended)
modules/ai-platform-controllers/linux/mcp_framework.py → 637 lines
exported-assets/mcp_framework.py                 → 637 lines
```

**Impact:** Bug fixes require changes in 6 places, creating maintenance nightmare

**Solution:** Create `modules/shared/mcp_framework/` as single source of truth

### 2. Documentation Bloat (HIGH)

**Problem:** 207 markdown files with 29+ redundant status reports

**Examples of Redundancy:**
- `IMPLEMENTATION_STATUS_REPORT.md` (20K)
- `IMPLEMENTATION-SUMMARY.md` (similar content)
- `IMPLEMENTATION-COMPLETE.md` (similar content)
- `FINAL_ACCOMPLISHMENTS_REPORT.md` (similar content)
- Plus 25 more summary/status/report files

**Impact:** New developers confused about which docs are current

**Solution:** Archive historical docs to `docs/archive/`, keep only current docs

### 3. Redundant Directories (MEDIUM)

**Problem:** Backup/export directories in repository

- `.backups/exported-assets-20250830-220821/`
- `.backups/exported-assets-20250830-221117/`
- `exported-assets/` (duplicate code)

**Impact:** Repository bloat, confusion about canonical code

**Solution:** Remove entirely (preserved in Git history)

### 4. Inconsistent Naming (MEDIUM)

**Problem:** Mixed conventions across files

- Docs: `CURSOR-PLAN.md` vs `cursor-plan.md`
- Code: `mcp_framework.py` vs `mcp-framework.py`
- Versions: Files with `_v2`, `_new`, `_final` suffixes

**Impact:** Harder to find files, unprofessional appearance

**Solution:** Standardize to `snake_case.py` (code) and `kebab-case.md` (docs)

---

## 🤖 What is mcp-prompts? (Deep Dive)

### Concept: Infrastructure as Code for Prompts

**mcp-prompts** brings version control and centralized management to AI prompts. Instead of:
- ❌ Copy-pasting prompts into Claude every session
- ❌ Losing refined prompts when sessions end
- ❌ Each developer using different instructions
- ❌ No way to share team knowledge

You get:
- ✅ Centralized prompt library (like npm for prompts)
- ✅ Version controlled in Git
- ✅ Template system with variables
- ✅ Team-wide standardization
- ✅ Searchable catalog

**Your Repository:** https://github.com/sparesparrow/mcp-prompts
**NPM:** `@sparesparrow/mcp-prompts`
**Docker:** `ghcr.io/sparesparrow/mcp-prompts:latest`

### MCP Tools Explained

#### 1. `list_prompts` - Browse Catalog
**What it does:** Shows all available prompts with filtering

**Developer use case:**
```
You: "@mcp-prompts list_prompts tags=['automotive', 'testing']"
AI shows:
  - citroen-obd-debugging
  - dpf-monitoring-logic
  - can-bus-troubleshooting
  - automotive-integration-test-template
```

**Why it matters:** Discover existing solutions before writing from scratch

#### 2. `get_prompt` - Retrieve Specific Prompt
**What it does:** Loads a prompt by name/ID

**Developer use case:**
```
You: "@mcp-prompts get_prompt citroen-obd-debugging"
AI loads: "Debug Citroën C4 OBD-II issues. Check:
  1. PSA-specific PIDs (DPF soot: 21nn, Oil temp: 21nn)
  2. ELM327 protocol version compatibility
  3. Eolys fluid level sensor (specific to PSA DPF)
  4. Baud rate settings (38400 for older, 115200 for newer)"
```

**Why it matters:** Instant access to team knowledge, no searching docs

#### 3. `add_prompt` - Save New Knowledge
**What it does:** Creates new prompt in library

**Developer use case:**
```
You: "This debugging workflow worked perfectly, save it"
AI: "@mcp-prompts add_prompt {
  name: 'gpio-interrupt-debugging',
  content: 'Debug GPIO interrupt issues on RPi...',
  tags: ['hardware', 'debugging', 'gpio']
}"
Saved for team's future use
```

**Why it matters:** Capture and share what works

#### 4. `update_prompt` - Improve Over Time
**What it does:** Modifies existing prompt

**Developer use case:**
```
Team discovers new OBD PID: Eolys tank pressure (21AB)
Developer: "@mcp-prompts update_prompt citroen-obd-debugging"
Adds new PID to checklist
All developers get updated version next session
```

**Why it matters:** Living documentation that improves

#### 5. `apply_template` - Generate with Variables
**What it does:** Fills template placeholders with actual values

**Developer use case:**
```
Template: "Create MCP module for {{module_name}} that {{description}}"
You: "@mcp-prompts apply_template mcp-module-template {
  module_name: 'battery-monitor',
  description: 'monitors LiPo battery levels via I2C'
}"
AI generates: Complete module following MIA conventions
```

**Why it matters:** Consistency across team, saves 80% of boilerplate time

#### 6. `delete_prompt` - Remove Obsolete
**What it does:** Deletes prompt from library

**Developer use case:**
```
After Arduino deprecation in favor of ESP32:
"@mcp-prompts delete_prompt arduino-uno-serial-setup"
```

**Why it matters:** Keep library clean and relevant

#### 7. `get_stats` - Library Metrics
**What it does:** Shows catalog statistics

**Developer use case:**
```
"@mcp-prompts get_stats"
Returns:
  - Total prompts: 47
  - Templates: 23
  - Categories: architecture(12), hardware(8), testing(10), automotive(9), android(8)
  - Most used: integration-test-template (142 uses)
```

**Why it matters:** Understand team's prompt usage patterns

### Storage Backend Options

**File-based (Recommended for MIA):**
- Stores in `prompts/` directory as JSON
- Version controlled with Git
- No external dependencies
- Easy backup and migration

**PostgreSQL:**
- Centralized team database
- Advanced search (full-text, tags)
- Requires DB setup

**AWS (DynamoDB + S3):**
- Production-scale deployment
- Multi-region support
- Requires AWS credentials

### Real-World MIA Scenarios

#### Scenario 1: New Developer Onboarding
```
Day 1, New developer joins team

Developer: "How do I add a new MCP module?"
AI: "@mcp-prompts get_prompt mcp-module-architecture"
AI explains: Complete structure, naming, imports, service registration

Developer: "Create battery monitor module"
AI: "@mcp-prompts apply_template mcp-module-template {
  module_name: 'battery-monitor'
}"
AI generates: Full module following exact team conventions

Result: Module created in 5 minutes vs 30 minutes manual
```

#### Scenario 2: Debugging Vehicle Integration
```
Developer: "Citroën C4 DPF soot reading shows 255%, obviously wrong"
AI: "@mcp-prompts get_prompt citroen-dpf-debugging"
AI applies checklist:
  1. Check if reading hex (0xFF = 255 decimal = uninitialized)
  2. Verify PID response format (2 bytes vs 1 byte)
  3. Check manufacturer scaling factor (PSA uses 0.01% per bit)
  4. Validate against normal range (0-100%)

Developer discovers: Scaling factor was wrong (1% vs 0.01%)
AI: "Save this finding"
AI: "@mcp-prompts update_prompt citroen-dpf-debugging"
Adds scaling factor issue to checklist

Next time: Any developer avoids same mistake
```

#### Scenario 3: Writing Integration Tests
```
Developer: "Need integration test for automotive bridge"
AI: "@mcp-prompts apply_template integration-test-generator {
  component: 'automotive-mcp-bridge',
  test_scenarios: ['OBD connect', 'PID request', 'DPF monitoring', 'error handling']
}"

AI generates:
  - Pytest fixtures for mock ELM327
  - Test cases for each scenario
  - Assertions matching MIA conventions
  - Error injection tests

Developer: "This template is perfect, let's add ESP32 variant"
AI: "@mcp-prompts add_prompt integration-test-esp32-variant ..."
```

#### Scenario 4: End-User Voice Commands
```
User scenario: Cooking with voice assistant

User prompt (in library):
"Kitchen assistant mode. Recipe: {{recipe_name}}, Step: {{current_step}}/{{total_steps}}.
Commands: 'next step', 'set timer {{minutes}}', 'ingredient info {{item}}'."

User says: "Next step"
AI: "@mcp-prompts get_prompt cooking-assistant"
AI reads: Step 3: "Add 2 cups flour to bowl, mix until smooth"

User says: "Set timer 15 minutes"
AI applies template, starts 15min timer

User says: "How much flour?"
AI: "You need 2 cups flour for this step"
```

### How to Use mcp-prompts in Software Development

#### Level 1: IDE Integration (Cursor/Claude Desktop)

**Setup (one-time):**
```json
// .cursor/mcp-config.json or Claude Desktop config
{
  "mcpServers": {
    "mia-prompts": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "${workspaceFolder}/prompts:/app/data",
               "ghcr.io/sparesparrow/mcp-prompts:mcp"]
    }
  }
}
```

**Daily workflow:**
1. Open Cursor/Claude in MIA project
2. Type `@mcp-prompts list_prompts` to browse
3. Use prompts inline: `@mcp-prompts get_prompt gpio-testing`
4. AI automatically applies prompt context

**Benefits:**
- No manual copy-paste
- Always uses latest version
- Consistent across team

#### Level 2: HTTP REST API (Docker Service)

**Setup:**
```yaml
# docker-compose.yml
services:
  mcp-prompts:
    image: ghcr.io/sparesparrow/mcp-prompts:file
    ports:
      - "3000:3000"
    volumes:
      - ./prompts:/app/data
    environment:
      - MODE=http
      - STORAGE_TYPE=file
```

**Usage:**
```bash
# List all prompts
curl http://localhost:3000/v1/prompts

# Get specific prompt
curl http://localhost:3000/v1/prompts/citroen-obd-debugging

# Create new prompt
curl -X POST http://localhost:3000/v1/prompts \
  -H "Content-Type: application/json" \
  -d '{"name":"new-prompt", "content":"..."}'

# Apply template
curl -X POST http://localhost:3000/v1/prompts/mcp-module-template/apply \
  -d '{"variables": {"module_name": "battery-monitor"}}'
```

**Benefits:**
- Works with any HTTP client
- Custom integrations (CI/CD, scripts)
- Team-wide web dashboard

#### Level 3: Agentic Workflows (GitHub Actions)

**Example: Auto-generate test cases on PR**

```yaml
# .github/workflows/generate-tests.yml
name: Generate Missing Tests
on: pull_request

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Start mcp-prompts
        run: |
          docker run -d --name prompts \
            -v $PWD/prompts:/app/data \
            -p 3000:3000 \
            ghcr.io/sparesparrow/mcp-prompts:file

      - name: Find modules without tests
        run: |
          MODULES=$(find modules -name "main.py" -exec dirname {} \;)
          for mod in $MODULES; do
            if [ ! -f "tests/test_$(basename $mod).py" ]; then
              # Get test template from mcp-prompts
              curl -X POST http://localhost:3000/v1/prompts/integration-test-template/apply \
                -d "{\"component\": \"$mod\"}" > tests/test_$(basename $mod).py
            fi
          done

      - name: Commit generated tests
        run: |
          git add tests/
          git commit -m "chore: auto-generate missing test files"
          git push
```

**Benefits:**
- Automated consistency
- No manual boilerplate
- Self-improving (prompts updated = all future generations improve)

### MCP-Prompts for MIA Users (Non-Developers)

#### Home Automation Prompts

**"home-automation-commands"**
```
Control MIA smart home. Zones: {{zones}}.
Commands: lights (on/off/dim), climate (temp/mode), security (arm/disarm).
Current: {{current_state}}.
```

**Usage:**
```
User: "Turn off living room lights"
AI loads prompt with: zones=['living_room', 'kitchen', 'bedroom']
AI understands: Living room is valid zone, lights can be turned off
AI executes: GPIO command to smart switch
```

#### Vehicle Diagnostics Prompts

**"car-health-check"**
```
Analyze {{vehicle_model}} telemetry:
- DPF soot: {{dpf_level}}% (normal: 0-80%, urgent: >80%)
- Coolant temp: {{coolant_temp}}°C (normal: 80-100°C)
- Error codes: {{error_codes}}

Provide: health status, maintenance needs, urgency (low/medium/high).
```

**Usage:**
```
User: "How's my car?"
AI loads prompt with current OBD values
AI responds: "Health: GOOD. DPF at 45% (normal). Coolant 92°C (optimal).
             Recommendation: Schedule DPF service in 2000 km."
```

#### Daily Productivity Prompts

**"focus-mode-control"**
```
Work session manager. Mode: {{work_mode}}.
Block: {{blocked_apps}}. Timer: {{session_duration}} min.
Breaks: {{break_schedule}}.

Commands: 'extend +15min', 'take break', 'end work', 'status'.
```

**Usage:**
```
User: "Start deep work mode"
AI loads prompt, sets: work_mode='deep', blocks=['social_media', 'games'], timer=90
AI confirms: "Deep work started. Blocked distractions for 90 min. Next break: 10:30 AM"

User (80 min later): "Extend session"
AI: "Extended 15 minutes. New end time: 10:45 AM"
```

---

## 📋 Planning Documents Created

### 1. CLEANUP_AND_MCP_INTEGRATION_PLAN.md (Complete Technical Plan)

**Contents:**
- 6-phase cleanup strategy with step-by-step bash commands
- Code consolidation procedures
- Documentation reorganization scripts
- File naming standardization guide
- mcp-prompts integration (Docker, configuration, prompt library)
- SpareTools package enablement
- Testing and validation procedures
- Success metrics (code quality, developer experience, maintainability)

**Size:** 724 lines
**Purpose:** Technical reference for executing cleanup

### 2. EXECUTIVE_SUMMARY.md (Stakeholder Overview)

**Contents:**
- Current state analysis (what is MIA, hardware/OS/applications)
- Issues identified (duplication, documentation, naming)
- Detailed mcp-prompts explanation with use cases
- Cleanup plan overview with timeline
- Success metrics and risk mitigation
- Implementation options (full vs incremental)
- Decision support information

**Size:** 634 lines
**Purpose:** High-level overview for decision-making

### 3. TODO.md (Updated Roadmap)

**Changes:**
- Added Phase 5: Code Cleanup & MCP Integration
  - 5.1: Code consolidation tasks
  - 5.2: Documentation organization
  - 5.3: File naming standardization
  - 5.4: MCP-prompts integration
  - 5.5: SpareTools integration
  - 5.6: Testing and validation
- Updated phase numbering (old Phase 5 → Phase 6, etc.)
- Marked completed tasks in existing phases
- Added current status section with project health

**Purpose:** Single source of truth for project roadmap

### 4. docs/architecture/diagrams.md (Updated Architecture)

**New Diagrams:**
- Code organization after cleanup (module structure with shared libraries)
- Documentation organization (standardized hierarchy)
- MCP-prompts developer workflow (sequence diagram)
- MCP-prompts architecture integration (system diagram)

**Purpose:** Visual reference for new structure and integration patterns

---

## 📈 Cleanup Plan Summary

### Timeline: 3-4 Weeks

| Phase | Timeline | Focus | Outcome |
|-------|----------|-------|---------|
| **Phase 1** | Week 1 | Code consolidation | 3,682 → <500 duplicate lines |
| **Phase 2** | Week 1-2 | Documentation cleanup | 207 → <50 files |
| **Phase 3** | Week 2-3 | File naming | Consistent conventions |
| **Phase 4** | Week 2-3 | MCP-prompts | 20+ development prompts |
| **Phase 5** | Week 3 | SpareTools | Optimized deployment |
| **Phase 6** | Week 4 | Testing | 95%+ coverage, all CI passing |

### Success Metrics

**Code Quality:**
- ✅ Duplicate lines: < 500 (from 3,682) = 86% reduction
- ✅ Test coverage: > 95% (from 90%) = +5%
- ✅ Build time: < 5 min (from ~8 min) = 37% faster

**Documentation:**
- ✅ Total .md files: < 50 (from 207) = 76% reduction
- ✅ Clear hierarchy: 4 levels max
- ✅ Single source: No duplicate content

**Developer Experience:**
- ✅ Onboarding: < 1 hour (from ~4 hours) = 75% faster
- ✅ Module creation: 5 min with prompts (from 30 min manual) = 83% faster
- ✅ Debug workflow: Checklist-driven (from ad-hoc)

---

## 🚀 What Happens Next?

### Option A: Full Cleanup (Recommended)
- Execute all 6 phases over 3-4 weeks
- Single large PR with comprehensive testing
- Tag as `v2.0.0-clean` release
- **Best for:** Long-term maintainability

### Option B: Incremental Updates
- Phase 1 (Code) → PR #1
- Phase 2 (Docs) → PR #2
- Phase 3-4 (Integration) → PR #3
- **Best for:** Risk-averse approach, faster initial value

### Option C: Hybrid Approach
- Phases 1-2 together (Core cleanup)
- Phases 3-4 together (Integrations)
- **Best for:** Balance between speed and safety

### Option D: Deploy As-Is
- Code is production-ready now (92/100 health)
- Cleanup is optional optimization
- Can always do later
- **Best for:** Urgent deployment needed

---

## ✅ Completed Tasks

1. ✅ **Deep codebase exploration**
   - Analyzed 400+ source files
   - Identified 14 MCP modules
   - Mapped architecture and dependencies

2. ✅ **Issue identification**
   - Found 3,682 duplicate lines (mcp_framework)
   - Cataloged 29+ redundant documentation files
   - Identified backup/export directories
   - Noted inconsistent naming conventions

3. ✅ **mcp-prompts research**
   - Studied GitHub repository
   - Tested all 7 MCP tools
   - Explored 3 storage backends
   - Created integration patterns

4. ✅ **Comprehensive planning**
   - Created 6-phase cleanup strategy
   - Designed mcp-prompts integration
   - Planned SpareTools enablement
   - Defined success metrics

5. ✅ **Documentation creation**
   - CLEANUP_AND_MCP_INTEGRATION_PLAN.md (724 lines)
   - EXECUTIVE_SUMMARY.md (634 lines)
   - Updated TODO.md with Phase 5
   - Enhanced architecture diagrams

6. ✅ **Git operations**
   - Committed all planning documents
   - Pushed to branch: `claude/cleanup-and-mcp-integration-OCG8H`
   - Ready for review/approval

---

## 📞 Your Decision Points

### 1. Review Planning Documents

**Read these in order:**
1. **EXECUTIVE_SUMMARY.md** (this file) - Overview
2. **CLEANUP_AND_MCP_INTEGRATION_PLAN.md** - Technical details
3. **TODO.md** (Phase 5 section) - Task breakdown
4. **docs/architecture/diagrams.md** (new sections) - Visual reference

### 2. Choose Approach

**Which option fits your needs?**
- Option A (Full cleanup) - Best long-term, 3-4 weeks
- Option B (Incremental) - Safest, slower value
- Option C (Hybrid) - Balanced approach
- Option D (Deploy now) - Cleanup later

### 3. Grant Approval or Request Changes

**To proceed with Phase 1:**
- Say: "Approved, proceed with Phase 1"
- I'll execute code consolidation immediately

**To modify plan:**
- Specify what to change
- Request alternative approach
- Ask clarifying questions

**To defer cleanup:**
- Say: "Let's deploy as-is for now"
- Cleanup can happen anytime later

---

## 📚 Additional Resources

**GitHub Repository:** https://github.com/sparesparrow/mia
**Current Branch:** `claude/cleanup-and-mcp-integration-OCG8H`
**Pull Request:** Ready to create after your approval

**External Tools:**
- **mcp-prompts:** https://github.com/sparesparrow/mcp-prompts
- **MCP Spec:** https://modelcontextprotocol.io
- **SpareTools:** https://cloudsmith.io/~sparesparrow-conan/repos/sparetools/

**Documentation (Web Search Sources):**
- [GitHub - sparesparrow/mcp-prompts](https://github.com/sparesparrow/mcp-prompts)
- [NPM - @sparesparrow/mcp-prompts](https://www.npmjs.com/package/@sparesparrow/mcp-prompts)
- [Model Context Protocol - Prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)
- [MCP Prompts Concept](https://modelcontextprotocol.info/docs/concepts/prompts/)

---

**Analysis Complete. Awaiting your decision to proceed.**
