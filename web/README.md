# MIA Web Pages

This directory contains the static web surfaces for MIA. Most public landing pages are generated from a shared template, while a few pages are standalone experiences maintained by hand.

## What Lives Here

- Generated segment landing pages in `dist/`: `business.html`, `family.html`, `musicians.html`, and `journalists.html`
- A shared page generator driven by `template.html`, `scripts/generatePages.js`, and YAML content in `i18n/`
- Customer-specific presentation assets in `customers/<segment>/`
- Standalone pages such as `index.html`, `voice-chat.html`, `team/index.html`, and `404.html`

## Stack

- Package: `mia-web@1.0.0`
- Build dependency: `js-yaml@4.1.0`
- Output model: static HTML, CSS, and JavaScript
- Runtime services: Google Fonts, Font Awesome CDN, in-browser YAML loading for language switching

## Generated Landing Pages

The generator builds one shared page structure for multiple customer segments:

- `business.html`: business fleets, productivity, navigation, and analytics
- `family.html`: safety, monitoring, and family-oriented protection messaging
- `musicians.html`: mobile studio and performance workflows
- `journalists.html`: investigative and gonzo-themed messaging with a dedicated style treatment

## Local Workflow

Install and build the generated landing pages:

```bash
cd web
npm install
npm run build
```

Preview the generated output from a static server:

```bash
cd web/dist
python3 -m http.server 8080
```

Use a real HTTP server for preview. The i18n runtime loads YAML files with `fetch()`, which is often blocked or unreliable from `file://` URLs.
