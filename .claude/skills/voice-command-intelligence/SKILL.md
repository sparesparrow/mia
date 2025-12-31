---
name: voice-command-intelligence
description: Design and optimize voice commands, handle speech recognition, execute smart actions with context awareness
tags: ["mia", "voice", "android", "raspberry-pi", "iot"]
---

# Voice Command Intelligence Skill

## Phase 1: Voice Interface Design
1. Analyze current commands:
   `list_prompts(tags=["mia", "voice-command"])`

2. Get design guidelines:
   `get_prompt("voice-command-design-principles", {
     deviceType: "mobile|raspberry-pi",
     userContext: "developer|homeowner",
     focusAreas: detected_usage_patterns
   })`

3. Evaluate command clarity:
   `get_prompt("voice-command-clarity-checklist", {
     commands: current_commands,
     userFeedback: collected_feedback
   })`

## Phase 2: Context-Aware Interpretation
1. When voice input received, query context:
   `get_prompt("mia-context-analyzer", {
     currentLocation: device_location,
     recentActions: action_history,
     deviceState: system_state,
     timeOfDay: current_time
   })`

2. Use context to interpret ambiguous commands:
   - "lights" could mean "turn on lights" or "show light status"
   - Context determines correct interpretation

3. Generate confident response:
   `get_prompt("voice-response-generator", {
     interpretation: chosen_meaning,
     confidence: confidence_score,
     context: extracted_context
   })`

## Phase 3: Action Execution
1. Execute interpreted command
2. Capture result
3. If successful, remember for future:
   - "That voice command worked well"
   - Add to successful patterns

4. If unclear or failed:
   - `create_prompt(name: "voice-command-failure-analysis-${cmdId}", ...)`

## Phase 4: Learning Loop
1. Collect voice interaction analytics
2. Identify commands that work well vs. those that confuse users
3. Update voice command prompts with improvements
4. When new command category discovered:
   ```
   create_prompt(
     name: "voice-command-pattern-${category}",
     content: command_pattern_guidelines,
     tags: ["mia", "voice-command", category]
   )
   ```

## Integration with Raspberry Pi
- Local processing for privacy
- Fallback to cloud when needed
- Continuous improvement based on local usage patterns
- Sharing successful patterns across devices via mcp-prompts