# Agent Team Portal — Web UX Improvement Roadmap

Date: 2026-06-30
Target: `/agents/`

## Working Assumptions

- **Primary user**: technical operator / builder using AI agents to plan, review, and execute work.
- **Primary device**: desktop web, with mobile as a quick-start companion for voice sessions.
- **Main job**: choose the right agent, start a session, and hand context to the next agent without losing momentum.
- **Failure cost**: medium. A broken or unclear voice start erodes trust in the whole agent system.

## North Star UX

The page should feel less like a static gallery of agents and more like a **mission-control surface**:

1. User sees which agents are available.
2. User understands which agent to start with.
3. User starts voice or text confidently.
4. User can hand work from one agent to the next.
5. User can diagnose configuration problems without reading logs.

## Priority Backlog

### P0 — Trust and Operability

These improvements prevent failed starts and confusion.

1. **Agent health diagnostics panel**
   - Add a collapsible “System status” panel below the handoff panel.
   - Pull from `/api/agents/status`.
   - Show: API reachable, ElevenLabs API key configured, each agent ID configured, signed URL availability.
   - Use user-facing statuses: Ready, Missing config, Rate limited, API offline.

2. **Unavailable-state recovery actions**
   - If an agent is missing `agentId`, show a small action link: “Add local dev ID”.
   - In dev mode, open a modal that writes `agent_id_orchestrator`, `agent_id_evaluator`, or `agent_id_executor` to localStorage.
   - In production, show “Contact admin” or “Open deployment docs”.

3. **Connection state timeline**
   - Replace a single status line with a small timeline after clicking Talk:
     1. Loading config
     2. Requesting signed URL
     3. Starting ElevenLabs widget
     4. Connected / failed
   - This makes slow starts feel intentional instead of broken.

4. **Explicit session end confirmation**
   - When ending an active session, show “Session ended” and a next-step prompt:
     - “Review with Evaluator”
     - “Execute with Executor”
     - “Start over with Orchestrator”

### P1 — Handoff and Multi-Agent Workflow

These improvements turn three separate agents into a coherent team.

1. **Handoff summary card**
   - After a session ends, display a structured summary block:
     - Goal
     - Decisions
     - Open risks
     - Proposed next agent
   - Initially this can be manual/static until transcript capture exists.

2. **“Send to next agent” action**
   - Add primary CTAs based on active agent:
     - Orchestrator → “Send plan to Evaluator”
     - Evaluator → “Send QA notes to Executor”
     - Executor → “Send result back to Evaluator”
   - Even before automatic context passing exists, this teaches the workflow.

3. **Task mode selector**
   - Add a compact selector above the cards:
     - Plan a task
     - Review quality
     - Execute/fix
     - Diagnose issue
   - Selecting a mode highlights the recommended agent and changes helper copy.

4. **Agent comparison microcopy**
   - Add “Best for” bullets per card:
     - Orchestrator: ambiguous work, roadmaps, dependency planning.
     - Evaluator: QA, risk, architecture review, metrics.
     - Executor: implementation, bug fixing, deployment steps.

### P2 — Conversation Experience

These improvements help users stay oriented during and after voice use.

1. **Transcript preview area**
   - Reserve space below the widget for transcript events when available.
   - Show speaker labels and timestamps.
   - Add “Copy summary” and “Copy transcript” actions.

2. **Voice readiness checklist**
   - Before first voice start, show checks:
     - Microphone permission
     - Browser support
     - Agent configured
     - Network reachable
   - Collapse after the first successful session.

3. **Fallback text prompt**
   - If voice fails, offer a text prompt box: “Describe what you wanted to ask.”
   - This avoids a dead end and creates future compatibility with text agents.

4. **Session timer and rate-limit awareness**
   - Show elapsed session time.
   - If signed-url endpoint returns 429, show retry countdown.

### P3 — Visual Polish and Brand

These improvements make the interface feel more premium and less prototype-like.

1. **Card hierarchy refinement**
   - Make agent name and role easier to scan.
   - Move personality title below the practical “Best for” copy.
   - Keep color accents but reduce glow intensity in light mode.

2. **Mode-aware page title**
   - Change hero copy based on task mode:
     - “Plan with Orchestrator”
     - “Verify with Evaluator”
     - “Ship with Executor”

3. **Better empty state**
   - Current placeholder should become a starter guide:
     - “Start with Orchestrator if you are unsure.”
     - “Use Evaluator before deployment.”
     - “Use Executor when you know the fix.”

4. **Consistent icons**
   - Use distinct icons for Plan, Review, Execute, Health, Handoff.
   - Avoid using only color to distinguish agents.

## Proposed Page Structure

1. **Header**
   - Home / Team Portal / language / theme.

2. **Hero**
   - Title: “Your Agent Team”
   - Subtitle: short value proposition.
   - Optional task-mode selector.

3. **System status strip**
   - Small, dismissible or collapsible.
   - Shows whether the page is ready for voice sessions.

4. **Agent cards**
   - Availability state.
   - Practical role.
   - Best-for bullets.
   - Talk / Focus / Details.

5. **Handoff workflow**
   - Orchestrator → Evaluator → Executor.
   - Add contextual next-step CTA after any session.

6. **Conversation area**
   - Widget.
   - Connection timeline.
   - Transcript/summary area.

7. **Diagnostics drawer**
   - Raw endpoint status, agent IDs masked, signed URL test result.
   - Useful for the operator without exposing secrets.

## Suggested Component Inventory

- `AgentCard`
- `AgentStatusBadge`
- `AgentHandoffPanel`
- `TaskModeSelector`
- `SystemStatusStrip`
- `ConnectionTimeline`
- `SessionSummaryCard`
- `DiagnosticsDrawer`
- `DevAgentIdModal`
- `Toast`

## Analytics and Success Metrics

Track events locally or through the existing telemetry pipeline:

- `agents_page_loaded`
- `agents_config_loaded`
- `agents_config_failed`
- `agent_focus_clicked`
- `agent_talk_clicked`
- `agent_signed_url_success`
- `agent_signed_url_failed`
- `agent_widget_connected`
- `agent_widget_error`
- `agent_session_ended`
- `agent_handoff_clicked`

Key metrics:

- Time from page load to first successful connected session.
- Percentage of users who can identify the correct starting agent.
- Agent session start failure rate.
- Language switch usage.
- Handoff CTA usage.

## Accessibility Requirements for Next Iteration

- Keep all controls reachable by keyboard.
- Add a skip link to the agent cards or conversation panel.
- Ensure status badges include text, not color alone.
- Announce connection state timeline updates.
- Avoid auto-moving focus when toasts appear.
- Keep mobile buttons at least 44px high.
- Confirm light and dark contrast ratios after visual polish.

## QA Test Matrix

### Functional

- Page loads with API online.
- Page loads with API offline.
- Page loads with no agent IDs.
- Page loads with localStorage fallback IDs.
- Signed URL succeeds.
- Signed URL fails and public agent ID fallback is used.
- Signed URL returns 429 and retry copy is shown.

### Interaction

- Mouse click Talk starts a session.
- Clicking active Talk ends a session.
- `Esc` ends a session.
- `1`, `2`, `3` start correct agents.
- `T` toggles theme.
- EN/CS updates static and dynamic copy.

### Responsive

- Desktop: three cards in one row.
- Tablet: cards remain readable.
- Mobile: navigation remains available; cards stack; toasts fit viewport.

### Accessibility

- Keyboard-only full path works.
- Screen reader announces status changes.
- Reduced motion disables shimmer/pulse.
- Focus indicators are visible in light and dark themes.

## Subagent Handoff Plan

1. **UX Researcher**
   - Validate whether users naturally understand Orchestrator → Evaluator → Executor.
   - Interview operators about real failure/recovery workflows.

2. **Frontend Engineer**
   - Build diagnostics panel and task-mode selector.
   - Add endpoint-backed health states.

3. **Accessibility Reviewer**
   - Audit keyboard order, live regions, contrast, and mobile touch targets.

4. **QA Automation Engineer**
   - Add Playwright smoke tests for loading, i18n, theme, missing config, and keyboard shortcuts.

5. **Agent Platform Engineer**
   - Define transcript/summary payload shape for future handoff automation.

## Recommended Next Sprint

1. Build `SystemStatusStrip` from `/api/agents/status`.
2. Add task-mode selector and “Best for” card bullets.
3. Add connection timeline for Talk flow.
4. Add Playwright smoke tests for the existing fixed bugs.
5. Prototype manual `SessionSummaryCard` and next-agent CTA.