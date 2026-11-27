# 0027. Vercel is the primary web address; GitHub Pages is a mirror

- Status: Accepted
- Date: 2026-11-26
- Requirements: REQ-WEB-002, REQ-WEB-004, REQ-WEB-005

## Context

`.github/workflows/publish-pages.yml` publishes the web site and the MkDocs documentation to the `gh-pages` branch.
GitHub Pages serves that branch at `https://sparesparrow.github.io/mia/`, and the Vercel project
`citadela-resort/mia-suzmatra` deploys the same branch at `https://mia-suzmatra.vercel.app/`. Both hosts serve
identical files, but canonical URLs, hreflang, Open Graph URLs, `robots.txt` and `sitemap.xml` named the GitHub
Pages host, so search engines treated the Vercel address as a duplicate. Only Vercel serves the site at a host root
(so `robots.txt` takes effect) and sends the security headers from the generated `vercel.json` (REQ-WEB-005).

## Decision

- `https://mia-suzmatra.vercel.app/` is the primary address. `SITE_URL` in `web/scripts/generatePages.js`, the
  homepage `<head>`, `mkdocs.yml` `site_url` and the tests use it.
- GitHub Pages stays as a mirror of the same `gh-pages` branch. It is not redirected to Vercel; its pages name the
  Vercel URL as canonical.
- Vercel keeps redirecting GitHub-Pages-style paths (`/mia/...`) to the root.

## Consequences

- Search engines consolidate both hosts on the Vercel URLs; the sitemap to submit is
  `https://mia-suzmatra.vercel.app/sitemap.xml`.
- If the Vercel project or domain changes, `SITE_URL`, the homepage `<head>`, `mkdocs.yml` and the ElevenLabs agent
  allowlist must change with it.
