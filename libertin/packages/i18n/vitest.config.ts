import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    name: 'i18n',
    environment: 'node',
    include: ['**/*.test.ts'],
    exclude: ['node_modules/**'],
  },
});
