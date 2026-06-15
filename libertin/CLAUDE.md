# CLAUDE.md — Libertin client

Context and working agreement for Claude Code. Read this fully before scaffolding.

## What we're building

Modernized **client layer** for an existing CZ/SK adult social community
(rebrand: `swingerslife.cz` → **Libertin**). We are NOT rewriting the backend.
We build a new **web app (Next.js + TS)** and **mobile app (React Native + TS,
Expo)** that talk to the existing API.

Audience: adults (naturist / swingers / BDSM / shibari), CZ + EN primary.
Design driver: **discretion as a feature** — privacy UX is a conversion lever,
not a compliance checkbox.

## The one rule that matters most

**The API is not ours. Treat its contract as untrusted external input.**
- Capture the live API as an OpenAPI/HAR snapshot, commit it as
  `contracts/openapi.snapshot.yaml`.
- Generate the typed client from that snapshot (`openapi-typescript`).
- CI fails loudly when the live shape drifts from the snapshot.
- This is the same pattern as freezing a FlatBuffers ICD — never call raw
  `fetch`; always go through the generated, snapshot-locked client.

Until credentials exist, run everything against **MSW mocks** derived from the
snapshot so the apps boot with zero backend.

## Repo shape (pnpm + Turborepo monorepo)

```
libertin/
  apps/
    web/            # Next.js 14 (app router), TS
    mobile/         # Expo (React Native), TS
  packages/
    ui/             # shared components (web + RN variants), Storybook
    theme/          # design tokens  -> from libertin_theme.ts / libertin_tokens.css
    i18n/           # i18next setup  -> from libertin_i18n.json (cs/en)
    api/            # generated client + MSW mocks, locked to the snapshot
  contracts/
    openapi.snapshot.yaml
```

## Assets already produced (drop these in, don't regenerate)

| Drop file here | From |
|---|---|
| `packages/theme/tokens.css` | `libertin_tokens.css` |
| `packages/theme/theme.ts` | `libertin_theme.ts` |
| `packages/i18n/locales.json` | `libertin_i18n.json` (cs+en, brand unified, typos fixed) |
| `packages/ui/icons/icon-bdsm.svg` | `icon-bdsm.svg` |
| `docs/fix-checklist.md` | `libertin_fix_checklist.md` |
| `docs/dev-orchestration.md` | `slc_dev_orchestration.md` |

Brand palette (already in tokens): primary `#F20B49`, bg `#FAFAF9`, dark surface
`#222222`, text `#1E1B1B`, info/blue `#0264FB`. Raspberry-as-text on white must
use `#C40A3C` (AA). An optional `private` night theme is included for the
authenticated area.

## Conventions

- TypeScript strict. No `any` in committed code.
- Components live in `packages/ui`; apps compose them, never duplicate.
- All user-facing strings go through i18next keys — no hardcoded copy. Source of
  truth is `packages/i18n/locales.json`.
- Use theme tokens, never raw hex, in components.
- Czech strings are corrected; do not reintroduce the old typos
  (Zapomenuté, Máte, svoji).
- Never hardcode PII (the old verify screen leaked a real email/phone — keep
  them as `{email}` / `{phone}` interpolations).

## Open decisions to confirm with the human before building far

1. **API access** — OpenAPI/Swagger available, or do we mock from the snapshot?
2. **Locales** — cs+en only (funded), or all 12 from the footer? i18n currently ships cs+en.
3. **MVP surface** — which screens first? Default order: Auth → Feed → Messages → Profile.

## Build order (phased)

**Phase 1 — skeleton (boots on mocks)**
- Scaffold the monorepo above. Wire theme + i18n + a Button/Input/Card/Avatar in `ui` with Storybook.
- Stand up `packages/api`: commit a starter `openapi.snapshot.yaml`, generate the client, wire MSW mocks.

**Phase 2 — auth flow (mobile first)**
- Screens from the Figma exports: Login → "Verify your email" → "Congratulations" (verified) → onboarding (3 steps) → Feed (mock).
- Use `verify.*`, `success.*`, `onboarding.*` keys.

**Phase 3 — web landing + core**
- Next.js landing (hero + Naturisté/Swingeři/BDSM/Šibari cards + footer) using `categories.*`, `home.*`, `footer.*`.
- Login parity with mobile.

**Phase 4 — live + CI**
- Swap MSW for the live client (credentials). GitLab CI stages: contract → lint → test → build → perf (k6 ≤1.5s, Lighthouse) → e2e. See `docs/dev-orchestration.md`.

## Definition of done per screen

Renders from tokens + i18n keys (no hardcoded color/copy), has a Storybook
entry, passes `tsc --noEmit` + eslint, and works against MSW mocks offline.
