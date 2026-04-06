# MIA Web Pages

This directory contains the static web surfaces for MIA and AI-SERVIS. Most public landing pages are generated from a shared template, while a few pages are standalone experiences maintained by hand.

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

Each generated landing page follows the same high-level structure:

- Language switcher
- Navigation bar
- Hero section with headline, subtitle, stats, and CTA buttons
- Feature grid
- Use-case section
- Pricing cards
- Technology section
- Final CTA block
- Footer

This keeps the information architecture consistent while allowing each segment to swap copy, pricing language, imagery, and styling.

## How the Generator Works

Build-time generation is handled by `scripts/generatePages.js`.

1. The script reads `template.html` as the shared page shell.
2. It selects a customer configuration with a namespace, default language, YAML file, and image directory.
3. It loads YAML translation data from `i18n/` using `js-yaml`.
4. `generatePageData()` normalizes customer-specific keys into one common view model.
5. `renderTemplate()` expands `{{variable}}`, `{{#each}}`, and `{{#if}}` blocks.
6. The generated HTML is written to `dist/<segment>.html`.
7. Shared runtime files are copied into `dist/`.
8. Customer-specific styles are copied into `dist/<segment>/styles.css`.
9. Optional per-segment assets are copied into `dist/<segment>/assets/` when those assets exist.

The result is a static site that can be hosted on GitHub Pages or any simple file server.

## Content Model

Generated pages are assembled from three layers of content:

- Shared structure in `template.html`
- Shared and segment-specific text in `i18n/common.yaml` and `i18n/<segment>.yaml`
- Segment-specific presentation in `customers/<segment>/styles.css`

That split matters when expanding the pages:

- Change `template.html` when every generated page needs a new section or layout change.
- Change `i18n/*.yaml` when the page needs more copy, translation coverage, or pricing text.
- Change `customers/<segment>/styles.css` when only one segment needs a different visual identity.

## Runtime Behavior

The generated pages are mostly static at load time, but two shared runtime scripts provide the interactive behavior:

- `scripts/app.js`: smooth scrolling, navbar state, mobile menu behavior, reveal animations, and the demo-request modal
- `scripts/i18n-loader.js`: loads YAML translations in the browser, switches language between Czech and English, and persists the selected language in `localStorage`

Important behavior notes:

- The primary copy is already rendered into the HTML during the build.
- JavaScript is mainly responsible for interaction polish and runtime language swapping.
- The demo form is currently UI-only. Submission is handled in-browser and logged rather than sent to a backend.

## Standalone Pages

Not every page in this directory comes from the shared generator.

- `index.html`: a hand-authored gonzo landing page with custom audio and a distinct journalists-focused visual style
- `voice-chat.html` and `voice-chat.js`: a standalone voice chat or monitoring UI prototype
- `team/index.html`: an internal team portal for architecture, modules, and status views
- `404.html`: redirect logic used for deployed site variants on static hosting

These standalone pages can diverge significantly from the generated landing pages in both tone and implementation.

## Relevant Layout

This is the generator-focused part of the directory structure:

```text
web/
|- template.html
|- scripts/
|  |- generatePages.js
|  |- app.js
|  `- i18n-loader.js
|- i18n/
|  |- common.yaml
|  |- business.yaml
|  |- family.yaml
|  |- musicians.yaml
|  `- journalists.yaml
|- customers/
|  |- business/
|  |- family/
|  |- musicians/
|  `- journalists/
|- assets/
`- dist/
```

And the wider web surface also includes:

- `index.html`
- `voice-chat.html`
- `team/`
- `404.html`

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

Then open:

- `/business.html`
- `/family.html`
- `/musicians.html`
- `/journalists.html`

Use a real HTTP server for preview. The i18n runtime loads YAML files with `fetch()`, which is often blocked or unreliable from `file://` URLs.

## When to Edit Which File

- Add or expand a shared section: `template.html`
- Change copy, labels, pricing text, or translations: `i18n/*.yaml`
- Change a segment's visual identity: `customers/<segment>/styles.css`
- Add a new segment: update `scripts/generatePages.js`, create a new YAML file, and add customer styles
- Build a one-off concept page: edit the standalone HTML, CSS, and JavaScript files directly

## Troubleshooting

- If a page still shows raw `{{...}}` markers, the template key is missing from the generated data model.
- If language switching fails, confirm the namespace YAML file exists in `i18n/` and is copied into `dist/i18n/`.
- If a page renders without styling, confirm the segment stylesheet exists under `customers/<segment>/`.
- If images or media are missing, confirm the segment asset directory exists and is copied into the generated output.
- If the page works in production but not locally, make sure you are previewing it through an HTTP server instead of opening the file directly.
