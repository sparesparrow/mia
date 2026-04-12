---
description: "Use when working on static web pages, generated customer pages, voice-chat prototypes, or the web build pipeline under web/."
name: "Web Pages Guidance"
applyTo:
  - "web/**"
  - "scripts/build_variant.py"
---
# Web Pages Guidance

- Treat `web/` as mixed source and output. `web/dist/` is generated output; preferred sources are `web/template.html`, `web/scripts/generatePages.js`, `web/i18n/*.yaml`, `web/customers/<segment>/`, and standalone pages such as `web/index.html`, `web/voice-chat.html`, and `web/team/index.html`.
- Keep the current stack lightweight. The repo uses static HTML, CSS, and JavaScript plus `js-yaml`; do not introduce a framework build step unless the task explicitly requires one.
- After changing shared templates, i18n data, or generator logic, rebuild from the source layer:
  - `cd web && npm install`
  - `cd web && npm run build`
  - `cd web && node scripts/generatePages.js` for the direct generator path
- Preview over HTTP, not `file://`, because the runtime i18n loader uses `fetch()`.
  - `cd web/dist && python3 -m http.server 8080`
- Keep segment concerns separated:
  - shared copy in `web/i18n/common.yaml`
  - segment copy in `web/i18n/*.yaml`
  - segment styling in `web/customers/<segment>/`
- `web/voice-chat.html` and `web/voice-chat.js` are runtime-facing pages. If they change, verify their WebSocket and HTTP assumptions still match the FastAPI boundary and current `/ws` behavior.
- The journalists and gonzo surface is partly hand-authored and has its own monitor loop. If you change that area, also audit `web/GONZO-MONITOR-README.md`, `web/monitor-gonzo.py`, and `web/start-gonzo-monitor.sh`.
- Related docs: [web/README.md](../../web/README.md), [web/GONZO-MONITOR-README.md](../../web/GONZO-MONITOR-README.md), [README.md](../../README.md), and [../copilot-instructions.md](../copilot-instructions.md).