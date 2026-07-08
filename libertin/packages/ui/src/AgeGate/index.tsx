'use client';

import React, { useEffect, useState } from 'react';

export interface AgeGateProps {
  title: string;
  body: string;
  confirmLabel: string;
  leaveLabel: string;
  /** localStorage key holding the consent flag. */
  storageKey?: string;
  /** Where the "leave" action navigates. */
  leaveHref?: string;
}

const DEFAULT_KEY = 'libertin.ageConfirmed';

export function AgeGate({
  title,
  body,
  confirmLabel,
  leaveLabel,
  storageKey = DEFAULT_KEY,
  leaveHref = 'https://www.google.com',
}: AgeGateProps) {
  // null = not yet known (SSR / first paint), avoids hydration mismatch.
  const [confirmed, setConfirmed] = useState<boolean | null>(null);

  useEffect(() => {
    try {
      setConfirmed(window.localStorage.getItem(storageKey) === '1');
    } catch {
      // Storage blocked (private mode) — show the gate each visit.
      setConfirmed(false);
    }
  }, [storageKey]);

  if (confirmed !== false) return null;

  const handleConfirm = () => {
    try {
      window.localStorage.setItem(storageKey, '1');
    } catch {
      // Best effort; still let the user in for this page view.
    }
    setConfirmed(true);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="age-gate-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--color-surface-dark)',
        padding: 'var(--space-6)',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--color-surface)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-8)',
          maxWidth: 440,
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
          textAlign: 'center',
        }}
      >
        <h2
          id="age-gate-title"
          style={{
            margin: 0,
            color: 'var(--color-text)',
            fontSize: 'var(--text-2xl)',
            fontWeight: 700,
          }}
        >
          {title}
        </h2>
        <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 'var(--text-base)' }}>
          {body}
        </p>
        <button
          type="button"
          onClick={handleConfirm}
          style={{
            backgroundColor: 'var(--color-primary)',
            color: 'var(--color-on-primary)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            padding: '12px 24px',
            fontSize: 'var(--text-base)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {confirmLabel}
        </button>
        <a
          href={leaveHref}
          style={{
            color: 'var(--color-text-muted)',
            fontSize: 'var(--text-sm)',
            textDecoration: 'underline',
          }}
        >
          {leaveLabel}
        </a>
      </div>
    </div>
  );
}
