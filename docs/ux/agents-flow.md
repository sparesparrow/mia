# Agent Team Portal — Figma-Ready Flow

Date: 2026-06-30

## Entry Point

User opens `/agents/` from the Team Portal or Home.

## Flow Steps

1. **Agent overview**
   - Header with Home, Team Portal, EN/CS, theme toggle.
   - Title: “Your Agent Team”.
   - Three agent cards: Orchestrator, Evaluator, Executor.
   - Each card shows avatar, role, availability status, Talk, and Focus.

2. **Recommended handoff panel**
   - Orchestrator: frames goal, plan, dependencies.
   - Evaluator: reviews risks, bugs, quality gates.
   - Executor: implements, tests, closes loop.

3. **Agent selection**
   - Mouse: click Focus or card body.
   - Keyboard: Tab to card/buttons; Enter/Space on card body focuses; 1/2/3 starts agent.
   - Status updates through an ARIA live region.

4. **Voice session start**
   - If agent ID exists: hide placeholder, mount ElevenLabs widget, Talk becomes End.
   - If signed URL fails: fallback to public agent ID for local development.
   - If agent ID missing: show unavailable state and localized error toast.

5. **Exit**
   - Click End or press Escape.
   - Widget unmounts, placeholder returns, status resets.

## Design Principles

1. **Workflow before personality**: Keep the sarcastic tone, but always explain what to do next.
2. **State is visible**: Loading, idle, unavailable, connected, and error states must be explicit.
3. **Fast recovery**: Missing config and connection failures should say what failed and avoid dead ends.
4. **Keyboard parity**: Every mouse path has a keyboard equivalent.
5. **Local-first resilience**: Page should still render and explain config issues when the agents API is down.

## Accessibility Requirements

- [x] Visible keyboard focus for links, buttons, and cards.
- [x] Header controls have labels and language pressed state.
- [x] Status and toast changes are announced with live regions.
- [x] Touch targets are at least 44px high for primary actions.
- [x] Motion respects `prefers-reduced-motion`.
- [x] Mobile keeps language/navigation controls available instead of hiding them.

## Future UX Improvements

- Add a “handoff summary” action after a session ends.
- Show agent configuration health from `/api/agents/status` in a collapsible diagnostics panel.
- Add transcript preview and “copy context to next agent”.
- Add a guided first-run setup for missing localStorage agent IDs in development.
- Add per-agent “best for” examples below each role.