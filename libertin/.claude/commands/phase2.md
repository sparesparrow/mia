Proceed to Phase 2: auth flow, mobile-first (Expo).

Screens in order:
1. Login — `auth.login.*` keys, email + password fields, raspberry primary button
2. Verify email — `verify.*` keys, `{email}` interpolation (no hardcoded PII)
3. Congratulations (verified) — `success.*` keys
4. Onboarding step 1–3 — `onboarding.*` keys

Rules: tokens only (no raw hex), i18n keys only (no hardcoded copy), each screen
gets a Storybook story, passes tsc --noEmit. Stop after all 4 screens and show me
the tree + how to run on simulator.
