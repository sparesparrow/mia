# MIA Web Pages

Static web surfaces for MIA. The primary address is <https://mia-suzmatra.vercel.app/>
(ADR-0027): canonical URLs, hreflang, Open Graph URLs, `robots.txt` and `sitemap.xml` all use
it. `.github/workflows/publish-pages.yml` publishes the site to the `gh-pages` branch, which
GitHub Pages serves as a mirror at <https://sparesparrow.github.io/mia/>; the Vercel project
`citadela-resort/mia-suzmatra` deploys the same branch (root directory `.`, no build step),
so every push to `gh-pages` by the workflow also redeploys Vercel. The generator writes
`dist/vercel.json`, which gives the Vercel copy its security headers (REQ-WEB-005): nosniff,
referrer and framing rules, and a report-only Content-Security-Policy with the hash of every
inline script. It also redirects `/mia/...` to the root, so the shared `404.html` links work
on Vercel without JavaScript. Rebuild after editing an inline script so its hash is updated;
GitHub Pages ignores the file. The audience landing pages and the
press kit are generated from shared templates. The gonzo homepage and a few
internal tools are maintained by hand.

## Site map

| Path | Audience | Source |
|---|---|---|
| `/` | general public, journalists (Czech "gonzo" manifesto), with the voice guides | `index.html`, hand-written |
| `/business/`, `/family/`, `/musicians/`, `/journalists/` | customers and B2B partners | generated: `template.html` + `i18n/<segment>.yaml` + `i18n/site.yaml` |
| `/en/` | the homepage in English | `en/index.html`, hand-written, copied into `dist/en/` by the generator |
| `/<segment>/en/` | the same pages in English | generated |
| `/press/`, `/press/en/` | press and marketing | generated: `press-template.html` + `i18n/site.yaml` |
| `/docs/` | developers, mechanics, testers | MkDocs (`mkdocs.yml`, `docs/`) |
| `/docs/for/{developers,mechanics,testers}/` | per-role entry pages | `docs/for/*.md` |
| `/developers/`, `/mechanics/`, `/testers/` | short aliases | generated redirects to `/docs/for/<role>/` |
| `/customers/<segment>.html` | old URLs | generated redirects to `/<segment>/` |
| any other missing path | | `404.html` redirects moved pages and lists the rest |
| `/robots.txt`, `/sitemap.xml` | search engines | generated; the sitemap lists every page in both languages |

Czech is the default language. Every generated page is rendered once per
language, so the language switch is a plain link and the pages need no runtime
i18n.

A segment page shows its use cases (`#scenarios`) first, then "what works today"
(`#today`), technology and the pilot call to action. A segment's YAML may carry a
`site:` block that overrides parts of `i18n/site.yaml` for that page only; the
journalists page (`gonzo.yaml`) uses it to say "what works today", technology
and the pilot text in the gonzo voice.

These are **not published**: `team/` (a mock status board), `agents/` (needs
private ElevenLabs agent config), `voice-chat.html` (needs a local backend),
`shared/formal-template/`, `templates/` and the gonzo monitor tooling.

## Voice guides on the homepage

The homepage embeds one ElevenLabs widget and three public agents. Holly is the
router: she says in a sentence what MIA is and hands the visitor to Rimmer (features,
software requirements, documentation, the pilot) or Kryten (architecture, source code,
protocols, safety design). The `#posadka` section also lets a visitor pick a guide
directly (REQ-WEB-003). This is separate from the unpublished `agents/` portal.

- The agent IDs sit in the inline script at the end of `index.html`. They are public
  by design: each agent only accepts the origins on its allowlist
  (`sparesparrow.github.io`, `mia-suzmatra.vercel.app`, and `localhost:8080` and
  `127.0.0.1:8080` for local previews) and has a daily conversation limit. Prompts, voices and the knowledge base live in the ElevenLabs
  workspace, not in this repository.
- Rimmer and Kryten share a fact sheet that follows the "what works today" rule
  below. Update that fact sheet in ElevenLabs when `i18n/site.yaml` changes.
- The rest of their knowledge is fetched from the public `main` branch and the
  published docs, and refreshed about weekly: Rimmer reads `spec/requirements/*.yaml`
  and the documentation guides; Kryten reads a fixed list of source files and the
  architecture, ADR and interface pages. A new source file or docs page is not picked
  up until it is added to that list in ElevenLabs.
- MIA runs without a cloud; the guides do not. The section says so, and the widget
  asks for consent before the first conversation.

## Content rules

- The product is called **MIA**. The old AI-SERVIS name only appears where the
  press kit explains the rename. Some images still have it in their pixels.
- No prices and no performance figures (such as "300% productivity") unless the
  requirement registry supports them (ADR-0010, REQ-WEB-002). Pages invite
  people to join the pilot instead.
- The "what works today" list in `i18n/site.yaml`, and any segment override of
  it, may only name behaviour whose requirement is `implemented_and_ci_tested`
  or better. Update it when evidence changes. Planned features belong in the
  use cases, not in this list.
- Images the site uses live in `assets/site/` as optimised JPEGs (made from the
  originals in `assets/<segment>/`, `assets/shared/` and `assets/dev/`).

## Layout

```
web/
  index.html                 gonzo homepage (root of the site, Czech)
  en/index.html              the same homepage in English (hand-maintained translation)
  404.html                   redirects moved pages, lists the rest
  template.html              audience page template ({{name}} placeholders)
  press-template.html        press kit template
  site.css                   shared components for generated pages
  scripts/
    generatePages.js         generator entry point (`npm run build`)
    build-smoke.js           smoke test (`npm test`)
  cypress/                   browser tests (`npm run e2e`, `npm run e2e:prod`)
  cypress.config.js          Cypress settings (baseUrl http://localhost:8080)
  i18n/
    site.yaml                shared site strings: what works today, nav, pilot, press kit
    business.yaml            fleet / commercial segment
    family.yaml              family safety segment
    musicians.yaml           mobile studio segment
    gonzo.yaml               journalists (gonzo) segment
    common.yaml              legacy shared strings and agents page strings
  customers/<segment>/       per-segment stylesheet (journalists also holds the
                             homepage's gonzo-styles.css, gonzo-app.js and music)
  assets/site/               images used by the published pages

  agents/, team/, voice-chat.{html,js}   internal tools, not published
  css/, js/, scripts/{app,i18n-loader}.js, styles.css, gonzo-styles.css,
  templates/, shared/                    legacy runtime and templates, not published
```

## Local workflow

```bash
cd web
npm ci             # js-yaml builds the pages; Cypress is a devDependency (set
                   # CYPRESS_INSTALL_BINARY=0 to skip its browser binary when not running e2e)
npm run build      # generate dist/
npm test           # rebuilds and runs scripts/build-smoke.js
npm run serve      # static preview of dist/ at http://localhost:8080
```

`npm test` fails if a page or language version is missing, a template
placeholder did not render, a page shows the old name, a price or a removed
percentage, a page does not link to every audience, a local asset is missing,
a redirect points to the wrong place, or the homepage loses its voice-guide markup.
It also fails if a page (homepage included) loses its skip link, its single `<main id="main">`,
its single `<h1>` or its Open Graph tags, if a homepage image below the hero is not lazy-loaded,
or if `robots.txt` or `sitemap.xml` is missing a page (REQ-WEB-004).
It also fails if `vercel.json` loses a security header or the hash of an inline script
(REQ-WEB-005), or if the hand-written `index.html` or `404.html` shows the old name, a price or a
removed percentage, stops linking to every audience page, or `vercel.json` loses the `/mia/`
redirect (REQ-WEB-002).

### Browser tests

`cypress/e2e/` holds Cypress tests for the assembled site: page structure, skip link and Open
Graph tags on every page, a 390 px phone width, local links, the language switch, the mobile
menu, the voice-guide switcher, the sitemap and WCAG AA text contrast over solid backgrounds
(`contrast.cy.js`; text over gradients and images is checked by eye). Third-party scripts and
fonts are stubbed, so no test starts a voice conversation. The publish-pages workflow runs them in the
`Browser Tests (Cypress)` job, and the deploy waits for it.

```bash
npm run build
rm -rf /tmp/mia-site && mkdir -p /tmp/mia-site/customers/journalists
cp -r dist/. /tmp/mia-site/ && cp index.html 404.html /tmp/mia-site/
cp customers/journalists/gonzo-styles.css customers/journalists/gonzo-app.js \
   customers/journalists/background-music.mp3 /tmp/mia-site/customers/journalists/
python3 -m http.server 8080 --bind 127.0.0.1 --directory /tmp/mia-site &
npm run e2e         # all local specs; prod-smoke.cy.js is skipped
npm run e2e:prod    # read-only smoke test against https://mia-suzmatra.vercel.app
```

`prod-smoke.cy.js` only sends GET requests and visits pages. It also runs against GitHub Pages
with `--config baseUrl=https://sparesparrow.github.io/mia`; the security-header and `/mia/`
redirect tests run on Vercel only.

To preview the whole site as published, copy the homepage next to `dist/` the way
the workflow's "Assemble static site" step does, and build the docs with
`mkdocs build --site-dir <site>/docs`.

## Known limitations

- The homepage is hand-written twice: Czech `index.html` and its English translation
  `en/index.html`. Change both in the same PR. `build-smoke.js` checks both for voice-guide
  markup, page structure (REQ-WEB-004), audience links, the language links between them and
  the forbidden name, prices and percentages (REQ-WEB-002); their other claims are reviewed by
  hand. The voice guides may still greet in Czech on the English page: their first message is set in ElevenLabs.
- Canonical URLs and the sitemap use the Vercel host (ADR-0027). The GitHub Pages mirror under
  `/mia/` serves the same files, so its pages also name Vercel as canonical; its `robots.txt` has no
  effect there (not at a host root). Submit `https://mia-suzmatra.vercel.app/sitemap.xml` to
  search engines.
- The voice guides are on the homepage only, and their widget script comes from
  `unpkg.com` unpinned, as ElevenLabs documents it.
- While one of the homepage's glitch effects runs, the widget moves with the page for
  the length of the effect, like the menu does: the effect puts a filter on `body`.
- `customers/journalists/background-music.mp3` (~3.2 MB, 80 kb/s stereo MP3, no cover art or tags) is
  published with the homepage. It is a gonzo brand asset; replace it only with product sign-off.
  `gonzo-app.js` starts it on load; where the browser blocks sound it starts on the first click, tap or key
  press. The 🎵/🔊 button pauses it and the choice is kept in `localStorage` (`mia-music`). Touching a voice
  guide pauses it and never starts it. `preload="none"` means nothing is downloaded until it actually plays.
  Re-encode from a source with
  `ffmpeg -i <src> -map 0:a:0 -vn -map_metadata -1 -c:a libmp3lame -b:a 80k -ac 2 -ar 44100 background-music.mp3`.
- `customers/journalists/index-gonzo.html` is an older copy of `index.html`
  that the gonzo monitor tooling (`monitor-gonzo.py`) still uses.
