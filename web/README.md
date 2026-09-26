# MIA Web Pages

Static web surfaces for MIA, published to <https://sparesparrow.github.io/mia/>
by `.github/workflows/publish-pages.yml`. The audience landing pages and the
press kit are generated from shared templates. The gonzo homepage and a few
internal tools are maintained by hand.

## Site map

| Path | Audience | Source |
|---|---|---|
| `/` | general public, journalists (Czech "gonzo" manifesto) | `index.html`, hand-written |
| `/business/`, `/family/`, `/musicians/`, `/journalists/` | customers and B2B partners | generated: `template.html` + `i18n/<segment>.yaml` + `i18n/site.yaml` |
| `/<segment>/en/` | the same pages in English | generated |
| `/press/`, `/press/en/` | press and marketing | generated: `press-template.html` + `i18n/site.yaml` |
| `/docs/` | developers, mechanics, testers | MkDocs (`mkdocs.yml`, `docs/`) |
| `/docs/for/{developers,mechanics,testers}/` | per-role entry pages | `docs/for/*.md` |
| `/developers/`, `/mechanics/`, `/testers/` | short aliases | generated redirects to `/docs/for/<role>/` |
| `/customers/<segment>.html` | old URLs | generated redirects to `/<segment>/` |
| any other missing path | | `404.html` redirects moved pages and lists the rest |

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
  index.html                 gonzo homepage (root of the site)
  404.html                   redirects moved pages, lists the rest
  template.html              audience page template ({{name}} placeholders)
  press-template.html        press kit template
  site.css                   shared components for generated pages
  scripts/
    generatePages.js         generator entry point (`npm run build`)
    build-smoke.js           smoke test (`npm test`)
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
npm ci             # only js-yaml is required
npm run build      # generate dist/
npm test           # rebuilds and runs scripts/build-smoke.js
npm run serve      # static preview of dist/ at http://localhost:8080
```

`npm test` fails if a page or language version is missing, a template
placeholder did not render, a page shows the old name, a price or a removed
percentage, a page does not link to every audience, a local asset is missing, or
a redirect points to the wrong place.

To preview the whole site as published, copy the homepage next to `dist/` the way
the workflow's "Assemble static site" step does, and build the docs with
`mkdocs build --site-dir <site>/docs`.

## Known limitations

- The homepage (`index.html`) is hand-written Czech. Its English link goes to
  `/journalists/en/`, and `build-smoke.js` does not check it.
- `customers/journalists/background-music.mp3` (~7.8 MB) is published with the
  homepage. It is not preloaded and only plays from the 🎵 button. It is a gonzo brand asset; clean it
  up only with product sign-off.
- `customers/journalists/index-gonzo.html` is an older copy of `index.html`
  that the gonzo monitor tooling (`monitor-gonzo.py`) still uses.
