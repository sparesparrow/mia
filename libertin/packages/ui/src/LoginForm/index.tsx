'use client';

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Input } from '../Input';
import { Button } from '../Button';

export interface LoginFormProps {
  onSubmit: (email: string, password: string) => void | Promise<void>;
  loading?: boolean | undefined;
  error?: string | undefined;
  forgotHref?: string;
  registerHref?: string;
}

export function LoginForm({
  onSubmit,
  loading = false,
  error,
  forgotHref = '#',
  registerHref = '#',
}: LoginFormProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void onSubmit(email, password);
      }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
        width: '100%',
        maxWidth: 400,
      }}
    >
      <h1
        style={{
          margin: 0,
          color: 'var(--color-primary)',
          fontSize: 'var(--text-3xl)',
          fontWeight: 700,
        }}
      >
        {t('auth.login.title')}
      </h1>

      <Input
        label={t('auth.login.email')}
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder={t('auth.login.emailPlaceholder')}
        required
      />
      <Input
        label={t('auth.login.password')}
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="••••••••"
        required
      />

      {error ? (
        <p role="alert" style={{ margin: 0, color: 'var(--color-error)', fontSize: 'var(--text-sm)' }}>
          {error}
        </p>
      ) : null}

      <Button
        type="submit"
        i18nKey="auth.login.submit"
        loading={loading}
        disabled={email.length === 0 || password.length === 0}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)', alignItems: 'center' }}>
        <a href={forgotHref} style={{ color: 'var(--color-primary-text)', fontSize: 'var(--text-sm)' }}>
          {t('auth.login.forgotPassword')}
        </a>
        <a href={registerHref} style={{ color: 'var(--color-primary-text)', fontSize: 'var(--text-sm)' }}>
          {t('auth.login.noAccount')}
        </a>
      </div>
    </form>
  );
}
