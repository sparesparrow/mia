import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    name: 'ui',
    // Component tests need a DOM. jsdom keeps the suite offline and headless.
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    // React Native primitives are not exercised here (they need a native
    // renderer); the web variants under src/ are what the web app ships.
    exclude: ['src/native/**'],
    restoreMocks: true,
  },
});
