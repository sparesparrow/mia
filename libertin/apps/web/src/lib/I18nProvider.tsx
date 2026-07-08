'use client';

import { useEffect, useState } from 'react';
import { i18n, initI18n, type Locale } from '@libertin/i18n';

export function I18nProvider({
  locale = 'cs',
  children,
}: {
  locale?: Locale;
  children: React.ReactNode;
}) {
  const [ready, setReady] = useState(i18n.isInitialized);

  useEffect(() => {
    let active = true;
    void Promise.resolve(initI18n(locale)).then(() => {
      if (active) setReady(true);
    });
    return () => {
      active = false;
    };
  }, [locale]);

  if (!ready) return null;
  return <>{children}</>;
}
