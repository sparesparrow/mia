# Agent Team Portal — JTBD

Date: 2026-06-30

## Assumed Users

- **Primary**: Technical owner/operator using MIA agents to plan, review, and execute work.
- **Skill level**: Comfortable with AI tools, keyboard shortcuts, and debugging, but should not need to understand ElevenLabs configuration to start.
- **Context**: Desktop-first, often in a focused work session; mobile should remain usable for quick voice starts.
- **Accessibility baseline**: Keyboard navigation, visible focus, readable contrast, and screen-reader status announcements.

## Job Statement

When I need help moving a complex task from idea to implementation, I want to quickly pick the right agent or hand off between agents, so I can get a plan, QA review, and execution without losing context.

## Current Solution & Pain Points

- **Current**: Three voice-agent cards with Talk/Focus buttons.
- **Pain**: User must already know which agent to choose and what order to use them in.
- **Pain**: Failed agent configuration was not visible until clicking Talk.
- **Pain**: Language switcher existed but translations did not work because page markup and loader contract differed.
- **Pain**: Theme toggle changed only an icon because light-theme variables were missing.
- **Consequence**: Users lose trust before starting a voice session.

## Success Criteria

- User can identify the recommended handoff order in under 5 seconds.
- User can operate the page with keyboard only.
- User can switch EN/CS and see static plus dynamic UI text update.
- Missing agent IDs are visible as an availability state, not discovered only after failure.
- Theme toggle visibly changes the page.

## Subagent QA Handoff Model Used

1. **UX Analyst**: clarified the job and found missing handoff guidance.
2. **Accessibility Auditor**: checked keyboard, focus, live regions, touch target, and mobile navigation issues.
3. **Frontend Fixer**: implemented i18n, theme, state, and safe DOM fixes.
4. **Security Reviewer**: removed unsafe `innerHTML` toast/status insertion for dynamic messages.