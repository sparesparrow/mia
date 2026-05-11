# Voice Command Learning System Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a comprehensive Claude Code plugin that implements and orchestrates the complete three-layer voice command learning system for MIA Universal.

**Architecture:** Multi-component orchestration plugin with skills (voice intelligence workflows), commands (deployment/monitoring), agents (system validation/health checking), MCP integration (5 learning prompts), and settings (configuration management). The plugin bridges the gap between the extensive documentation (20+ files across 3 layers) and actual implementation.

**Tech Stack:**
- Claude Code Plugin System (skills, commands, agents, hooks, MCP, settings)
- MCP Prompts (5 existing learning prompts)
- Python (for agent implementations)
- Markdown (for skill documentation)
- YAML (for configuration and frontmatter)
- JSON (for MCP prompt definitions)

---

## Prerequisites

**Verify documentation exists:**
```bash
ls -la docs/architecture/VOICE_KNOWLEDGE_SYSTEM_README.md
ls -la prompts/mia-voice-command-*.json
ls -la voice-command-learning-system.json
ls -la COMPLETE_VOICE_LEARNING_SYSTEM.md
```

**Expected:** All files exist. If missing, this plan cannot proceed.

---

## Task 1: Create Plugin Structure and Manifest

**Files:**
- Create: `.claude/plugins/voice-learning/plugin.json`
- Create: `.claude/plugins/voice-learning/README.md`
- Create: `.claude/plugins/voice-learning/.gitignore`

**Step 1: Create plugin directory**

```bash
mkdir -p .claude/plugins/voice-learning/{skills,commands,agents,settings}
```

**Step 2: Create plugin.json manifest**

Create `.claude/plugins/voice-learning/plugin.json`:

```json
{
  "name": "voice-learning",
  "version": "1.0.0",
  "description": "Comprehensive plugin for MIA's three-layer voice command learning system: storage, learning/synthesis, and orchestration",
  "author": "MIA Development Team",
  "tags": ["mia", "voice", "learning", "orchestration", "multi-agent"],
  "components": {
    "skills": ["voice-learning-workflow", "learning-cycle-management", "pattern-analysis"],
    "commands": ["deploy-infrastructure", "run-learning-cycle", "analyze-metrics", "manage-agents"],
    "agents": ["voice-system-validator", "deployment-orchestrator", "metrics-analyzer", "health-checker"],
    "settings": ["voice-learning.local.md"]
  },
  "dependencies": {
    "mcp_servers": ["mcp-prompts"],
    "required_tools": ["list_prompts", "get_prompt", "create_prompt", "update_prompt"]
  },
  "requirements": {
    "claude_code_version": ">=1.0.0",
    "python_version": ">=3.11"
  }
}
```

**Step 3: Create plugin README**

Create `.claude/plugins/voice-learning/README.md`:

```markdown
# Voice Command Learning System Plugin

Comprehensive Claude Code plugin that implements and orchestrates the complete three-layer voice command learning system for MIA Universal.

## Three-Layer Architecture

### Layer 1: Storage & Retrieval
- Hot cache (in-memory, <10ms)
- Warm index (SQLite, <100ms)
- Cold archive (compressed)
- Context Manager agent
- Privacy protection

### Layer 2: Learning & Synthesis
- 5 MCP learning prompts
- Knowledge-Synthesizer agent
- Pattern extraction and analysis
- Failure analysis and prevention
- Context effectiveness measurement

### Layer 3: Orchestration & Coordination
- 7 specialized agents
- 5-phase learning cycle
- Redis Streams messaging
- Performance monitoring
- Error coordination

## Components

### Skills
- `voice-learning-workflow` - Complete 4-phase voice command workflow
- `learning-cycle-management` - Manage the 5-phase learning cycle
- `pattern-analysis` - Analyze command patterns and user preferences

### Commands
- `deploy-infrastructure` - Deploy storage, agents, and message bus
- `run-learning-cycle` - Trigger manual learning cycle execution
- `analyze-metrics` - Analyze system performance and learning metrics
- `manage-agents` - Start/stop/monitor agent health

### Agents
- `voice-system-validator` - Validate system configuration and components
- `deployment-orchestrator` - Orchestrate deployment of all components
- `metrics-analyzer` - Deep analysis of system metrics and trends
- `health-checker` - Monitor agent health and system status

### Settings
- `voice-learning.local.md` - Configuration for storage paths, endpoints, thresholds

## Usage

### Initial Setup
```
/deploy-infrastructure
```

### Run Learning Cycle
```
/run-learning-cycle
```

### Analyze Performance
```
/analyze-metrics
```

## Documentation References

- Master Guide: `COMPLETE_VOICE_LEARNING_SYSTEM.md`
- Storage Layer: `docs/architecture/VOICE_KNOWLEDGE_SYSTEM_README.md`
- Learning Layer: `VOICE_COMMAND_LEARNING_GUIDE.md`
- Orchestration: `VOICE_COMMAND_LEARNING_ARCHITECTURE.md`
- Gap Analysis: `VOICE_COMMAND_INTELLIGENCE_ANALYSIS.json`
```

**Step 4: Create .gitignore**

Create `.claude/plugins/voice-learning/.gitignore`:

```
*.pyc
__pycache__/
.pytest_cache/
.coverage
*.local.md
.DS_Store
```

**Step 5: Verify structure**

Run:
```bash
tree .claude/plugins/voice-learning -L 2
```

Expected output:
```
.claude/plugins/voice-learning
├── plugin.json
├── README.md
├── .gitignore
├── skills/
├── commands/
├── agents/
└── settings/
```

**Step 6: Commit**

```bash
git add .claude/plugins/voice-learning/
git commit -m "feat(plugin): initialize voice-learning plugin structure

- Add plugin.json manifest with component definitions
- Add comprehensive README with architecture overview
- Create directory structure for skills, commands, agents, settings"
```

---

## Task 2: Create Voice Learning Workflow Skill

**Files:**
- Create: `.claude/plugins/voice-learning/skills/voice-learning-workflow/SKILL.md`

**Step 1: Create skill directory**

```bash
mkdir -p .claude/plugins/voice-learning/skills/voice-learning-workflow
```

**Step 2: Create SKILL.md with frontmatter and content**

Create `.claude/plugins/voice-learning/skills/voice-learning-workflow/SKILL.md`:

```markdown
---
name: voice-learning-workflow
description: Complete 4-phase voice command workflow with learning integration
tags: ["mia", "voice", "learning", "workflow"]
---

# Voice Learning Workflow Skill

Execute the complete 4-phase voice command learning workflow with MCP prompt integration.

## When to Use

Use this skill when working with voice command development, optimization, or analysis:
- Designing new voice commands
- Analyzing command effectiveness
- Implementing context-aware interpretation
- Tracking command execution results
- Running learning cycles

## Phase 1: Voice Interface Design

**Objective:** Design and optimize voice command interfaces using established patterns.

### Step 1.1: Discover Existing Commands

Query the MCP prompts knowledge base:

```javascript
list_prompts(tags: ["mia", "voice-command"])
```

**Expected:** List of existing voice command prompts including:
- `mia-car-voice-command`
- `mia-car-voice-response`
- `mia-car-climate-control`
- `mia-car-navigation`
- `mia-car-emergency-response`

### Step 1.2: Get Design Guidelines

Retrieve design principles for the target platform:

```javascript
get_prompt("voice-command-design-principles", {
  deviceType: "mobile|raspberry-pi|car",
  userContext: "developer|homeowner|driver",
  focusAreas: "clarity|context-awareness|safety"
})
```

**Note:** If this prompt doesn't exist, use the skill to create it from documentation.

### Step 1.3: Evaluate Command Clarity

Check command clarity and confusability:

```javascript
get_prompt("voice-command-clarity-checklist", {
  commands: current_commands_array,
  userFeedback: collected_feedback_data
})
```

**Output:** Clarity assessment with recommendations for improvement.

## Phase 2: Context-Aware Interpretation

**Objective:** Process voice input with contextual understanding to improve accuracy.

### Step 2.1: Query Context

When processing a voice command, retrieve relevant context:

```javascript
get_prompt("mia-context-analyzer", {
  currentLocation: device_location,
  recentActions: action_history_array,
  deviceState: system_state_object,
  timeOfDay: current_time
})
```

**Context Variables to Include:**
- `user_id` - User identifier (anonymized)
- `timestamp` - ISO-8601 timestamp
- `device_type` - "mobile", "raspberry-pi", "car"
- `location` - GPS coordinates or zone
- `time_of_day` - "morning", "afternoon", "evening", "night"
- `recent_commands` - Last 5 commands
- `device_state` - Battery, network, sensors
- `ambient_conditions` - Noise level, lighting

### Step 2.2: Interpret with Context

Use context to disambiguate commands:

**Example:**
- **Command:** "lights"
- **Without Context:** Ambiguous (on? off? status?)
- **With Context:**
  - `timeOfDay: "night"` + `recentActions: ["enter_car"]` → "turn on lights"
  - `recentActions: ["lights_on"]` → "show light status"

### Step 2.3: Generate Confident Response

Generate a context-aware response:

```javascript
get_prompt("voice-response-generator", {
  interpretation: chosen_meaning,
  confidence: confidence_score,
  context: extracted_context
})
```

**Confidence Thresholds:**
- `>0.9` - Execute immediately
- `0.7-0.9` - Execute with confirmation
- `<0.7` - Ask for clarification

## Phase 3: Action Execution & Result Capture

**Objective:** Execute commands and capture results for learning.

### Step 3.1: Execute Command

Route the command to the appropriate service via MCP framework.

### Step 3.2: Capture Result

**Success Case:**
```javascript
{
  command_id: "uuid",
  intent: "climate_control",
  parameters: {temperature: 22},
  execution_status: "success",
  execution_time_ms: 450,
  user_satisfaction: 5
}
```

Store in analytics database for learning.

### Step 3.3: Handle Failures

If command fails or is unclear:

```javascript
create_prompt({
  name: `voice-command-failure-analysis-${cmdId}`,
  content: {
    original_command: voice_text,
    interpretation: attempted_interpretation,
    failure_type: "recognition|interpretation|execution|response",
    error_details: error_message,
    context: captured_context,
    timestamp: iso_timestamp
  },
  tags: ["mia", "voice-command", "failure", "learning"]
})
```

## Phase 4: Learning Loop

**Objective:** Continuously improve the system through analytics and pattern discovery.

### Step 4.1: Collect Interaction Analytics

**Metrics to Track:**
- Total commands processed
- Success rate (by intent type)
- Confidence score distribution
- Context boost effectiveness
- User satisfaction ratings
- Execution latency

### Step 4.2: Identify Patterns

Run pattern analysis on batches of interactions:

```javascript
get_prompt("mia-voice-command-pattern-synthesis", {
  analysis_period: "last_24h",
  command_sample: interaction_batch,
  success_data: success_metrics,
  failure_data: failure_metrics
})
```

**Output:** Discovered patterns including:
- Intent families (similar commands)
- Parameter variations
- Context patterns
- Success predictors

### Step 4.3: Update System

When high-confidence patterns emerge:

```javascript
create_prompt({
  name: `voice-command-pattern-${category}`,
  content: command_pattern_guidelines,
  tags: ["mia", "voice-command", category, "learned"],
  metadata: {
    confidence: 0.95,
    sample_size: 1000,
    discovery_date: timestamp
  }
})
```

### Step 4.4: Trigger Learning Cycles

**Real-time:** After each interaction
- Store interaction data
- Update metrics
- Flag anomalies

**Daily:** Batch pattern synthesis
- Analyze 100+ interactions
- Discover new patterns
- Generate recommendations

**Weekly:** Comprehensive analysis
- Context effectiveness
- User preference trends
- System improvements

## Integration with MIA Components

### With Storage Layer (Layer 1)
- Store all interactions in hot cache
- Query warm index for recent patterns
- Archive old data to cold storage
- Use Context Manager for retrieval

### With Learning Layer (Layer 2)
- Use 5 MCP learning prompts
- Invoke Knowledge-Synthesizer agent
- Generate actionable insights
- Update NLP models

### With Orchestration Layer (Layer 3)
- Coordinate via Learning Loop Orchestrator
- Monitor via Performance Monitor
- Handle errors via Error Coordinator
- Analyze patterns via Voice Pattern Analyzer

## Success Metrics

Track these KPIs:
- **Command Accuracy:** ≥85% intent recognition
- **Parameter Quality:** ≥90% correct extraction
- **User Satisfaction:** ≥4.0/5.0 rating
- **Response Time:** <1000ms p95
- **Learning Rate:** ≥2% accuracy improvement per cycle

## Privacy Considerations

- Delete raw audio immediately after processing
- Anonymize user IDs after 90 days
- Store only aggregated patterns (federated learning)
- Apply differential privacy for pattern sharing
- Obtain explicit user consent for data collection

## Common Patterns

### Pattern: Ambiguous Command Resolution
```
1. Receive ambiguous command
2. Query context with mia-context-analyzer
3. Generate top 3 interpretations with confidence
4. If top confidence >0.9: execute
5. If top confidence 0.7-0.9: confirm with user
6. If top confidence <0.7: ask for clarification
7. Store resolution for learning
```

### Pattern: New Category Discovery
```
1. Collect 100+ interactions with low-confidence intent classification
2. Analyze with pattern-synthesis prompt
3. If cluster emerges with >0.85 similarity:
   a. Create new intent category
   b. Generate command pattern prompt
   c. Update NLP classifier
   d. A/B test improvements
```

### Pattern: Context Boost Optimization
```
1. Track context usage and command success
2. Calculate: success_with_context vs success_without_context
3. If delta >5%: increase context weight
4. If delta <2%: decrease context weight
5. Update context boost configuration
```

## Example Usage

```
User: "I'm working on voice commands for the car system. Can you help me design a better climate control interface?"

Claude (using this skill):

Phase 1: Let me discover existing commands and design guidelines.

[Queries mcp-prompts for existing car voice commands]
[Gets voice-command-design-principles for car context]

I found 3 existing climate control commands. Here are clarity improvements:

1. "Set temperature to 22" - Clear (keep)
2. "Make it warmer" - Ambiguous (could be +1°C or +5°C)
3. "Climate on" - Unclear (what settings?)

Recommendations:
- Add explicit increment commands: "Increase temperature by 2 degrees"
- Define default behaviors: "Climate on" → use last saved settings
- Add confirmation for large changes: ">5°C change requires confirmation"

Phase 2: Now let's add context awareness...

[Continues through all phases]
```
```

**Step 3: Verify skill file**

Run:
```bash
head -20 .claude/plugins/voice-learning/skills/voice-learning-workflow/SKILL.md
```

Expected: Shows frontmatter with name, description, tags.

**Step 4: Commit**

```bash
git add .claude/plugins/voice-learning/skills/voice-learning-workflow/
git commit -m "feat(skill): add voice-learning-workflow skill

- Complete 4-phase workflow (design, interpretation, execution, learning)
- MCP prompt integration for all phases
- Context-aware interpretation guidance
- Learning loop implementation details
- Privacy-first design patterns"
```

---

## Task 3: Create Learning Cycle Management Skill

**Files:**
- Create: `.claude/plugins/voice-learning/skills/learning-cycle-management/SKILL.md`

**Step 1: Create skill directory**

```bash
mkdir -p .claude/plugins/voice-learning/skills/learning-cycle-management
```

**Step 2: Create SKILL.md**

Create `.claude/plugins/voice-learning/skills/learning-cycle-management/SKILL.md`:

```markdown
---
name: learning-cycle-management
description: Manage the 5-phase continuous learning cycle for voice commands
tags: ["mia", "learning", "orchestration", "multi-agent"]
---

# Learning Cycle Management Skill

Coordinate the complete 5-phase learning cycle that continuously improves voice command recognition and response quality.

## When to Use

Use this skill when:
- Triggering manual learning cycles
- Monitoring learning progress
- Debugging learning failures
- Optimizing cycle timing
- Validating learning effectiveness

## The 5-Phase Learning Cycle

### Phase 1: Collection (Continuous)

**Agents Involved:** Voice Command Intelligence

**Objective:** Capture all voice interactions with full context.

**What to Collect:**
```javascript
{
  interaction_id: "uuid",
  timestamp: "ISO-8601",
  user_context: {
    user_id: "anonymized",
    location: "gps_or_zone",
    device_type: "mobile|car|rpi",
    time_of_day: "morning|afternoon|evening|night"
  },
  voice_input: {
    text: "transcribed_command",
    acoustic_features: ["duration", "pitch", "volume"],
    confidence: 0.95
  },
  interpretation: {
    intent: "climate_control",
    parameters: {temperature: 22},
    confidence: 0.92,
    alternatives: [{intent: "fan_control", confidence: 0.78}]
  },
  execution: {
    service: "climate-service",
    status: "success|failure|partial",
    duration_ms: 450,
    result: {action_performed: true}
  },
  user_feedback: {
    satisfaction: 5,
    correction: null,
    confirmation: true
  }
}
```

**Storage:** Write to hot cache immediately, batch to warm index every 5 minutes.

**Success Metric:** 100% of interactions logged with <10ms latency.

### Phase 2: Analysis (5-15 minutes)

**Agents Involved:** Performance Monitor, Error Coordinator, Voice Pattern Analyzer

**Objective:** Extract learning signals from collected interactions.

**Analysis Types:**

**2.1 Performance Analysis** (Performance Monitor)
```javascript
get_prompt("mia-voice-command-learning", {
  analysis_period: "last_15_min",
  interactions: interaction_batch,
  success_rate: 0.87,
  avg_confidence: 0.85,
  context_usage: {
    location: 0.42,
    time_of_day: 0.33,
    recent_actions: 0.25
  }
})
```

**Output:** Success rate trends, confidence score distribution, context effectiveness.

**2.2 Failure Analysis** (Error Coordinator)
```javascript
get_prompt("mia-voice-command-failure-analysis", {
  failures: failed_interactions,
  failure_types: ["recognition", "interpretation", "execution"],
  root_causes: analysis_results,
  impact: affected_user_count
})
```

**Output:** Classified failures with root causes and prevention strategies.

**2.3 Pattern Detection** (Voice Pattern Analyzer)
```javascript
get_prompt("mia-voice-command-pattern-synthesis", {
  command_samples: interaction_batch,
  min_pattern_size: 10,
  confidence_threshold: 0.85
})
```

**Output:** Intent families, parameter variations, command sequences.

**Trigger Conditions:**
- Time-based: Every 15 minutes
- Metric-based: Error rate increase >5%
- Event-based: New user onboarded

**Success Metric:** Analysis complete in <15 minutes with >90% anomaly detection rate.

### Phase 3: Synthesis (5-30 minutes)

**Agents Involved:** Knowledge Synthesizer

**Objective:** Consolidate insights from analysis and generate improvement recommendations.

**Synthesis Process:**

**3.1 Aggregate Insights**

Combine results from all analyzers:
```javascript
{
  performance_insights: performance_monitor_output,
  failure_patterns: error_coordinator_output,
  linguistic_patterns: pattern_analyzer_output,
  context_insights: context_analyzer_output
}
```

**3.2 Generate Knowledge**

```javascript
get_prompt("mia-voice-command-knowledge-synthesis", {
  insights: aggregated_insights,
  time_period: "last_24h",
  sample_size: 1500,
  current_accuracy: 0.87
})
```

**Expected Output:**
```javascript
{
  synthesis_id: "uuid",
  insights: [
    {
      type: "intent_family",
      pattern: "temperature_control_variants",
      confidence: 0.95,
      sample_size: 342,
      description: "Users use 'warm', 'warmer', 'heat up' interchangeably"
    }
  ],
  recommendations: [
    {
      priority: "high",
      type: "add_synonyms",
      target: "climate_control_intent",
      action: "Add ['warm', 'warmer', 'heat up'] to intent patterns",
      expected_improvement: "+3% accuracy",
      confidence: 0.95
    }
  ],
  new_patterns: [
    {
      name: "voice-command-pattern-temperature-control-variants",
      content: "Pattern definition...",
      tags: ["learned", "temperature", "synonyms"]
    }
  ]
}
```

**Success Metric:** Synthesis completes in <30 minutes, generates ≥10 actionable insights with >85% confidence.

### Phase 4: Implementation (30 minutes - 24 hours)

**Agents Involved:** Voice Command Intelligence, Learning Loop Orchestrator

**Objective:** Apply improvements to the system.

**Implementation Steps:**

**4.1 Prioritize Recommendations**

Sort by:
1. Expected improvement (impact)
2. Confidence score
3. Implementation complexity
4. Risk level

**4.2 Validate Safety**

Check each recommendation:
- ✅ Doesn't reduce existing accuracy
- ✅ Doesn't introduce security issues
- ✅ Doesn't violate privacy policies
- ✅ Has rollback plan

**4.3 Apply Changes**

**For Model Updates:**
```python
# Update NLP intent classifier
model.add_intent_synonyms(
    intent="climate_control",
    synonyms=["warm", "warmer", "heat up"],
    weight=0.95
)
model.retrain_incremental()
```

**For Pattern Creation:**
```javascript
create_prompt({
  name: recommendation.new_pattern_name,
  content: recommendation.pattern_definition,
  tags: recommendation.tags,
  metadata: {
    created_by: "learning_cycle",
    confidence: recommendation.confidence,
    expected_improvement: recommendation.expected_improvement
  }
})
```

**For Configuration Updates:**
```yaml
# Update context boost weights
context_boost:
  location: 0.45  # increased from 0.42
  time_of_day: 0.33
  recent_actions: 0.22  # decreased from 0.25
```

**4.4 A/B Test (Optional)**

For high-impact changes:
```python
ab_test = {
    "name": "temperature_synonyms_test",
    "treatment": "new_model_with_synonyms",
    "control": "current_model",
    "split": 50/50,
    "duration": "7 days",
    "success_metric": "intent_accuracy"
}
```

**Success Metric:** >70% of high-priority recommendations implemented within 24 hours.

### Phase 5: Validation (Continuous)

**Agents Involved:** Performance Monitor

**Objective:** Measure improvement effectiveness and detect regressions.

**Validation Process:**

**5.1 Track Metrics**

Compare before/after metrics:
```javascript
{
  before: {
    accuracy: 0.87,
    avg_confidence: 0.85,
    satisfaction: 4.1
  },
  after: {
    accuracy: 0.89,  // +2.3% improvement
    avg_confidence: 0.87,  // +2.4% improvement
    satisfaction: 4.3  // +4.9% improvement
  },
  improvement: {
    accuracy_delta: +0.02,
    met_expectation: true,  // expected +3%, achieved +2.3%
    confidence_level: 0.95
  }
}
```

**5.2 Detect Regressions**

Alert if:
- Accuracy drops >1% from baseline
- Error rate increases >3%
- User satisfaction drops >0.2 points

**5.3 Rollback if Needed**

```python
if regression_detected:
    rollback_to_version(previous_version)
    log_failure(recommendation_id, reason="regression_detected")
    notify_orchestrator("learning_cycle_rollback")
```

**Success Metric:** Validation detects 100% of regressions within 1 hour, <5% false positive rate.

## Cycle Coordination

### Triggering Conditions

**Time-Based Triggers:**
```yaml
triggers:
  quick_analysis: "every 5 minutes"
  synthesis_cycle: "every 1 hour"
  major_update: "every 8 hours"
  comprehensive_review: "daily at 2am"
```

**Metric-Based Triggers:**
```yaml
triggers:
  error_rate_spike: "error_rate > baseline + 5%"
  success_rate_drop: "success_rate < baseline - 3%"
  new_failure_pattern: "unique_failure_type not in known_patterns"
  high_confidence_improvement: "recommendation_confidence > 0.95"
```

**Event-Based Triggers:**
```yaml
triggers:
  user_feedback_received: "user_correction or user_rating < 3"
  new_user_onboarded: "new_user_id detected"
  model_performance_degradation: "p95_latency > 2000ms"
  system_update_completed: "version_change detected"
```

### Orchestration Workflow

```
Learning Loop Orchestrator:

1. Receive trigger (time/metric/event)
2. Check if previous cycle completed
3. If not: queue trigger for later
4. If yes: start new cycle

Phase 1 (Collection): Always running
  ↓
Phase 2 (Analysis): Triggered every 15 min or on metric threshold
  ↓ (send results to message bus)
Phase 3 (Synthesis): Triggered when Phase 2 completes
  ↓ (send recommendations to message bus)
Phase 4 (Implementation): Triggered when Phase 3 completes
  ↓ (apply changes, notify monitor)
Phase 5 (Validation): Continuous monitoring of Phase 4 changes
  ↓ (if regression: rollback; if success: keep)
[Cycle repeats]
```

## Message Bus Communication

**Message Types:**

**1. Collection Event**
```json
{
  "type": "interaction_collected",
  "interaction_id": "uuid",
  "timestamp": "ISO-8601",
  "metadata": {}
}
```

**2. Analysis Complete**
```json
{
  "type": "analysis_complete",
  "phase": "analysis",
  "analyzer": "performance_monitor",
  "results": {},
  "timestamp": "ISO-8601"
}
```

**3. Synthesis Complete**
```json
{
  "type": "synthesis_complete",
  "synthesis_id": "uuid",
  "recommendations_count": 8,
  "high_priority_count": 3,
  "timestamp": "ISO-8601"
}
```

**4. Implementation Started**
```json
{
  "type": "implementation_started",
  "recommendation_ids": ["uuid1", "uuid2"],
  "estimated_duration_min": 45,
  "timestamp": "ISO-8601"
}
```

**5. Implementation Complete**
```json
{
  "type": "implementation_complete",
  "recommendation_id": "uuid",
  "status": "success",
  "applied_changes": {},
  "timestamp": "ISO-8601"
}
```

**6. Validation Alert**
```json
{
  "type": "validation_alert",
  "alert_level": "warning|critical",
  "metric": "accuracy",
  "current_value": 0.85,
  "expected_value": 0.89,
  "recommendation_id": "uuid",
  "timestamp": "ISO-8601"
}
```

**7. Cycle Status**
```json
{
  "type": "cycle_status",
  "cycle_id": "uuid",
  "phase": "synthesis",
  "status": "in_progress",
  "progress": 0.65,
  "estimated_completion": "ISO-8601"
}
```

## Monitoring and Debugging

### Cycle Health Indicators

```javascript
{
  cycle_completion_rate: 0.98,  // >98% target
  avg_cycle_duration_min: 42,  // <60 min target
  improvement_rate: 0.023,  // >2% target
  rollback_rate: 0.03,  // <5% target
  recommendation_adoption_rate: 0.72  // >70% target
}
```

### Common Issues

**Issue: Synthesis taking too long**
- Check: Data volume (>10,000 interactions?)
- Fix: Increase batch size, reduce sample size, add parallel processing

**Issue: Low recommendation adoption**
- Check: Confidence thresholds too high?
- Fix: Lower threshold to 0.80, increase sample size for confidence

**Issue: Frequent rollbacks**
- Check: A/B testing enabled?
- Fix: Enable A/B testing for high-impact changes, increase validation period

**Issue: No improvements detected**
- Check: Baseline metrics stale?
- Fix: Refresh baseline every week, ensure sufficient data variety

## Example Usage

```
User: "Run a learning cycle analysis on the last 24 hours of voice commands."

Claude (using this skill):

Starting 5-phase learning cycle...

Phase 1: Collection ✓
- Collected: 1,247 interactions
- Storage: Hot cache → Warm index
- Completeness: 100%

Phase 2: Analysis (in progress)
- Performance Monitor: analyzing success rates...
  → Success rate: 87% (+2% from baseline)
  → Avg confidence: 0.85
  → Context usage: location 42%, time 33%, actions 25%

- Error Coordinator: analyzing 162 failures...
  → Recognition failures: 45 (noise interference)
  → Interpretation failures: 89 (ambiguous commands)
  → Execution failures: 28 (service timeout)

- Pattern Analyzer: detecting patterns...
  → Found 3 new intent families
  → Detected 12 parameter variations
  → Identified 5 command sequences

Phase 2: Complete (12 minutes)

Phase 3: Synthesis (in progress)
- Aggregating insights from 3 analyzers...
- Generating recommendations...
  → High priority: 4 recommendations
  → Medium priority: 7 recommendations
  → Low priority: 3 recommendations

Top recommendation:
  Priority: HIGH
  Type: Add synonyms
  Target: climate_control intent
  Action: Add ["warm", "warmer", "heat up"] to patterns
  Expected improvement: +3% accuracy
  Confidence: 0.95

Phase 3: Complete (8 minutes)

Phase 4: Implementation
- Applying 4 high-priority recommendations...
  [1/4] Adding climate control synonyms... ✓
  [2/4] Updating context boost weights... ✓
  [3/4] Creating new pattern prompt... ✓
  [4/4] Incremental model retraining... ✓

Phase 4: Complete (35 minutes)

Phase 5: Validation (monitoring)
- Tracking metrics for next 24 hours...
- Will alert if regression detected.

Learning cycle complete!
- Cycle ID: 7f3e9a2b-...
- Duration: 55 minutes
- Recommendations applied: 4
- Expected improvement: +3.2% accuracy
```
```

**Step 3: Commit**

```bash
git add .claude/plugins/voice-learning/skills/learning-cycle-management/
git commit -m "feat(skill): add learning-cycle-management skill

- Complete 5-phase learning cycle workflow
- Phase 1: Collection (continuous)
- Phase 2: Analysis (5-15 min)
- Phase 3: Synthesis (5-30 min)
- Phase 4: Implementation (30 min - 24h)
- Phase 5: Validation (continuous)
- Message bus communication protocols
- Monitoring and debugging guidance"
```

---

## Task 4: Create Deploy Infrastructure Command

**Files:**
- Create: `.claude/plugins/voice-learning/commands/deploy-infrastructure.md`

**Step 1: Create command file**

Create `.claude/plugins/voice-learning/commands/deploy-infrastructure.md`:

```markdown
---
name: deploy-infrastructure
description: Deploy complete voice learning infrastructure (storage, agents, message bus)
arguments: []
---

# Deploy Voice Learning Infrastructure

This command deploys the complete three-layer voice learning infrastructure:
- Layer 1: Storage (hot/warm/cold cache, Context Manager)
- Layer 2: Learning agents (Knowledge Synthesizer, Pattern Analyzer, etc.)
- Layer 3: Orchestration (message bus, Learning Loop Orchestrator)

## Prerequisites Check

Before deploying, verify:

1. **Python environment:**
   ```bash
   python3 --version  # ≥3.11
   pip3 list | grep -E "(redis|sqlite|pymongo)"
   ```

2. **Required services:**
   ```bash
   redis-server --version  # For message bus
   sqlite3 --version  # For warm index
   ```

3. **Configuration files exist:**
   ```bash
   ls -la .claude/plugins/voice-learning/settings/voice-learning.local.md
   ls -la voice-command-learning-system.json
   ls -la docs/architecture/voice-command-knowledge-storage-spec.json
   ```

## Deployment Steps

### Step 1: Create Storage Infrastructure

**Hot Cache (In-Memory):**

Python implementation for hot cache:

```python
# modules/voice-learning/storage/hot_cache.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

class HotCache:
    """In-memory hot cache for recent interactions (<10ms access)"""

    def __init__(self, ttl_minutes: int = 30, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
        self.access_count = 0
        self.hit_count = 0

    def put(self, key: str, value: Dict[str, Any]) -> None:
        """Store interaction in hot cache"""
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = {
            "data": value,
            "timestamp": datetime.now(),
            "access_count": 0
        }

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve interaction from hot cache"""
        self.access_count += 1

        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check if expired
        if datetime.now() - entry["timestamp"] > self.ttl:
            del self.cache[key]
            return None

        # Update access count
        entry["access_count"] += 1
        self.hit_count += 1

        return entry["data"]

    def _evict_oldest(self) -> None:
        """Evict least recently accessed entry"""
        if not self.cache:
            return

        oldest_key = min(
            self.cache.keys(),
            key=lambda k: (
                self.cache[k]["access_count"],
                self.cache[k]["timestamp"]
            )
        )
        del self.cache[oldest_key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = self.hit_count / self.access_count if self.access_count > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "access_count": self.access_count,
            "hit_count": self.hit_count
        }
```

Create the file:
```bash
mkdir -p modules/voice-learning/storage
# Create hot_cache.py with above content
```

**Warm Index (SQLite):**

```python
# modules/voice-learning/storage/warm_index.py
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

class WarmIndex:
    """SQLite warm index for 7-day history (<100ms access)"""

    def __init__(self, db_path: str = "data/voice_learning_warm.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                device_type TEXT NOT NULL,
                voice_text TEXT NOT NULL,
                intent TEXT NOT NULL,
                confidence REAL NOT NULL,
                parameters TEXT,
                execution_status TEXT,
                execution_duration_ms INTEGER,
                user_satisfaction INTEGER,
                context TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indices for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON interactions(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON interactions(user_id, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intent
            ON interactions(intent, timestamp DESC)
        """)

        conn.commit()
        conn.close()

    def insert(self, interaction: Dict[str, Any]) -> None:
        """Insert interaction into warm index"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO interactions (
                interaction_id, timestamp, user_id, device_type,
                voice_text, intent, confidence, parameters,
                execution_status, execution_duration_ms,
                user_satisfaction, context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction["interaction_id"],
            interaction["timestamp"],
            interaction["user_context"]["user_id"],
            interaction["user_context"]["device_type"],
            interaction["voice_input"]["text"],
            interaction["interpretation"]["intent"],
            interaction["interpretation"]["confidence"],
            json.dumps(interaction["interpretation"]["parameters"]),
            interaction["execution"]["status"],
            interaction["execution"]["duration_ms"],
            interaction.get("user_feedback", {}).get("satisfaction"),
            json.dumps(interaction["user_context"])
        ))

        conn.commit()
        conn.close()

    def query_recent(self, hours: int = 24, limit: int = 1000) -> List[Dict[str, Any]]:
        """Query recent interactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT * FROM interactions
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (cutoff, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def query_by_intent(self, intent: str, hours: int = 168) -> List[Dict[str, Any]]:
        """Query interactions by intent (default: 7 days)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT * FROM interactions
            WHERE intent = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (intent, cutoff))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        return {
            "interaction_id": row[0],
            "timestamp": row[1],
            "user_id": row[2],
            "device_type": row[3],
            "voice_text": row[4],
            "intent": row[5],
            "confidence": row[6],
            "parameters": json.loads(row[7]) if row[7] else {},
            "execution_status": row[8],
            "execution_duration_ms": row[9],
            "user_satisfaction": row[10],
            "context": json.loads(row[11]) if row[11] else {}
        }

    def cleanup_old_data(self, days: int = 7) -> int:
        """Remove data older than N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            DELETE FROM interactions WHERE timestamp < ?
        """, (cutoff,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count
```

Create the file:
```bash
# Create warm_index.py with above content
```

### Step 2: Deploy Message Bus (Redis Streams)

```bash
# Start Redis server
redis-server --daemonize yes

# Verify Redis is running
redis-cli ping  # Should return "PONG"

# Create message topics
redis-cli XGROUP CREATE voice-learning:interactions mia-agents $ MKSTREAM
redis-cli XGROUP CREATE voice-learning:analysis mia-agents $ MKSTREAM
redis-cli XGROUP CREATE voice-learning:synthesis mia-agents $ MKSTREAM
redis-cli XGROUP CREATE voice-learning:implementation mia-agents $ MKSTREAM
redis-cli XGROUP CREATE voice-learning:validation mia-agents $ MKSTREAM
```

### Step 3: Deploy Context Manager Agent

```bash
# Start Context Manager agent
python3 modules/voice-learning/agents/context_manager.py &

# Verify agent is running
ps aux | grep context_manager

# Check agent health
curl http://localhost:8001/health
# Expected: {"status": "healthy", "agent": "context_manager"}
```

### Step 4: Deploy Learning Agents

```bash
# Start Knowledge Synthesizer
python3 modules/voice-learning/agents/knowledge_synthesizer.py &

# Start Performance Monitor
python3 modules/voice-learning/agents/performance_monitor.py &

# Start Error Coordinator
python3 modules/voice-learning/agents/error_coordinator.py &

# Start Voice Pattern Analyzer
python3 modules/voice-learning/agents/voice_pattern_analyzer.py &

# Start Learning Loop Orchestrator
python3 modules/voice-learning/agents/learning_loop_orchestrator.py &

# Verify all agents running
ps aux | grep "voice-learning/agents"
```

### Step 5: Verify Deployment

```bash
# Check storage infrastructure
python3 -c "
from modules.voice_learning.storage.hot_cache import HotCache
cache = HotCache()
print('Hot cache initialized:', cache.get_stats())
"

# Check message bus
redis-cli XINFO STREAM voice-learning:interactions

# Check agent connectivity
curl http://localhost:8001/health  # Context Manager
curl http://localhost:8002/health  # Knowledge Synthesizer
curl http://localhost:8003/health  # Performance Monitor
curl http://localhost:8004/health  # Error Coordinator
curl http://localhost:8005/health  # Voice Pattern Analyzer
curl http://localhost:8006/health  # Learning Loop Orchestrator
```

Expected: All health checks return `{"status": "healthy"}`.

## Post-Deployment Verification

Run this verification script:

```bash
python3 modules/voice-learning/scripts/verify_deployment.py
```

Expected output:
```
✓ Hot cache operational (access time: 3ms)
✓ Warm index operational (query time: 45ms)
✓ Redis message bus operational
✓ All 6 agents healthy
✓ Message topics created
✓ Storage directories exist
✓ Configuration loaded successfully

Deployment Status: SUCCESS
```

## Rollback Procedure

If deployment fails:

```bash
# Stop all agents
pkill -f "voice-learning/agents"

# Stop Redis
redis-cli SHUTDOWN

# Remove databases
rm -f data/voice_learning_warm.db

# Restore previous configuration
git checkout .claude/plugins/voice-learning/settings/voice-learning.local.md
```

## Configuration

Edit `.claude/plugins/voice-learning/settings/voice-learning.local.md`:

```yaml
---
storage:
  hot_cache:
    ttl_minutes: 30
    max_size: 1000
  warm_index:
    db_path: "data/voice_learning_warm.db"
    retention_days: 7
  cold_archive:
    path: "data/voice_learning_archive/"
    compression: "gzip"

message_bus:
  redis_host: "localhost"
  redis_port: 6379
  stream_prefix: "voice-learning"

agents:
  context_manager:
    port: 8001
  knowledge_synthesizer:
    port: 8002
  performance_monitor:
    port: 8003
  error_coordinator:
    port: 8004
  voice_pattern_analyzer:
    port: 8005
  learning_loop_orchestrator:
    port: 8006

learning_cycle:
  triggers:
    quick_analysis: "5m"
    synthesis_cycle: "1h"
    major_update: "8h"
    comprehensive_review: "daily@02:00"
  thresholds:
    error_rate_spike: 0.05
    success_rate_drop: 0.03
    confidence_threshold: 0.85
---

# Voice Learning System Configuration

This file configures the complete voice learning infrastructure.

## Storage Configuration

- **Hot Cache:** In-memory cache for last 30 minutes (1000 interactions max)
- **Warm Index:** SQLite database for last 7 days
- **Cold Archive:** Compressed long-term storage

## Agent Configuration

All agents expose health check endpoints on their configured ports.

## Learning Cycle Configuration

Trigger conditions are configurable for different cycle frequencies.
```

## Success Criteria

Deployment is successful when:

- ✓ Hot cache responds in <10ms
- ✓ Warm index responds in <100ms
- ✓ All 6 agents are healthy
- ✓ Redis message bus operational
- ✓ Storage directories created
- ✓ Configuration loaded
- ✓ No errors in agent logs

## Monitoring

After deployment, monitor:

```bash
# Watch agent logs
tail -f logs/voice-learning/*.log

# Monitor Redis streams
redis-cli MONITOR

# Check storage usage
du -sh data/voice_learning_*

# Monitor agent health
watch -n 5 'curl -s http://localhost:8001/health | jq'
```
```

**Step 2: Commit**

```bash
git add .claude/plugins/voice-learning/commands/deploy-infrastructure.md
git commit -m "feat(command): add deploy-infrastructure command

- Deploy complete 3-layer infrastructure
- Hot cache (in-memory, <10ms)
- Warm index (SQLite, <100ms)
- Redis Streams message bus
- 6 learning agents
- Verification and rollback procedures"
```

---

## Task 5: Create Voice System Validator Agent

**Files:**
- Create: `.claude/plugins/voice-learning/agents/voice-system-validator/AGENT.md`
- Create: `.claude/plugins/voice-learning/agents/voice-system-validator/agent.py`

**Step 1: Create agent directory**

```bash
mkdir -p .claude/plugins/voice-learning/agents/voice-system-validator
```

**Step 2: Create AGENT.md**

Create `.claude/plugins/voice-learning/agents/voice-system-validator/AGENT.md`:

```markdown
---
name: voice-system-validator
description: Validate voice learning system configuration, components, and integration
color: blue
---

# Voice System Validator Agent

Validates the complete voice learning system configuration, verifies all components are properly integrated, and identifies configuration issues.

## When to Invoke

Invoke this agent:
- After deploying infrastructure (`/deploy-infrastructure`)
- Before running learning cycles
- When debugging system issues
- After configuration changes
- During system health checks

## Agent Capabilities

### 1. Configuration Validation

Validates:
- Storage configuration (hot/warm/cold paths, retention)
- Message bus configuration (Redis connection, topics)
- Agent configuration (ports, health endpoints)
- Learning cycle configuration (triggers, thresholds)
- MCP prompt availability (5 learning prompts)

### 2. Component Health Checks

Checks:
- Storage infrastructure (hot cache, warm index, cold archive)
- Message bus connectivity (Redis Streams)
- Agent health (6 agents: Context Manager, Knowledge Synthesizer, Performance Monitor, Error Coordinator, Voice Pattern Analyzer, Learning Loop Orchestrator)
- MCP server connectivity

### 3. Integration Validation

Validates:
- Agent-to-agent communication
- Message bus pub/sub
- Storage read/write operations
- MCP prompt retrieval
- Learning cycle workflows

### 4. Performance Validation

Measures:
- Hot cache latency (<10ms target)
- Warm index latency (<100ms target)
- Agent response times (<500ms target)
- Message bus throughput

## Input Contract

```json
{
  "validation_type": "full|quick|config-only|health-only",
  "components": ["storage", "message_bus", "agents", "mcp", "integration"],
  "verbose": true|false
}
```

## Output Contract

```json
{
  "validation_id": "uuid",
  "timestamp": "ISO-8601",
  "status": "pass|fail|warning",
  "summary": {
    "total_checks": 45,
    "passed": 42,
    "failed": 2,
    "warnings": 1
  },
  "results": [
    {
      "component": "storage.hot_cache",
      "check": "latency",
      "status": "pass",
      "measured": "3ms",
      "target": "<10ms",
      "message": "Hot cache latency within target"
    },
    {
      "component": "agents.context_manager",
      "check": "health",
      "status": "fail",
      "error": "Connection refused on port 8001",
      "recommendation": "Start Context Manager agent"
    }
  ],
  "recommendations": [
    "Start Context Manager agent (port 8001)",
    "Increase warm index cache size for better performance"
  ]
}
```

## Validation Workflow

```
1. Load configuration from voice-learning.local.md
2. Validate configuration schema
3. Check storage infrastructure:
   - Hot cache operational?
   - Warm index accessible?
   - Cold archive path exists?
4. Check message bus:
   - Redis running?
   - Topics created?
   - Can publish/subscribe?
5. Check agents:
   - For each agent:
     - Health endpoint reachable?
     - Response time acceptable?
     - Error rate acceptable?
6. Check MCP integration:
   - 5 learning prompts available?
   - Can retrieve prompts?
7. Check integration:
   - Can agents communicate?
   - Can write to storage?
   - Can publish to message bus?
8. Generate validation report
9. Provide recommendations for failures
```

## Usage Examples

**Full System Validation:**
```
Input: {
  "validation_type": "full",
  "components": ["storage", "message_bus", "agents", "mcp", "integration"],
  "verbose": true
}

Output: Comprehensive validation report with 45 checks.
```

**Quick Health Check:**
```
Input: {
  "validation_type": "quick",
  "components": ["agents"],
  "verbose": false
}

Output: Agent health status only (6 checks, fast).
```

**Configuration Validation:**
```
Input: {
  "validation_type": "config-only",
  "components": ["storage", "message_bus", "agents"],
  "verbose": true
}

Output: Configuration schema validation without runtime checks.
```

## Success Criteria

Validation passes when:
- ✓ All required configuration keys present
- ✓ Storage infrastructure operational
- ✓ Message bus operational
- ✓ All 6 agents healthy
- ✓ 5 MCP learning prompts available
- ✓ Integration tests pass

## Common Issues and Fixes

| Issue | Recommendation |
|-------|----------------|
| Hot cache latency >10ms | Reduce cache size or increase memory |
| Warm index latency >100ms | Add indices, reduce retention period |
| Redis not running | Start Redis: `redis-server --daemonize yes` |
| Agent health check fails | Check agent logs, verify port not in use |
| MCP prompts missing | Run `list_prompts(tags=["mia", "voice"])` to verify |
| Integration test fails | Check agent connectivity and message bus |
```

**Step 3: Create agent.py implementation stub**

Create `.claude/plugins/voice-learning/agents/voice-system-validator/agent.py`:

```python
"""
Voice System Validator Agent

Validates voice learning system configuration and health.
"""

from typing import Dict, Any, List
from datetime import datetime
import json

class VoiceSystemValidator:
    """Validator agent for voice learning system"""

    def __init__(self, config_path: str = ".claude/plugins/voice-learning/settings/voice-learning.local.md"):
        self.config_path = config_path
        self.config = self._load_config()
        self.results: List[Dict[str, Any]] = []

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from settings file"""
        # TODO: Implement YAML frontmatter parsing
        return {}

    def validate_full(self) -> Dict[str, Any]:
        """Run full system validation"""
        validation_id = f"val-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self.results = []

        # Run all validation checks
        self._validate_config()
        self._validate_storage()
        self._validate_message_bus()
        self._validate_agents()
        self._validate_mcp()
        self._validate_integration()

        # Generate summary
        summary = self._generate_summary()

        # Generate recommendations
        recommendations = self._generate_recommendations()

        return {
            "validation_id": validation_id,
            "timestamp": datetime.now().isoformat(),
            "status": summary["status"],
            "summary": summary,
            "results": self.results,
            "recommendations": recommendations
        }

    def _validate_config(self) -> None:
        """Validate configuration schema"""
        # TODO: Implement configuration validation
        pass

    def _validate_storage(self) -> None:
        """Validate storage infrastructure"""
        # TODO: Implement storage validation
        pass

    def _validate_message_bus(self) -> None:
        """Validate Redis message bus"""
        # TODO: Implement message bus validation
        pass

    def _validate_agents(self) -> None:
        """Validate agent health"""
        # TODO: Implement agent health checks
        pass

    def _validate_mcp(self) -> None:
        """Validate MCP prompt availability"""
        # TODO: Implement MCP validation
        pass

    def _validate_integration(self) -> None:
        """Validate integration between components"""
        # TODO: Implement integration tests
        pass

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = sum(1 for r in self.results if r["status"] == "fail")
        warnings = sum(1 for r in self.results if r["status"] == "warning")

        status = "pass" if failed == 0 else "fail" if failed > 3 else "warning"

        return {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "status": status
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on failed checks"""
        recommendations = []

        for result in self.results:
            if result["status"] == "fail" and "recommendation" in result:
                recommendations.append(result["recommendation"])

        return recommendations


if __name__ == "__main__":
    validator = VoiceSystemValidator()
    report = validator.validate_full()
    print(json.dumps(report, indent=2))
```

**Step 4: Commit**

```bash
git add .claude/plugins/voice-learning/agents/voice-system-validator/
git commit -m "feat(agent): add voice-system-validator agent

- Validates configuration, storage, message bus, agents, MCP
- Runs health checks and integration tests
- Generates validation reports with recommendations
- Stub implementation for TDD development"
```

---

## Task 6: Create Settings Template

**Files:**
- Create: `.claude/plugins/voice-learning/settings/voice-learning.local.md.template`

**Step 1: Create settings template**

Create `.claude/plugins/voice-learning/settings/voice-learning.local.md.template`:

```markdown
---
storage:
  hot_cache:
    ttl_minutes: 30
    max_size: 1000
  warm_index:
    db_path: "data/voice_learning_warm.db"
    retention_days: 7
    cache_size_mb: 100
  cold_archive:
    path: "data/voice_learning_archive/"
    compression: "gzip"
    retention_years: 2

message_bus:
  redis_host: "localhost"
  redis_port: 6379
  stream_prefix: "voice-learning"
  consumer_group: "mia-agents"
  max_retries: 3
  ack_timeout_ms: 5000

agents:
  context_manager:
    port: 8001
    host: "localhost"
  knowledge_synthesizer:
    port: 8002
    host: "localhost"
  performance_monitor:
    port: 8003
    host: "localhost"
  error_coordinator:
    port: 8004
    host: "localhost"
  voice_pattern_analyzer:
    port: 8005
    host: "localhost"
  learning_loop_orchestrator:
    port: 8006
    host: "localhost"

learning_cycle:
  triggers:
    quick_analysis: "5m"
    synthesis_cycle: "1h"
    major_update: "8h"
    comprehensive_review: "daily@02:00"
  thresholds:
    error_rate_spike: 0.05
    success_rate_drop: 0.03
    confidence_threshold: 0.85
    min_sample_size: 100
  optimization:
    batch_size: 500
    parallel_analyzers: 3
    max_cycle_duration_min: 60

performance:
  targets:
    hot_cache_latency_ms: 10
    warm_index_latency_ms: 100
    agent_response_time_ms: 500
    cache_hit_rate: 0.89
  monitoring:
    metrics_retention_days: 30
    alert_on_regression: true
    rollback_on_critical: true

privacy:
  anonymization:
    user_id_after_days: 90
    location_precision: "zone"  # "exact", "zone", "city"
  retention:
    raw_audio: "delete_immediately"
    interactions: 365  # days
    aggregated_patterns: "indefinite"
  consent:
    required: true
    opt_out_available: true
---

# Voice Learning System Configuration

This file contains the configuration for the voice command learning system.

## Configuration Sections

### Storage Configuration

- **Hot Cache:** In-memory cache for most recent interactions
  - TTL: 30 minutes
  - Max size: 1000 interactions
  - Target latency: <10ms

- **Warm Index:** SQLite database for 7-day history
  - Retention: 7 days
  - Cache size: 100 MB
  - Target latency: <100ms

- **Cold Archive:** Compressed long-term storage
  - Compression: gzip
  - Retention: 2 years

### Message Bus Configuration

- **Redis Streams** for agent communication
- Consumer group: `mia-agents`
- Automatic retries on failure (max 3)

### Agent Configuration

All agents run on localhost with dedicated ports:
- Context Manager: 8001
- Knowledge Synthesizer: 8002
- Performance Monitor: 8003
- Error Coordinator: 8004
- Voice Pattern Analyzer: 8005
- Learning Loop Orchestrator: 8006

### Learning Cycle Configuration

**Trigger Frequencies:**
- Quick analysis: Every 5 minutes
- Synthesis cycle: Every 1 hour
- Major update: Every 8 hours
- Comprehensive review: Daily at 2:00 AM

**Thresholds:**
- Error rate spike: 5% above baseline
- Success rate drop: 3% below baseline
- Confidence threshold: 0.85 for auto-apply

### Performance Targets

- Hot cache: <10ms latency
- Warm index: <100ms latency
- Agent response: <500ms
- Cache hit rate: >89%

### Privacy Configuration

**Anonymization:**
- User IDs anonymized after 90 days
- Location stored at zone level (not exact GPS)

**Retention:**
- Raw audio: Deleted immediately after transcription
- Interactions: 365 days
- Aggregated patterns: Indefinite (no PII)

**Consent:**
- Explicit consent required for data collection
- Opt-out available at any time

## Customization

Copy this template to `voice-learning.local.md` and customize for your environment:

```bash
cp voice-learning.local.md.template voice-learning.local.md
# Edit voice-learning.local.md with your settings
```

**Note:** `voice-learning.local.md` is in `.gitignore` and will not be committed.

## Validation

Validate your configuration:

```
/manage-agents validate-config
```

Expected output: `Configuration valid: ✓`
```

**Step 2: Create .gitignore entry**

Edit `.claude/plugins/voice-learning/.gitignore` to add:

```
*.local.md
```

**Step 3: Commit**

```bash
git add .claude/plugins/voice-learning/settings/voice-learning.local.md.template
git add .claude/plugins/voice-learning/.gitignore
git commit -m "feat(settings): add configuration template

- Complete settings template with YAML frontmatter
- Storage, message bus, agent, learning cycle config
- Performance targets and privacy settings
- Detailed documentation and customization guide
- Add *.local.md to .gitignore"
```

---

## Task 7: Create Plugin Documentation

**Files:**
- Create: `.claude/plugins/voice-learning/docs/ARCHITECTURE.md`
- Create: `.claude/plugins/voice-learning/docs/GETTING_STARTED.md`
- Create: `.claude/plugins/voice-learning/docs/TROUBLESHOOTING.md`

**Step 1: Create ARCHITECTURE.md**

Create `.claude/plugins/voice-learning/docs/ARCHITECTURE.md`:

```markdown
# Voice Learning Plugin Architecture

Complete technical architecture documentation for the voice command learning system plugin.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE PLUGIN                           │
│                     (voice-learning)                             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
     ┌────▼────┐              ┌────▼────┐
     │ Skills  │              │Commands │
     └────┬────┘              └────┬────┘
          │                        │
     ┌────▼────────────────────────▼────┐
     │         ORCHESTRATION            │
     │    (Learning Loop Orchestrator)   │
     └────┬────────────────────────┬────┘
          │                        │
     ┌────▼────┐              ┌────▼────┐
     │ Agents  │              │  MCP    │
     └────┬────┘              └────┬────┘
          │                        │
          └────────────┬───────────┘
                       │
          ┌────────────▼────────────┐
          │    MESSAGE BUS          │
          │   (Redis Streams)       │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │    STORAGE LAYER        │
          │  (Hot/Warm/Cold Cache)  │
          └─────────────────────────┘
```

## Component Architecture

### Layer 1: Plugin Interface (Claude Code)

**Skills:**
- `voice-learning-workflow` - 4-phase voice command workflow
- `learning-cycle-management` - 5-phase learning cycle management
- `pattern-analysis` - Command pattern analysis and discovery

**Commands:**
- `/deploy-infrastructure` - Deploy complete infrastructure
- `/run-learning-cycle` - Trigger learning cycle
- `/analyze-metrics` - Analyze system metrics
- `/manage-agents` - Agent management

**Agents:**
- `voice-system-validator` - System validation and health checks
- `deployment-orchestrator` - Deployment coordination
- `metrics-analyzer` - Deep metrics analysis
- `health-checker` - Continuous health monitoring

### Layer 2: Storage & Retrieval

**Hot Cache (In-Memory):**
- Purpose: Ultra-fast access to recent interactions
- Technology: Python dict with TTL and LRU eviction
- Performance: <10ms latency
- Capacity: 1000 interactions (30 min TTL)

**Warm Index (SQLite):**
- Purpose: Fast queries for 7-day history
- Technology: SQLite with indices
- Performance: <100ms latency
- Capacity: 7 days retention

**Cold Archive (Compressed):**
- Purpose: Long-term pattern storage
- Technology: Gzip compressed JSON
- Performance: >1s latency (acceptable)
- Capacity: 2 years retention

**Context Manager Agent:**
- Coordinates storage tier access
- Implements data lifecycle policies
- Provides unified query interface
- Handles data migration (hot → warm → cold)

### Layer 3: Learning & Synthesis

**MCP Prompts (5 Total):**
1. `mia-voice-command-learning` - Single interaction learning
2. `mia-voice-command-failure-analysis` - Failure root cause analysis
3. `mia-voice-command-pattern-synthesis` - Batch pattern synthesis
4. `mia-voice-context-analyzer` - Context effectiveness analysis
5. `mia-voice-command-knowledge-synthesis` - Knowledge consolidation

**Knowledge Synthesizer Agent:**
- Aggregates insights from all analyzers
- Generates actionable recommendations
- Creates new pattern prompts
- Measures confidence and impact

**Voice Pattern Analyzer Agent:**
- Detects command variations
- Identifies user preferences
- Discovers intent families
- Tracks acoustic patterns

**Performance Monitor Agent:**
- Collects real-time metrics
- Tracks success/failure rates
- Measures response times
- Identifies bottlenecks

**Error Coordinator Agent:**
- Classifies failures (recognition, interpretation, execution, response)
- Determines root causes
- Coordinates recovery
- Tracks remediation effectiveness

### Layer 4: Orchestration & Coordination

**Learning Loop Orchestrator Agent:**
- Coordinates 5-phase learning cycle
- Manages agent communication
- Triggers cycle based on time/metrics/events
- Monitors cycle health

**Message Bus (Redis Streams):**
- Event-driven pub/sub
- 7 message types (see Communication Protocols)
- Guaranteed delivery
- Message ordering per topic

## Communication Protocols

### Message Types

**1. interaction_collected**
```json
{
  "type": "interaction_collected",
  "interaction_id": "uuid",
  "timestamp": "ISO-8601",
  "metadata": {}
}
```

**2. analysis_complete**
```json
{
  "type": "analysis_complete",
  "phase": "analysis",
  "analyzer": "performance_monitor",
  "results": {},
  "timestamp": "ISO-8601"
}
```

**3. synthesis_complete**
```json
{
  "type": "synthesis_complete",
  "synthesis_id": "uuid",
  "recommendations_count": 8,
  "high_priority_count": 3,
  "timestamp": "ISO-8601"
}
```

**4. implementation_started**
```json
{
  "type": "implementation_started",
  "recommendation_ids": ["uuid1", "uuid2"],
  "estimated_duration_min": 45,
  "timestamp": "ISO-8601"
}
```

**5. implementation_complete**
```json
{
  "type": "implementation_complete",
  "recommendation_id": "uuid",
  "status": "success|failure",
  "applied_changes": {},
  "timestamp": "ISO-8601"
}
```

**6. validation_alert**
```json
{
  "type": "validation_alert",
  "alert_level": "warning|critical",
  "metric": "accuracy",
  "current_value": 0.85,
  "expected_value": 0.89,
  "recommendation_id": "uuid",
  "timestamp": "ISO-8601"
}
```

**7. cycle_status**
```json
{
  "type": "cycle_status",
  "cycle_id": "uuid",
  "phase": "synthesis",
  "status": "in_progress|complete|failed",
  "progress": 0.65,
  "estimated_completion": "ISO-8601"
}
```

## Data Flow

### Voice Command Execution Flow

```
1. User speaks command
   ↓
2. Voice Command Intelligence agent processes
   ↓
3. Query Context Manager for user context
   ↓
4. Interpret with context awareness
   ↓
5. Execute via MCP service routing
   ↓
6. Capture result
   ↓
7. Store in hot cache
   ↓
8. Publish "interaction_collected" to message bus
   ↓
9. Performance Monitor updates metrics
10. Voice Pattern Analyzer queues for analysis
```

### Learning Cycle Flow

```
Phase 1: Collection (continuous)
  - Voice Command Intelligence captures interactions
  - Write to hot cache
  - Batch to warm index every 5 min

Phase 2: Analysis (every 15 min or on trigger)
  - Performance Monitor analyzes success rates
  - Error Coordinator analyzes failures
  - Voice Pattern Analyzer detects patterns
  - Publish "analysis_complete" messages

Phase 3: Synthesis (triggered by analysis completion)
  - Knowledge Synthesizer aggregates insights
  - Generate recommendations
  - Create new pattern prompts
  - Publish "synthesis_complete" message

Phase 4: Implementation (triggered by synthesis)
  - Learning Loop Orchestrator prioritizes recommendations
  - Validate safety
  - Apply changes (model updates, pattern creation)
  - Publish "implementation_complete" messages

Phase 5: Validation (continuous)
  - Performance Monitor tracks metrics
  - Compare before/after
  - Detect regressions
  - Publish "validation_alert" if issues detected
```

## Scalability Considerations

### Horizontal Scaling

**Voice Pattern Analyzer:**
- Stateless design
- Work queue with batch processing
- Scale trigger: Analysis backlog >1000 interactions

**Knowledge Synthesizer:**
- Distributed synthesis with result aggregation
- Scale trigger: Knowledge base size growth

**Performance Monitor:**
- Time-series database sharding
- Scale trigger: Metric ingestion rate >10k/sec

### Vertical Scaling

**Context Manager:**
- Database capacity (SQLite → PostgreSQL)
- Metric: Query response time >200ms

**Message Bus:**
- Redis cluster mode
- Metric: Queue depth >10k messages

## Security & Privacy

**Data Protection:**
- Raw audio deleted immediately after transcription
- User IDs hashed after 90 days
- PII anonymization before archival
- Encryption at rest (AES-256)

**Access Control:**
- RBAC for agent access
- API authentication required
- Audit logging of all access

**Compliance:**
- GDPR-compliant data retention
- User consent tracking
- Right to deletion support
- Differential privacy for pattern sharing

## Monitoring & Observability

**Key Metrics:**
- Command processing latency (p50, p95, p99)
- Command success rate (by intent type)
- Learning cycle completion time
- Pattern detection accuracy
- Agent health status
- Message queue depth

**Alerting Thresholds:**
- Success rate <90%: CRITICAL
- Response time p95 >2000ms: WARNING
- Agent uptime <99%: CRITICAL
- Learning cycle failure rate >5%: WARNING

**Observability Tools:**
- Distributed tracing (OpenTelemetry)
- Metrics collection (Prometheus)
- Centralized logging (ELK)
- Custom dashboards (Grafana)

## Failure Handling

**Resilience Patterns:**
- Circuit breaker (prevent cascading failures)
- Timeout and retry (exponential backoff)
- Fallback (use previous model version)
- Bulkhead (separate thread pools per agent)
- Health checks (periodic liveness checks)

**Recovery Scenarios:**

| Failure | Impact | Recovery |
|---------|--------|----------|
| Voice Command Intelligence failure | Commands not processed | Fallback to previous model, retry |
| Context Manager failure | Context unavailable | Use in-memory cache, restore from backup |
| Knowledge Synthesizer failure | Learning stops | Skip cycle, retry with backoff |
| Message queue failure | Agent communication disrupted | Queue persistence, sync fallback |

## Performance Targets

| Component | Target | Measurement |
|-----------|--------|-------------|
| Hot cache latency | <10ms | p95 |
| Warm index latency | <100ms | p95 |
| Agent response time | <500ms | p95 |
| Cache hit rate | >89% | average |
| Learning cycle duration | <60min | average |
| Success rate | >85% | by intent type |
| User satisfaction | >4.0/5.0 | average rating |

## Technology Stack

**Languages:**
- Python 3.11+ (agent implementations)
- Markdown (skill documentation)
- YAML (configuration)
- JSON (MCP prompts, data storage)

**Databases:**
- Redis Streams (message bus)
- SQLite (warm index)
- File system (hot cache, cold archive)

**Tools:**
- Claude Code Plugin System
- MCP (Model Context Protocol)
- OpenTelemetry (tracing)
- Prometheus (metrics)

**Dependencies:**
- redis-py
- sqlite3 (built-in)
- pyyaml
- json (built-in)
```

**Step 2: Create GETTING_STARTED.md**

Create `.claude/plugins/voice-learning/docs/GETTING_STARTED.md`:

```markdown
# Getting Started with Voice Learning Plugin

Complete guide to install, configure, and use the voice command learning system plugin.

## Prerequisites

### Required Software

1. **Claude Code CLI** (>=1.0.0)
   ```bash
   claude --version
   ```

2. **Python 3.11+**
   ```bash
   python3 --version
   ```

3. **Redis** (for message bus)
   ```bash
   redis-server --version
   ```

4. **SQLite3** (usually pre-installed)
   ```bash
   sqlite3 --version
   ```

### Required Python Packages

```bash
pip3 install redis pyyaml
```

## Installation

### Step 1: Install Plugin

The plugin is located at `.claude/plugins/voice-learning/` in the MIA project.

Verify installation:
```bash
ls -la .claude/plugins/voice-learning/plugin.json
```

### Step 2: Configure Settings

Copy the settings template:
```bash
cd .claude/plugins/voice-learning/settings
cp voice-learning.local.md.template voice-learning.local.md
```

Edit `voice-learning.local.md` for your environment:
```yaml
---
storage:
  warm_index:
    db_path: "/absolute/path/to/data/voice_learning_warm.db"
  cold_archive:
    path: "/absolute/path/to/data/voice_learning_archive/"

message_bus:
  redis_host: "localhost"  # or your Redis host
  redis_port: 6379

agents:
  # Default ports 8001-8006 usually work
  # Change if ports conflict with other services
---
```

### Step 3: Start Redis

```bash
redis-server --daemonize yes

# Verify
redis-cli ping  # Should return "PONG"
```

### Step 4: Verify MCP Prompts

Check that the 5 required MCP prompts exist:

```bash
ls -la prompts/mia-voice-command-learning.json
ls -la prompts/mia-voice-command-failure-analysis.json
ls -la prompts/mia-voice-command-pattern-synthesis.json
ls -la prompts/mia-voice-context-analyzer.json
ls -la prompts/mia-voice-command-knowledge-synthesis.json
```

## Quick Start

### 1. Deploy Infrastructure

Deploy the complete infrastructure:

```
/deploy-infrastructure
```

This will:
- Create storage directories
- Initialize hot cache
- Initialize warm index (SQLite)
- Start Redis message bus
- Start 6 learning agents
- Verify deployment

Expected output:
```
✓ Storage infrastructure deployed
✓ Message bus operational
✓ 6 agents started successfully
✓ Deployment verified

Deployment Status: SUCCESS
```

### 2. Validate System

Validate the complete system:

```
User: "Validate the voice learning system"

Claude will automatically invoke the voice-system-validator agent.
```

Expected output:
```
Validation Report:
✓ Configuration valid
✓ Storage operational (hot cache: 3ms, warm index: 45ms)
✓ Message bus operational
✓ All 6 agents healthy
✓ 5 MCP prompts available
✓ Integration tests passed

Status: PASS (45/45 checks passed)
```

### 3. Run Learning Cycle

Trigger a learning cycle manually:

```
/run-learning-cycle
```

This will execute the 5-phase cycle:
1. Collection (continuous)
2. Analysis (5-15 min)
3. Synthesis (5-30 min)
4. Implementation (30 min - 24h)
5. Validation (continuous)

### 4. Analyze Metrics

View system metrics:

```
/analyze-metrics
```

Output includes:
- Command success rates
- Response time distribution
- Learning cycle effectiveness
- Agent health status
- Storage usage

## Using Skills

### Voice Learning Workflow Skill

Use when working with voice commands:

```
User: "I'm designing voice commands for climate control. Help me improve clarity."

Claude (using voice-learning-workflow skill):

Phase 1: Voice Interface Design
[Discovers existing commands via MCP prompts]
[Gets design principles]
[Evaluates clarity]

Recommendations:
1. Add explicit temperature increments
2. Define default behaviors
3. Add confirmation for large changes
...
```

### Learning Cycle Management Skill

Use when managing learning cycles:

```
User: "Run a learning cycle on the last 24 hours."

Claude (using learning-cycle-management skill):

Starting 5-phase learning cycle...

Phase 1: Collection ✓
- Collected: 1,247 interactions
...

Phase 5: Validation (monitoring)
- Will alert if regression detected

Learning cycle complete!
- Duration: 55 minutes
- Recommendations applied: 4
- Expected improvement: +3.2% accuracy
```

## Common Workflows

### Workflow 1: Deploy New Voice Command

```
1. User: "I need to add a new voice command for seat heating."

2. Claude uses voice-learning-workflow skill:
   - Phase 1: Design command patterns
   - Phase 2: Define context awareness
   - Phase 3: Implement execution logic
   - Phase 4: Set up learning tracking

3. Deploy to system:
   /deploy-infrastructure  # if new infrastructure needed

4. Test command with real users

5. Monitor learning:
   /analyze-metrics

6. Learning cycle runs automatically and improves command over time
```

### Workflow 2: Debug System Issues

```
1. User: "Voice commands are slow. What's wrong?"

2. Validate system:
   User: "Validate the system"
   Claude invokes voice-system-validator agent

3. Review validation report:
   - If storage latency high: Increase cache size
   - If agent unhealthy: Check logs
   - If message bus slow: Check Redis

4. Apply fixes

5. Re-validate:
   User: "Validate again"

6. Monitor improvements:
   /analyze-metrics
```

### Workflow 3: Analyze Learning Effectiveness

```
1. Trigger learning cycle:
   /run-learning-cycle

2. Wait for cycle completion (~1 hour)

3. Analyze results:
   /analyze-metrics

4. Review metrics:
   - Pattern discovery: How many new patterns found?
   - Recommendation adoption: How many applied?
   - Improvement rate: Did accuracy increase?
   - Validation: Any regressions detected?

5. If improvements insufficient:
   - Check sample size (need >100 interactions)
   - Check confidence thresholds
   - Check A/B testing enabled
   - Review user feedback collection
```

## Configuration Guide

### Storage Configuration

**Hot Cache:**
```yaml
storage:
  hot_cache:
    ttl_minutes: 30  # Longer = more memory, better analysis
    max_size: 1000   # Increase if high traffic
```

**Warm Index:**
```yaml
storage:
  warm_index:
    retention_days: 7      # Increase for longer history
    cache_size_mb: 100     # Increase if slow queries
```

### Learning Cycle Configuration

**Trigger Frequencies:**
```yaml
learning_cycle:
  triggers:
    quick_analysis: "5m"   # Real-time feedback
    synthesis_cycle: "1h"  # Regular improvements
    major_update: "8h"     # Model retraining
    comprehensive_review: "daily@02:00"  # Full analysis
```

**Thresholds:**
```yaml
learning_cycle:
  thresholds:
    confidence_threshold: 0.85  # Lower = more aggressive improvements
    min_sample_size: 100        # Higher = more confidence
```

### Performance Tuning

**For High Traffic:**
- Increase hot cache size
- Add warm index cache
- Enable parallel analysis
- Increase batch size

**For Low Latency:**
- Reduce hot cache TTL
- Add SSD for warm index
- Optimize Redis configuration
- Reduce analysis frequency

**For Better Learning:**
- Increase sample size
- Enable A/B testing
- Lower confidence threshold
- Increase synthesis frequency

## Monitoring

### Health Checks

Check agent health:
```bash
curl http://localhost:8001/health  # Context Manager
curl http://localhost:8002/health  # Knowledge Synthesizer
curl http://localhost:8003/health  # Performance Monitor
curl http://localhost:8004/health  # Error Coordinator
curl http://localhost:8005/health  # Voice Pattern Analyzer
curl http://localhost:8006/health  # Learning Loop Orchestrator
```

### Logs

View agent logs:
```bash
tail -f logs/voice-learning/*.log
```

### Metrics

Monitor Redis:
```bash
redis-cli MONITOR
```

Check storage:
```bash
du -sh data/voice_learning_*
```

## Next Steps

1. **Read the Architecture docs:** [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Review Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **Explore Skills:** Read skill documentation in `skills/*/SKILL.md`
4. **Review MCP Prompts:** Check `prompts/mia-voice-*.json`
5. **Study the Master Guide:** Read `COMPLETE_VOICE_LEARNING_SYSTEM.md`

## Support

**Documentation:**
- Master Guide: `COMPLETE_VOICE_LEARNING_SYSTEM.md`
- Storage Layer: `docs/architecture/VOICE_KNOWLEDGE_SYSTEM_README.md`
- Learning Layer: `VOICE_COMMAND_LEARNING_GUIDE.md`
- Orchestration: `VOICE_COMMAND_LEARNING_ARCHITECTURE.md`

**Troubleshooting:**
- Common issues: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Gap analysis: `VOICE_COMMAND_INTELLIGENCE_ANALYSIS.json`

**Community:**
- Report issues on GitHub
- Contribute improvements via PR
```

**Step 3: Create TROUBLESHOOTING.md**

Create `.claude/plugins/voice-learning/docs/TROUBLESHOOTING.md`:

```markdown
# Troubleshooting Guide

Common issues and solutions for the voice learning plugin.

## Deployment Issues

### Issue: Redis Connection Refused

**Symptoms:**
```
Error: Connection refused on Redis port 6379
Agent startup failed: Cannot connect to message bus
```

**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# If not running:
redis-server --daemonize yes

# Verify:
redis-cli ping  # Should return "PONG"

# Check configuration:
cat .claude/plugins/voice-learning/settings/voice-learning.local.md | grep redis
```

### Issue: Agent Port Already in Use

**Symptoms:**
```
Error: Address already in use: 8001
Context Manager failed to start
```

**Solution:**
```bash
# Find process using port
lsof -i :8001

# Kill process
kill <PID>

# Or change port in configuration:
# Edit .claude/plugins/voice-learning/settings/voice-learning.local.md
agents:
  context_manager:
    port: 9001  # Use different port
```

### Issue: Storage Directory Not Found

**Symptoms:**
```
Error: No such file or directory: 'data/voice_learning_warm.db'
Warm index initialization failed
```

**Solution:**
```bash
# Create data directories
mkdir -p data/voice_learning_archive

# Update configuration with absolute paths:
storage:
  warm_index:
    db_path: "/absolute/path/to/mia/data/voice_learning_warm.db"
  cold_archive:
    path: "/absolute/path/to/mia/data/voice_learning_archive/"
```

### Issue: Missing MCP Prompts

**Symptoms:**
```
Validation failed: MCP prompt 'mia-voice-context-analyzer' not found
```

**Solution:**
```bash
# Check if prompts exist
ls -la prompts/mia-voice-*.json

# If missing, check gap analysis:
cat VOICE_COMMAND_INTELLIGENCE_ANALYSIS.json | jq '.existing_prompts_audit.missing_critical_prompts'

# Create missing prompts using templates
# See VOICE_COMMAND_LEARNING_GUIDE.md for prompt structure
```

## Performance Issues

### Issue: Hot Cache Latency >10ms

**Symptoms:**
```
Hot cache latency: 15ms (target: <10ms)
Performance validation: WARNING
```

**Solution:**
```yaml
# Reduce cache size
storage:
  hot_cache:
    max_size: 500  # reduce from 1000

# Or increase memory allocation
# Or reduce TTL
storage:
  hot_cache:
    ttl_minutes: 15  # reduce from 30
```

### Issue: Warm Index Latency >100ms

**Symptoms:**
```
Warm index query time: 150ms (target: <100ms)
Storage validation: WARNING
```

**Solution:**
```bash
# Add indices to SQLite database
sqlite3 data/voice_learning_warm.db <<EOF
CREATE INDEX IF NOT EXISTS idx_timestamp ON interactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_id ON interactions(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_intent ON interactions(intent, timestamp DESC);
EOF

# Increase cache size
storage:
  warm_index:
    cache_size_mb: 200  # increase from 100

# Reduce retention period
storage:
  warm_index:
    retention_days: 3  # reduce from 7
```

### Issue: Learning Cycle Takes Too Long

**Symptoms:**
```
Learning cycle duration: 95 minutes (target: <60 minutes)
Synthesis phase taking 45 minutes
```

**Solution:**
```yaml
# Increase batch size
learning_cycle:
  optimization:
    batch_size: 1000  # increase from 500

# Enable parallel analysis
learning_cycle:
  optimization:
    parallel_analyzers: 5  # increase from 3

# Reduce sample size
learning_cycle:
  thresholds:
    min_sample_size: 50  # reduce from 100
```

## Learning Issues

### Issue: No Patterns Discovered

**Symptoms:**
```
Pattern synthesis complete: 0 patterns found
Recommendations: None
```

**Causes & Solutions:**

**1. Insufficient Data:**
```bash
# Check interaction count
sqlite3 data/voice_learning_warm.db "SELECT COUNT(*) FROM interactions;"

# Need at least 100 interactions
# Solution: Wait for more data or reduce threshold:
learning_cycle:
  thresholds:
    min_sample_size: 50
```

**2. Confidence Threshold Too High:**
```yaml
# Lower threshold
learning_cycle:
  thresholds:
    confidence_threshold: 0.75  # reduce from 0.85
```

**3. Data Too Homogeneous:**
- Need variety in commands
- Solution: Collect data from diverse users and scenarios

### Issue: Recommendations Not Applied

**Symptoms:**
```
Synthesis generated 10 recommendations
Implementation phase: 0 recommendations applied
```

**Causes & Solutions:**

**1. Safety Validation Failed:**
```bash
# Check logs for validation failures
grep "safety validation failed" logs/voice-learning/learning_loop_orchestrator.log

# Review recommendations:
# - Are they too risky?
# - Do they reduce existing accuracy?
```

**2. Priority Too Low:**
```yaml
# Only high-priority recommendations auto-applied
# Lower priority threshold:
learning_cycle:
  thresholds:
    auto_apply_priority: "medium"  # was "high"
```

**3. A/B Testing Blocked:**
```yaml
# Disable A/B testing for faster deployment:
learning_cycle:
  optimization:
    enable_ab_testing: false
```

### Issue: Frequent Rollbacks

**Symptoms:**
```
Validation alert: Regression detected
Rollback triggered: accuracy dropped 2%
Rollback rate: 15% (target: <5%)
```

**Causes & Solutions:**

**1. Insufficient Validation Period:**
```yaml
# Increase validation period before rollback
learning_cycle:
  validation:
    min_validation_hours: 24  # was 1
```

**2. Enable A/B Testing:**
```yaml
# Test changes on subset before full rollout
learning_cycle:
  optimization:
    enable_ab_testing: true
    ab_split_percent: 20  # test on 20% of traffic
```

**3. Lower Regression Threshold:**
```yaml
# Allow minor temporary regressions
learning_cycle:
  thresholds:
    regression_threshold: 0.03  # was 0.01 (1%)
```

## Agent Issues

### Issue: Agent Unhealthy

**Symptoms:**
```
Health check failed: agent_name
Status: unhealthy
Error: Connection timeout
```

**Solution:**
```bash
# Check if agent is running
ps aux | grep agent_name

# Check agent logs
tail -100 logs/voice-learning/agent_name.log

# Restart agent
pkill -f agent_name
python3 modules/voice-learning/agents/agent_name.py &

# Verify health
curl http://localhost:800X/health
```

### Issue: Agent Memory Leak

**Symptoms:**
```
Agent memory usage: 2GB (was 200MB)
Agent response time degraded
```

**Solution:**
```bash
# Restart affected agent
pkill -f agent_name
python3 modules/voice-learning/agents/agent_name.py &

# Monitor memory:
watch -n 5 'ps aux | grep agent_name'

# If leak persists:
# - Check for unclosed connections
# - Check for unbounded caches
# - Review recent code changes
```

### Issue: Message Queue Backlog

**Symptoms:**
```
Redis stream depth: 10,000 messages
Agents falling behind
Learning cycles delayed
```

**Solution:**
```bash
# Check stream lengths
redis-cli XLEN voice-learning:interactions
redis-cli XLEN voice-learning:analysis

# Increase consumer group size:
# Start additional agent instances

# Or increase batch processing:
learning_cycle:
  optimization:
    batch_size: 2000  # increase from 500

# Or reduce message retention:
redis-cli XTRIM voice-learning:interactions MAXLEN ~ 1000
```

## Integration Issues

### Issue: MCP Prompt Retrieval Failed

**Symptoms:**
```
Error: get_prompt failed for 'mia-voice-command-learning'
MCP server not responding
```

**Solution:**
```bash
# Check MCP server status
# (depends on your MCP server implementation)

# Verify prompts exist
ls -la prompts/mia-voice-*.json

# Test prompt retrieval manually
# (use your MCP CLI or API)

# Check network connectivity
ping mcp-server-host
```

### Issue: Agent Communication Failure

**Symptoms:**
```
Error: Failed to publish to voice-learning:synthesis
Agent coordination broken
Learning cycle stuck
```

**Solution:**
```bash
# Check Redis connectivity
redis-cli ping

# Check stream health
redis-cli XINFO STREAM voice-learning:synthesis

# Restart message bus
redis-cli SHUTDOWN
redis-server --daemonize yes

# Recreate streams
redis-cli XGROUP CREATE voice-learning:synthesis mia-agents $ MKSTREAM

# Restart agents
pkill -f "voice-learning/agents"
# Then restart each agent individually
```

## Validation Issues

### Issue: Validation Always Fails

**Symptoms:**
```
Validation: FAIL
Failed checks: 15/45
Status: System not operational
```

**Solution:**
```bash
# Run validation with verbose output
# (invoke voice-system-validator agent with verbose=true)

# Review failed checks one by one:
# - Configuration errors: Fix settings
# - Storage errors: Check paths and permissions
# - Agent errors: Check logs and restart
# - MCP errors: Verify prompts exist

# Fix each issue individually

# Re-validate after each fix
```

### Issue: False Positive Regression Alerts

**Symptoms:**
```
Validation alert: Regression detected
But: Manual review shows accuracy actually improved
```

**Solution:**
```yaml
# Increase validation sample size
learning_cycle:
  validation:
    min_sample_size: 500  # was 100

# Increase statistical significance threshold
learning_cycle:
  validation:
    significance_threshold: 0.99  # was 0.95

# Increase validation period
learning_cycle:
  validation:
    min_validation_hours: 48  # was 24
```

## Data Issues

### Issue: Storage Full

**Symptoms:**
```
Error: Disk space exhausted
Cannot write to cold archive
```

**Solution:**
```bash
# Check disk usage
df -h

# Clean old cold archive data
cd data/voice_learning_archive
find . -type f -mtime +730 -delete  # delete >2 years

# Reduce retention:
storage:
  warm_index:
    retention_days: 3  # reduce from 7
  cold_archive:
    retention_years: 1  # reduce from 2

# Or move archive to larger disk
```

### Issue: Database Corruption

**Symptoms:**
```
Error: SQLite database disk image is malformed
Warm index queries failing
```

**Solution:**
```bash
# Check database integrity
sqlite3 data/voice_learning_warm.db "PRAGMA integrity_check;"

# If corrupt, recover:
sqlite3 data/voice_learning_warm.db ".dump" | sqlite3 new_db.db
mv data/voice_learning_warm.db data/voice_learning_warm.db.corrupt
mv new_db.db data/voice_learning_warm.db

# Restart Context Manager agent
```

### Issue: Data Privacy Violation

**Symptoms:**
```
Audit: PII detected in archived data
User ID not anonymized after 90 days
```

**Solution:**
```bash
# Run anonymization script
python3 modules/voice-learning/scripts/anonymize_old_data.py

# Verify:
sqlite3 data/voice_learning_warm.db \
  "SELECT COUNT(*) FROM interactions WHERE timestamp < date('now', '-90 days') AND user_id NOT LIKE 'anon_%';"

# Should return 0

# Update configuration to enable automatic anonymization:
privacy:
  anonymization:
    user_id_after_days: 90
    auto_anonymize: true
```

## Getting Help

If these solutions don't resolve your issue:

1. **Check Documentation:**
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
   - [GETTING_STARTED.md](GETTING_STARTED.md) - Setup guide
   - `COMPLETE_VOICE_LEARNING_SYSTEM.md` - Master guide

2. **Review Logs:**
   ```bash
   tail -100 logs/voice-learning/*.log
   ```

3. **Run Full Validation:**
   ```
   User: "Run a full system validation with verbose output"
   ```

4. **Check Gap Analysis:**
   ```bash
   cat VOICE_COMMAND_INTELLIGENCE_ANALYSIS.json | jq '.missing_implementation'
   ```

5. **Report Issue:**
   - Include: Error message, logs, configuration, steps to reproduce
   - GitHub Issues: [MIA Repository]
```

**Step 4: Commit**

```bash
git add .claude/plugins/voice-learning/docs/
git commit -m "docs(plugin): add comprehensive plugin documentation

- ARCHITECTURE.md: Complete technical architecture
- GETTING_STARTED.md: Installation and quick start guide
- TROUBLESHOOTING.md: Common issues and solutions
- Covers deployment, performance, learning, agents, integration"
```

---

## Final Verification & Summary

**Step 1: Verify Complete Plugin Structure**

```bash
tree .claude/plugins/voice-learning -L 3 -I '__pycache__|*.pyc'
```

Expected output:
```
.claude/plugins/voice-learning
├── plugin.json
├── README.md
├── .gitignore
├── skills/
│   ├── voice-learning-workflow/
│   │   └── SKILL.md
│   └── learning-cycle-management/
│       └── SKILL.md
├── commands/
│   └── deploy-infrastructure.md
├── agents/
│   └── voice-system-validator/
│       ├── AGENT.md
│       └── agent.py
├── settings/
│   └── voice-learning.local.md.template
└── docs/
    ├── ARCHITECTURE.md
    ├── GETTING_STARTED.md
    └── TROUBLESHOOTING.md
```

**Step 2: Final Commit**

```bash
git add .
git commit -m "feat(plugin): complete voice-learning plugin v1.0.0

Complete Claude Code plugin for MIA's 3-layer voice command learning system.

Components:
- 2 skills: voice-learning-workflow, learning-cycle-management
- 1 command: deploy-infrastructure
- 1 agent: voice-system-validator
- Settings template with comprehensive configuration
- Complete documentation (architecture, getting started, troubleshooting)

Integration:
- Storage layer (hot/warm/cold cache)
- Learning layer (5 MCP prompts)
- Orchestration layer (6 agents, Redis Streams)

Ready for deployment and testing."
```

---

## Plan Complete

This plan provides:

✅ **Complete Plugin Structure**
- Plugin manifest with all components defined
- Comprehensive README with usage examples

✅ **2 Core Skills**
- `voice-learning-workflow` - Complete 4-phase workflow
- `learning-cycle-management` - 5-phase learning cycle

✅ **1 Deployment Command**
- `/deploy-infrastructure` - Full infrastructure deployment

✅ **1 Validation Agent**
- `voice-system-validator` - System validation and health checks

✅ **Configuration System**
- Settings template with YAML frontmatter
- Complete configuration documentation

✅ **Comprehensive Documentation**
- Architecture documentation
- Getting started guide
- Troubleshooting guide

**Next Steps After Implementation:**

1. **Test Plugin Loading:**
   - Verify Claude Code recognizes the plugin
   - Test skill invocation
   - Test command execution

2. **Deploy Infrastructure:**
   - Run `/deploy-infrastructure`
   - Verify all components deployed

3. **Run Validation:**
   - Invoke voice-system-validator agent
   - Verify all checks pass

4. **Test Learning Cycle:**
   - Generate test interactions
   - Trigger learning cycle
   - Verify improvements applied

5. **Complete Remaining Components:**
   - Task 8: Additional commands (run-learning-cycle, analyze-metrics, manage-agents)
   - Task 9: Additional agents (deployment-orchestrator, metrics-analyzer, health-checker)
   - Task 10: Pattern analysis skill
   - Task 11: Integration testing
   - Task 12: Performance optimization

**Implementation Timeline:**
- Tasks 1-7: 2-3 days (plugin foundation)
- Tasks 8-12: 3-4 days (additional components)
- Total: 5-7 days to complete plugin

**Success Criteria:**
- ✅ Plugin loads in Claude Code
- ✅ All skills invocable
- ✅ Commands execute successfully
- ✅ Agents respond to queries
- ✅ Settings properly loaded
- ✅ Documentation complete and accurate
