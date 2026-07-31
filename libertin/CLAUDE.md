# CLAUDE.md — Libertin

Working agreement for Claude Code. Read this fully before starting work.

## What we're building

A CZ/SK adult social community platform (rebrand: `swingerslife.cz` →
**Libertin**), delivered as **contract work**. Web app (Next.js + TS) and mobile
app (React Native + TS, Expo), plus the backend and infrastructure the platform
runs on.

Audience: adults (naturist / swingers / BDSM / shibari), CZ + EN primary.
Design driver: **discretion as a feature** — members risk real-world harm from
being outed, so privacy UX is a product requirement, not a compliance checkbox.

## Scope: the contract is the spec

The owner decided the delivery follows the signed technical specification — the
**whole system**, not only a client layer over the legacy API.

- `docs/backlog.yaml` — **single source of truth** for scope and status
  (15 epics, ~72 tasks, all traced to contract codes).
- `docs/requirements-traceability.md` — every contract requirement (A1–A4,
  B1–B14, C1–C13) mapped to current state.
- `docs/team-workflow.md` — how the agent team iterates without colliding.
- `.claude/agents/*.md` — the roles that do the work.
- `docs/adr/` — decisions, with honest trade-offs.

Never invent scope, never silently drop a contracted requirement. Blocking
decisions belong to the owner — record them under `decisions` in the backlog.

Hard acceptance gates from the contract: **UI response ≤ 1,5 s under peak load**
(C12.1), full **CS+EN** delivery (B13), **2FA with SMS + TOTP + passkey**
(B4.2), on-premise maximum (C2), containerised components (C3), **Ansible IaC**
(C11.2), GitLab CI/CD (C10), and handover to an **external operator** (C8).

## The rule that matters most for clients

**Treat the API contract as frozen, untrusted external input.**
- Capture the live API as an OpenAPI/HAR snapshot, commit it as
  `contracts/openapi.snapshot.yaml`.
- The typed client in `packages/api` is currently **hand-written** against the
  snapshot — there is no codegen yet (E11-T3). Agreement therefore rests on
  discipline plus the contract-check task, not on a generator.
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

## Blocking decisions (owner-owned)

Tracked as `decisions` in `docs/backlog.yaml`. Dependent tasks stay `blocked`
until resolved — do not work around them with an assumption:

- **D-001** Figma editor access — the hand-off defines the contracted UI scope
  (C1), and the account only holds a View seat, so design parity, token
  extraction and the real screen count are all unknown.
- **D-002** GitLab vs GitHub — contract mandates GitLab (C10).
- **D-003** Backend stack — extend the legacy Laravel or build fresh (C13 data
  migration depends on it).
- **D-004** Hosting / cloud provider (A1 vs C2 on-premise tension).
- **D-005** AI-assisted moderation — not in the contract, needs approval.

## Delivered so far

Phases 1–3 are done and verified: monorepo (pnpm + Turborepo), theme tokens
(web + native), i18n cs/en, UI components with Storybook, typed API client with
MSW mocks, mobile auth flow (login → verify → success → onboarding → feed), web
landing + login parity, age gate, security headers, robots/sitemap.

Everything boots offline against MSW mocks; `pnpm type-check` and `pnpm test`
pass, and `next build` succeeds.

## Definition of done

For a screen or component: renders from tokens + i18n keys (no hardcoded colour
or copy), has a Storybook entry, passes `pnpm type-check` and `next build`, and
works against MSW mocks offline.

For any task: verified with real command output, backlog status updated,
committed and pushed. **Never report done without running the verification.**
