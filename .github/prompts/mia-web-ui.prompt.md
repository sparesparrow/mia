---
mode: agent
description: "Web UI — dashboard, voice chat interface, i18n, customer segments"
---

# MIA Web UI Worker

You own `web/`. Browser-based dashboard and voice chatbot interface.

## Structure

| Asset | Purpose |
|-------|---------|
| `web/index.html` | Main dashboard entry |
| `web/voice-chat.html` | Voice chatbot WebSocket UI |
| `web/team/index.html` | Team/admin panel |
| `web/404.html` | Error page |
| `scripts/generatePages.js` | Template-based page generation |
| `template.html` | Base HTML template |
| `i18n/*.yaml` | Internationalization strings |
| `customers/<segment>/styles.css` | Per-segment theming |

## Stack

- Package: `mia-web@1.0.0`
- Build dep: `js-yaml@4.1.0`
- Generated pages from YAML + template pipeline
- WebSocket streaming to FastAPI `/ws` endpoint
- No heavy framework — vanilla JS + generated HTML

## Conventions

- Voice chat connects to `ws://{rpi_host}:8000/ws`
- i18n keys in YAML, rendered at build time by `generatePages.js`
- Customer segments get separate `styles.css` overrides
- Audio-reactive interfaces for voice chatbot visualization

## When working here

1. Run `node scripts/generatePages.js` after changing templates or i18n
2. Voice chat WebSocket messages follow same JSON shape as RPi API
3. Keep pages lightweight — this may run on low-power devices
4. Test across segments by switching `customers/<segment>/` styles
