# Agent Team Portal — QA Report

Date: 2026-06-30
Target: `http://localhost:8091/agents/`

## Scope

- Static page review of `web/agents/`.
- UX, accessibility, i18n, theme, and client-side robustness.
- Browser automation was not available in this session; validation was performed by source review and local page fetch attempt.

## Bugs Fixed

| ID | Severity | Finding | Fix |
|---|---:|---|---|
| AG-QA-001 | High | Language buttons did not translate the page because markup used `data-i18n` while the loader reads `data-i18n-path`. | Updated agent page markup and static i18n bootstrap. |
| AG-QA-002 | High | Page called non-existent `I18nLoader.init()`, causing a console error. | Replaced with supported `setLanguage()` + `translateDom()`. |
| AG-QA-003 | Medium | Theme toggle only changed the icon; no light theme variables existed. | Added `.light-theme` token overrides. |
| AG-QA-004 | Medium | Loading state class existed but had no visible styling. | Added shimmer/loading state and localized loading text. |
| AG-QA-005 | Medium | Agent config failure was discovered only after clicking Talk. | Added unavailable state per card when agent IDs are missing. |
| AG-QA-006 | Medium | Dynamic status/toast messages used `innerHTML`. | Replaced with safe DOM text insertion. |
| AG-QA-007 | Medium | Mobile CSS hid the whole nav, including language switching. | Changed mobile header to wrap controls instead of hiding them. |
| AG-QA-008 | Medium | Keyboard/focus affordances were incomplete. | Added focus-visible styles, card keyboard handling, live regions, and control labels. |
| AG-QA-009 | Low | `AbortSignal.timeout()` was used directly in config fetch. | Centralized fetch timeout helper with fallback. |

## UX Improvements Implemented

- Added a visible recommended handoff workflow: Orchestrator → Evaluator → Executor.
- Added localized dynamic statuses and button copy.
- Added active language button state and document `lang` updates.
- Improved mobile toast layout.
- Added reduced-motion handling.

## Remaining Recommendations

1. Add a proper `/api/agents/status` diagnostics panel for configuration and ElevenLabs health.
2. Add end-of-session transcript summary and explicit “handoff to Evaluator/Executor”.
3. Add Playwright smoke tests for EN/CS switching, theme toggling, missing config state, and keyboard shortcuts.
4. Consider moving inline static agent translations into a generated JSON payload to avoid duplication with `web/i18n/common.yaml`.