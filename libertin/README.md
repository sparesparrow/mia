# Libertin

Modernized client layer for the `swingerslife.cz` → **Libertin** rebrand.
Next.js 14 web + Expo mobile, pnpm + Turborepo monorepo. See [CLAUDE.md](CLAUDE.md)
for the working agreement and [docs/live-audit.md](docs/live-audit.md) for the
audit of the legacy site this project replaces.

## Quickstart

```bash
pnpm install

# Storybook — all UI components + screens (web & native via react-native-web)
pnpm storybook                          # → http://localhost:6006

# Web (Next.js) — needs the MSW worker file once:
pnpm --filter=@libertin/web msw:init    # generates apps/web/public/mockServiceWorker.js
pnpm --filter=@libertin/web dev         # → http://localhost:3000

# Mobile (Expo)
pnpm --filter=@libertin/mobile start    # then i / a for simulator

# Type check everything
pnpm type-check
```

Everything boots offline against MSW mocks derived from
[`contracts/openapi.snapshot.yaml`](contracts/openapi.snapshot.yaml) — no
backend credentials needed. Never call `fetch` directly; always go through
`@libertin/api`.

## Workspace layout

| Path | What |
|---|---|
| `apps/web` | Next.js 14 (app router) — landing, login, security headers |
| `apps/mobile` | Expo / React Native — auth flow (login → verify → onboarding → feed) |
| `packages/ui` | Shared components, web + native variants, Storybook |
| `packages/theme` | Design tokens (`tokens.css` for web, `native.ts` for RN) |
| `packages/i18n` | i18next setup + `locales.json` (cs/en, source of truth for all copy) |
| `packages/api` | Typed client + MSW mocks, locked to the OpenAPI snapshot |
| `contracts/` | Frozen API contract — run `/contract-check` to detect drift |

## Conventions (enforced)

- All user-facing strings via i18n keys — no hardcoded copy, no PII.
- Theme tokens only — no raw hex in components.
- TypeScript strict; components live in `packages/ui`, apps compose.

Claude Code shortcuts: `/phase2`, `/contract-check`, `/audit-czech`, `/storybook`
(see `.claude/commands/`).
