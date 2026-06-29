# MIA Web Pages

Static web surfaces for MIA. Customer segment landing pages are generated
from a shared template; standalone experiences (gonzo landing, voice chat,
booking sim, agents portal, team page, 404) are maintained by hand.

## Layout

```
web/
  template.html                shared HTML template for generated pages
  scripts/
    generatePages.js           generator entry point (`npm run build`)
    build-smoke.js             smoke test (`npm test`)
    app.js                     runtime UI helpers shipped to generated pages
    i18n-loader.js             runtime i18n loader shipped to generated pages
  i18n/
    common.yaml                shared strings (cs/en)
    business.yaml              fleet / commercial segment
    family.yaml                family safety segment
    musicians.yaml             mobile studio segment
    gonzo.yaml                 "journalists" gonzo paranoia segment
  customers/<segment>/         per-segment overrides (styles.css, etc.)
  assets/<segment>/            per-segment images and binaries

  index.html                   hand-maintained gonzo landing
  voice-chat.{html,js}         WebSocket voice-intercept terminal demo
  chatka-booking.html          hotel reception WebSocket booking sim
  agents/                      ElevenLabs convai agent portal
  team/                        team status board
  404.html                     redirect-aware 404

  styles.css                   copy of customers/journalists/gonzo-styles.css;
                               consumed by .github/workflows/publish-pages.yml
                               (do not delete without updating the workflow)
  gonzo-styles.css             same as above; kept for the publish workflow
  css/*.css                    fallback shards used by scripts/build_variant.py
  js/{app,i18n-loader}.js      smaller legacy runtime used by templates/ and
                               agents/index.html; do not merge with scripts/
                               versions without first fixing the agents page
```

## Generated landing pages

The generator emits one HTML file per segment into `dist/`:

- `business.html` &mdash; fleets, productivity, navigation, analytics
- `family.html` &mdash; safety, monitoring, family protection
- `musicians.html` &mdash; mobile studio, performance
- `journalists.html` &mdash; gonzo investigative tooling (uses
  `customers/journalists/gonzo-styles.css` instead of the default per-segment
  `styles.css`)

## Local workflow

```bash
cd web
npm install        # only js-yaml is required
npm run build      # generate dist/
npm test           # rebuilds and runs scripts/build-smoke.js
npm run serve      # static preview at http://localhost:8080
```

`npm test` exits non-zero if any expected output file is missing, if a
template placeholder failed to render, or if the duplicate-asset-copy bug
this README warns about regresses.

> Always preview through a real HTTP server. The runtime i18n layer fetches
> `./i18n/*.yaml` and most browsers block `fetch()` against `file://` URLs.

## i18n

Generated pages load `scripts/i18n-loader.js`, which fetches the YAML files
copied to `dist/i18n/`. When that fetch fails (CORS, offline, broken path)
the loader now installs a visible red banner instead of silently rendering
raw translation keys.

The standalone pages (`index.html`, `voice-chat.html`, `chatka-booking.html`,
`team/index.html`) are currently **not** i18n-enabled and ship with
hardcoded Czech/English text. Migrating them is tracked separately.

## chatka-booking.html

`chatka-booking.html` derives its WebSocket URL from `window.location` at
runtime. To point the page at a different backend without editing HTML:

- append `?ws=ws://demo.local:8432/ws` to the URL, or
- set `window.MIA_CHATKA_WS_URL` before the inline script runs.

The default falls back to the current host and port `8432` (matches the
local `python server.py` simulator).

## Known limitations

- `scripts/i18n-loader.js` includes a hand-rolled YAML parser that only
  understands 4-level nesting. Deeper structures in `i18n/*.yaml` are
  silently dropped at runtime.
- `index.html` and `customers/journalists/index-gonzo.html` reference S3
  images and a `background-music.mp3` checked in at ~3MB. These are gonzo
  brand assets; clean them up only with product sign-off.
- The generator's segment list and template fallback chains in
  `scripts/generatePages.js` are hardcoded. Adding a fifth segment still
  requires a code change.

