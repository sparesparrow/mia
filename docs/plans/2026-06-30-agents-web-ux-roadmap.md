# Agent Team Portal — Web UX Roadmap

Date: 2026-06-30
Target page: `/agents/`
Status: expanded design/QA plan for the web iteration currently implemented in `web/agents/`

## Executive Summary

The Agent Team page should evolve from a static “three cards and a voice widget” page into a small mission-control interface for multi-agent work. The strongest improvements are not purely visual; they are about trust, operational clarity, and handoff continuity.

The current web iteration already adds:

- agent system status strip
- diagnostics drawer
- task-mode selector
- practical “best for” bullets
- recommended agent highlighting
- explicit Orchestrator → Evaluator → Executor handoff panel
- connection timeline
- session summary / next-agent CTA
- EN/CS copy coverage
- keyboard/focus/accessibility hardening

The next improvements should focus on making the page useful when the backend is partially down, when users are unsure which agent to choose, and when a session needs to continue with another agent.

## Design Principles

### 1. State before style

Users need to know whether the system is usable before they click Talk. Show API, config, signed URL, and widget state explicitly.

### 2. Workflow before personality

The agent personas are memorable, but the page must first answer:

- Which agent should I use?
- What is this agent best at?
- What should happen after this session?

### 3. Recoverable failure

A failure should include:

- what failed
- whether local fallback is active
- what the user can do next

### 4. Bilingual parity

EN and CS must cover static labels, dynamic statuses, diagnostics, toasts, and next-step copy.

### 5. Keyboard and mobile parity

The page must support:

- mouse
- keyboard-only
- mobile/touch
- screen readers

## Recommended Information Architecture

### Header

Purpose: persistent navigation and global controls.

Contents:

- brand
- Team Portal link
- Home link
- EN/CS switch
- theme toggle

Future improvements:

- add a small “connected / offline” status in the header if this page becomes a dashboard entry point
- add a skip link to the agent cards for keyboard users

### Hero

Purpose: orient the user.

Current title: “Your Agent Team”

Future copy variants:

- default: “Your Agent Team”
- plan mode: “Plan with Orchestrator”
- review mode: “Verify with Evaluator”
- execute mode: “Ship with Executor”
- diagnose mode: “Diagnose before you fix”

### System status strip

Purpose: make operational readiness visible.

Current statuses:

- API online/offline/checking
- agent config ready/missing/loading
- diagnostics button

Future enhancements:

- rate-limit status
- ElevenLabs signed URL test
- webhook health
- last successful session timestamp
- “Retry health check” button

### Task mode selector

Purpose: help users choose the correct agent from intent rather than memorizing personas.

Modes:

1. Plan a task → Orchestrator
2. Review quality → Evaluator
3. Execute / fix → Executor
4. Diagnose issue → Evaluator first, then Executor

Future modes:

- Deploy / release
- Write docs
- Investigate logs
- Refactor safely
- Prepare handoff summary

### Agent cards

Purpose: show agent role, readiness, and quick start.

Current content:

- avatar
- name
- persona title
- role
- best-for bullets
- status line
- Talk / Focus buttons

Future improvements:

- add “Details” panel per agent
- show last used timestamp
- show average response latency if telemetry exists
- show “recommended because…” when a mode is selected
- add warning badge if an agent is configured via localStorage fallback

### Handoff panel

Purpose: teach the team workflow.

Current flow:

1. Orchestrator: frame goal, plan, dependencies
2. Evaluator: review risk, bugs, quality gates
3. Executor: implement, test, close loop

Future improvements:

- clickable handoff steps
- visual progress state after sessions
- “copy handoff prompt” for each next agent
- transcript-based summary once available

### Conversation panel

Purpose: start and monitor sessions.

Current features:

- placeholder instructions
- connection timeline
- ElevenLabs widget mount point
- session summary
- next-agent CTA

Future improvements:

- transcript preview
- manual note field
- copy last summary
- retry connection
- microphone readiness check
- clear session button

### Diagnostics drawer

Purpose: support local development and operator troubleshooting.

Current fields:

- API
- Orchestrator config
- Evaluator config
- Executor config

Future fields:

- active API base
- signed URL endpoint result
- rate-limit response
- masked agent IDs
- localStorage fallback status
- browser microphone permission
- widget script loaded

## Detailed Improvement Backlog

### P0 — Must-Have Reliability

#### Health retry button

Add a “Retry” action in diagnostics and/or status strip.

Acceptance criteria:

- clicking Retry calls `/api/agents/status`
- statuses update without page reload
- no duplicate retry timers are created

#### Config fallback disclosure

If the page uses `localStorage` agent IDs or public `agent-id` fallback, show a visible notice.

Acceptance criteria:

- signed URL failure triggers a non-blocking warning toast
- diagnostics shows “Public ID fallback active” for the session
- fallback copy is translated EN/CS

#### API offline empty state

When `/api/agents/*` is unavailable, show a concise operator message:

> Voice backend is offline. The page is still usable for review, but voice sessions require agent configuration.

Acceptance criteria:

- visible before clicking Talk
- does not hide agent cards
- links to diagnostics

### P1 — Handoff Continuity

#### Manual handoff summary

Until automatic transcript capture exists, provide a structured card users can fill or copy.

Fields:

- Goal
- Decisions
- Risks
- Next action
- Recommended next agent

Acceptance criteria:

- appears after session end
- can be copied to clipboard
- includes next-agent CTA

#### Handoff prompt templates

Add prewritten prompts:

- Orchestrator → Evaluator: “Review this plan for risks and missing tests…”
- Evaluator → Executor: “Implement the highest-priority fix from this QA review…”
- Executor → Evaluator: “Verify this implementation and list remaining gaps…”

Acceptance criteria:

- EN/CS labels
- template content can stay English if agents operate primarily in English, but UI labels must be translated
- copy action confirms success

#### Handoff progress indicator

Show which workflow stage is current.

States:

- Not started
- Planned
- Reviewed
- Executed
- Verified

Acceptance criteria:

- state changes after session end or manual user action
- does not imply automatic verification unless telemetry exists

### P2 — Conversation Experience

#### Microphone readiness check

Before starting voice:

- browser supports microphone APIs
- page can request permission
- widget script loaded
- agent ID configured

Acceptance criteria:

- no microphone request until user initiates
- clear error if permission denied
- translated copy

#### Text fallback

If voice cannot start, offer text handoff:

- “Copy prompt for Orchestrator”
- “Open text input” if text agent backend exists later

Acceptance criteria:

- no dead end on widget/script/network failure
- diagnostic status is preserved

#### Session timer

Show elapsed time during active conversation.

Acceptance criteria:

- starts when widget is mounted or connected
- stops when session ends
- resets between sessions

### P3 — Visual and Interaction Polish

#### Recommended badge localization

Current implementation uses `data-recommended`; keep it fully localized.

Acceptance criteria:

- EN: Recommended
- CS: Doporučeno
- updates immediately on language switch

#### Light mode tuning

Light mode should reduce glow and keep contrast.

Acceptance criteria:

- buttons meet contrast guidelines
- card borders remain visible
- focus ring is visible

#### Mobile layout refinement

Current layout stacks cards and wraps nav.

Future improvements:

- sticky “Talk” action inside active card
- diagnostics as accordion
- two-column connection timeline on small screens

Acceptance criteria:

- no horizontal overflow at 320px width
- primary actions remain 44px high
- diagnostics content is readable

## Copy Improvements

### Empty State

Current:

> Select an agent and click Talk to begin a voice session

Improved:

> Start with Orchestrator if the task is unclear. Use Evaluator to review risk. Use Executor when the next fix is known.

### API Offline

> Voice backend is offline. You can still review the workflow, but starting private voice sessions requires the agents API.

### Missing Agent ID

> This agent has no configured ElevenLabs ID. Add a local dev ID or start the agents API.

### Signed URL Fallback

> Signed URL unavailable; using public agent ID fallback for this session.

### End Session Summary

> Session ended. Suggested next step: review with Evaluator.

## Component-Level Acceptance Criteria

### `SystemStatusStrip`

- Shows API state and config state
- Uses text + color, not color alone
- Supports Retry
- Opens diagnostics
- Updates after language switch

### `TaskModeSelector`

- Uses `aria-pressed`
- One active mode at a time
- Updates recommended card
- Updates helper text
- Does not start sessions automatically

### `AgentCard`

- Has practical best-for bullets
- Shows loading/idle/unavailable/active state
- Talk button starts or ends session
- Focus button highlights only; it does not start voice
- Works with keyboard

### `ConnectionTimeline`

- Hidden until session start
- Shows config → signed URL → widget → connected
- Supports active/done/error states
- Reflows on mobile
- Auto-opens diagnostics on error

### `SessionSummaryCard`

- Hidden until session end
- Shows next recommended agent
- CTA starts the next agent
- CTA disables during async start to avoid double-click races

## QA Matrix

### Browser

- Chrome / Edge latest
- Firefox latest if widget supports it
- Mobile Chromium viewport

### Functional Cases

1. Static server only, no API
2. API online, no agent IDs
3. API online, all agent IDs configured
4. API online, signed URL fails
5. API online, signed URL succeeds
6. Widget script blocked
7. Microphone denied
8. LocalStorage fallback IDs present

### Interaction Cases

- click each mode
- click Focus on each card
- click Talk with missing config
- set dev ID and start session
- end session and click next-agent CTA
- switch language before/after session
- toggle theme before/after session
- open diagnostics in each state

### Accessibility Cases

- keyboard-only path to Talk
- screen reader announces status changes
- focus ring visible on buttons/cards
- `aria-pressed` correct for task modes and language buttons
- diagnostics button maintains `aria-expanded`
- no critical text exposed only through pseudo-elements

## Proposed Automated Tests

Use Playwright against the static server.

Recommended smoke tests:

1. `agents-page-loads.spec.ts`
   - title is correct
   - three cards render
   - status strip renders

2. `agents-i18n.spec.ts`
   - switch to CS
   - verify title, mode copy, card status, handoff copy
   - switch back to EN

3. `agents-theme.spec.ts`
   - click theme button
   - body has `.light-theme`
   - reload preserves theme

4. `agents-config-missing.spec.ts`
   - with no localStorage IDs, statuses become unavailable
   - clicking Talk shows error toast and timeline config error

5. `agents-dev-id-session.spec.ts`
   - inject localStorage agent ID
   - click Talk
   - timeline appears
   - fallback warning appears if signed URL 404s
   - click End
   - summary appears

6. `agents-diagnostics.spec.ts`
   - open diagnostics
   - verify API/config state text
   - verify `aria-expanded`

## Subagent Workflow for Continued Development

### UX subagent

Owns:

- user flow
- copy clarity
- mode selection model
- handoff design

Outputs:

- updated journey map
- final copy table
- acceptance criteria

### Frontend subagent

Owns:

- component implementation
- state management
- responsive CSS
- i18n integration

Outputs:

- page changes
- no syntax errors
- no console errors except expected backend 404s in static mode

### Accessibility subagent

Owns:

- keyboard flow
- ARIA
- color contrast
- mobile touch target audit

Outputs:

- accessibility checklist
- bug list with severity

### QA automation subagent

Owns:

- Playwright smoke suite
- test fixtures for API offline / mocked API online
- regression coverage for language/theme/session states

Outputs:

- test files
- CI command
- pass/fail summary

### Platform subagent

Owns:

- `/api/agents/status` contract
- signed URL security posture
- transcript/summary API shape
- local dev configuration rules

Outputs:

- API contract doc
- backend implementation tasks

## Implementation Sequence

### Sprint 1: Stabilize current prototype

- Add Playwright smoke tests
- Add Retry health check
- Add visible API offline empty state
- Add diagnostics details for localStorage fallback

### Sprint 2: Handoff continuity

- Add copyable handoff prompt templates
- Add editable manual summary fields
- Add handoff progress indicator

### Sprint 3: Voice readiness

- Add microphone readiness check
- Add widget script loaded check
- Add session timer
- Add retry connection CTA

### Sprint 4: Telemetry and polish

- Add local analytics events
- Add success metrics dashboard or log output
- Tune light/mobile visuals
- Add screenshot-based visual regression checks

## Definition of Done

The web portal iteration is done when:

- users can understand which agent to start with without external docs
- API/config failures are visible before Talk
- Talk flow has a visible timeline
- ending a session suggests the next agent
- EN/CS translation covers all visible copy
- keyboard-only operation works
- mobile layout has no horizontal overflow
- smoke tests cover load, i18n, theme, missing config, diagnostics, and local dev session flow
