import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import { initI18n, i18n } from '@libertin/i18n';

// Components render real translations, so the suite catches missing keys
// instead of asserting against hardcoded copy. Czech is the default locale.
await initI18n('cs');

beforeEach(async () => {
  if (i18n.language !== 'cs') {
    await i18n.changeLanguage('cs');
  }
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
});
