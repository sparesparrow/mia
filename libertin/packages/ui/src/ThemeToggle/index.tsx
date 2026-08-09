'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * Day mode is the token default (`:root`); night mode is the `private` theme
 * already defined in `packages/theme/tokens.css`.
 */
export type ThemeName = 'default' | 'private';

/** localStorage key holding the member's explicit choice. */
export const THEME_STORAGE_KEY = 'libertin.theme';

const DARK_QUERY = '(prefers-color-scheme: dark)';

function isThemeName(value: string | null): value is ThemeName {
  return value === 'default' || value === 'private';
}

function readStoredTheme(storageKey: string): ThemeName | null {
  try {
    const raw = window.localStorage.getItem(storageKey);
    return isThemeName(raw) ? raw : null;
  } catch {
    // Storage blocked (private browsing) — fall back to the system preference.
    return null;
  }
}

function matchDark(): MediaQueryList | null {
  if (typeof window.matchMedia !== 'function') return null;
  try {
    return window.matchMedia(DARK_QUERY);
  } catch {
    return null;
  }
}

/**
 * Writes the theme onto `<html>`. Day mode removes the attribute rather than
 * setting a value, so the `:root` tokens apply unchanged.
 */
export function applyTheme(theme: ThemeName): void {
  const root = document.documentElement;
  if (theme === 'private') {
    root.setAttribute('data-theme', 'private');
  } else {
    root.removeAttribute('data-theme');
  }
}

export interface ThemeToggleProps {
  /** Override the persistence key (tests, Storybook). */
  storageKey?: string;
  /** Render the text label next to the switch. Icon-only still has an aria-label. */
  showLabel?: boolean | undefined;
  /** Notified after every explicit switch. */
  onThemeChange?: ((theme: ThemeName) => void) | undefined;
}

const srOnly: React.CSSProperties = {
  position: 'absolute',
  width: 1,
  height: 1,
  margin: -1,
  padding: 0,
  overflow: 'hidden',
  clip: 'rect(0 0 0 0)',
  whiteSpace: 'nowrap',
  border: 0,
};

export function ThemeToggle({
  storageKey = THEME_STORAGE_KEY,
  showLabel = true,
  onThemeChange,
}: ThemeToggleProps) {
  const { t } = useTranslation();
  // The server cannot know the stored choice, so the first paint must match the
  // server output ('default') and the real theme is resolved in the effect.
  const [theme, setTheme] = useState<ThemeName>('default');
  // Announced only after an explicit switch — never on mount, which would make
  // a screen reader read the theme out to a member who did not ask.
  const [status, setStatus] = useState('');

  useEffect(() => {
    const stored = readStoredTheme(storageKey);
    const resolved: ThemeName = stored ?? (matchDark()?.matches ? 'private' : 'default');
    setTheme(resolved);
    applyTheme(resolved);
  }, [storageKey]);

  // Keep following the system preference until the member chooses for themselves.
  useEffect(() => {
    const mql = matchDark();
    if (!mql || typeof mql.addEventListener !== 'function') return;

    const onChange = (event: MediaQueryListEvent) => {
      if (readStoredTheme(storageKey) !== null) return;
      const next: ThemeName = event.matches ? 'private' : 'default';
      setTheme(next);
      applyTheme(next);
    };

    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [storageKey]);

  const isNight = theme === 'private';

  const toggle = useCallback(() => {
    const next: ThemeName = isNight ? 'default' : 'private';
    setTheme(next);
    applyTheme(next);
    try {
      window.localStorage.setItem(storageKey, next);
    } catch {
      // Best effort — the switch still applies for this page view.
    }
    setStatus(next === 'private' ? t('theme.nightOn') : t('theme.dayOn'));
    onThemeChange?.(next);
  }, [isNight, onThemeChange, storageKey, t]);

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center' }}>
      <button
        type="button"
        onClick={toggle}
        aria-pressed={isNight}
        aria-label={t('theme.toggle')}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          backgroundColor: 'var(--color-surface)',
          color: 'var(--color-text)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-full)',
          padding: 'var(--space-1) var(--space-3)',
          font: 'inherit',
          fontSize: 'var(--text-sm)',
          fontWeight: 'var(--font-medium)',
          cursor: 'pointer',
        }}
      >
        <span
          aria-hidden="true"
          style={{
            position: 'relative',
            display: 'inline-block',
            width: 32,
            height: 18,
            flexShrink: 0,
            borderRadius: 'var(--radius-full)',
            backgroundColor: isNight ? 'var(--color-primary)' : 'var(--color-border)',
          }}
        >
          <span
            style={{
              position: 'absolute',
              top: 2,
              left: isNight ? 16 : 2,
              width: 14,
              height: 14,
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'var(--color-surface)',
              boxShadow: 'var(--shadow-sm)',
            }}
          />
        </span>
        {showLabel ? <span>{t('theme.toggle')}</span> : null}
      </button>
      <span aria-live="polite" style={srOnly}>
        {status}
      </span>
    </span>
  );
}
