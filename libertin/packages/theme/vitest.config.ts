import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    name: 'theme',
    // Pure parsing + value comparison: no DOM, no network, no native runtime.
    environment: 'node',
    include: ['**/*.test.ts'],
    exclude: ['node_modules/**'],
  },
});
