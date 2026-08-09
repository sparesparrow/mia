import { defineConfig } from 'vitest/config';

// Aggregate entry point so `pnpm vitest run` at the repo root executes every
// workspace suite in one process tree (used by CI). Per-package configs stay
// authoritative for environment and setup.
export default defineConfig({
  test: {
    projects: ['packages/ui', 'packages/i18n', 'packages/theme'],
  },
});
