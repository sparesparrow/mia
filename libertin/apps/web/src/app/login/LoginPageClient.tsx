'use client';

import { useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { createClient } from '@libertin/api/client';
import { LoginForm } from '@libertin/ui';
import { I18nProvider } from '../../lib/I18nProvider';

// Matches the base URL the MSW handlers intercept.
const API_BASE = 'https://api.libertin.cz/v1';
const client = createClient(API_BASE);

function LoginInner() {
  const router = useRouter();
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);

  const handleSubmit = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      setError(undefined);
      try {
        await client.auth.login({ email, password });
        router.push('/');
      } catch {
        setError(t('common.error'));
      } finally {
        setLoading(false);
      }
    },
    [router, t],
  );

  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-6)',
      }}
    >
      <LoginForm onSubmit={handleSubmit} loading={loading} error={error} />
    </main>
  );
}

export function LoginPageClient() {
  return (
    <I18nProvider locale="cs">
      <LoginInner />
    </I18nProvider>
  );
}
