# User Journey: Start and Handoff an Agent Session

Date: 2026-06-30

## Persona

- **Who**: MIA technical operator.
- **Goal**: Start the right conversational agent and move a task through planning, evaluation, and execution.
- **Context**: Focused desktop session, sometimes mobile; may be switching languages.
- **Success metric**: Agent session starts or fails with a clear, recoverable reason.

## Journey Stages

### 1. Arrival

**Doing**: Opens `/agents/`.

**Thinking**: “Which agent should I use first?”

**Feeling**: Curious, slightly uncertain.

**Pain points found**:
- Cards described agent personalities but not workflow order.
- Loading/configuration state was not obvious.

**Implemented opportunity**:
- Added a recommended handoff panel: Orchestrator → Evaluator → Executor.
- Added loading and unavailable status copy.

### 2. Selection

**Doing**: Compares three cards, uses mouse or keyboard shortcuts.

**Thinking**: “I need planning first, then QA, then execution.”

**Feeling**: More confident.

**Pain points found**:
- Cards looked clickable but had no keyboard affordance.
- Focus states were weak.

**Implemented opportunity**:
- Added keyboard focus styling and card keyboard handling.
- Preserved button controls as first-class actions.

### 3. Start Voice Session

**Doing**: Clicks Talk or presses 1/2/3.

**Thinking**: “Is this connected or broken?”

**Feeling**: Needs fast feedback.

**Pain points found**:
- Missing config surfaced as a generic toast only after click.
- Connection errors could render unhelpful `[object Object]` text.

**Implemented opportunity**:
- Added clear unavailable state per agent.
- Formatted connection error details safely.
- Added live-region status announcements.

### 4. Switch Language / Theme

**Doing**: Uses EN/CS or theme button.

**Thinking**: “Did anything happen?”

**Feeling**: Previously confused.

**Pain points found**:
- i18n bootstrap called a missing `I18nLoader.init()` method.
- Markup used `data-i18n`, while the loader expects `data-i18n-path`.
- Theme toggle had no light theme variables.

**Implemented opportunity**:
- Fixed static-page i18n bootstrap.
- Added dynamic text refresh on language switch.
- Added light theme token overrides.

### 5. Handoff

**Doing**: Ends one session and starts another agent.

**Thinking**: “Now QA this / now execute it.”

**Feeling**: In control if workflow guidance is visible.

**Future opportunity**:
- Add explicit “Send summary to next agent” once conversation transcript/state is available.