'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';

export interface AgeGateProps {
  title: string;
  body: string;
  confirmLabel: string;
  leaveLabel: string;
  /**
   * Name of the **session** cookie that records consent. A session cookie (no
   * Max-Age / Expires) is deliberate: a shared or family machine must not stay
   * unlocked after the browser closes.
   */
  cookieName?: string;
  /** Where the "leave" action navigates. */
  leaveHref?: string;
  /**
   * Called once consent has actually been persisted. The host uses this to ask
   * the server to re-render — the gated content is never in the initial HTML,
   * so revealing it is a server decision, not a client one.
   */
  onConfirmed?: (() => void) | undefined;
  /**
   * Copy shown when the browser refuses cookies. Supplied by the host from
   * i18n; the component never hardcodes user-facing text.
   */
  cookieNotice?: string | undefined;
}

const DEFAULT_COOKIE = 'libertin.age';

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Writes the consent cookie and reads it back. Returns false when the browser
 * refuses cookies (blocked by the user, an extension, or an embedding context),
 * so the caller can say so instead of pretending consent was recorded.
 */
function persistConsent(cookieName: string): boolean {
  try {
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    // No Max-Age and no Expires => session cookie, dropped when the browser
    // closes. See P7 in docs/privacy-review.md.
    document.cookie = `${cookieName}=1; Path=/; SameSite=Lax${secure}`;
    return document.cookie.split('; ').some((pair) => pair.startsWith(`${cookieName}=`));
  } catch {
    return false;
  }
}

export function AgeGate({
  title,
  body,
  confirmLabel,
  leaveLabel,
  cookieName = DEFAULT_COOKIE,
  leaveHref = 'https://www.google.com',
  onConfirmed,
  cookieNotice,
}: AgeGateProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [cookiesBlocked, setCookiesBlocked] = useState(false);

  // The gate is mounted only when the server decided consent is missing, so it
  // is open for its whole lifetime. Everything the `aria-modal` claim implies
  // is set up here and torn down on unmount.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;

    // 1. Lock background scroll — a modal that scrolls the page behind it is
    //    not modal, and here the page behind it is the thing being withheld.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // 2. Move focus in.
    const first = dialog.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? dialog).focus();

    // 3. Pull focus back if anything outside the dialog manages to take it
    //    (browser find-in-page, a stray autofocus, a portal from a host app).
    const onFocusIn = (event: FocusEvent) => {
      const target = event.target as Node | null;
      if (target && !dialog.contains(target)) {
        (dialog.querySelector<HTMLElement>(FOCUSABLE) ?? dialog).focus();
      }
    };
    document.addEventListener('focusin', onFocusIn);

    return () => {
      // Remove the guard *before* restoring focus, otherwise it would fight the
      // restore and yank focus back into a dialog that is going away.
      document.removeEventListener('focusin', onFocusIn);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, []);

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      // Deliberately swallowed. The usual modal contract says Escape closes the
      // dialog, but an age gate is not a dismissible dialog: closing it would
      // reveal adult content to someone who has not confirmed their age. The
      // only two exits are "confirm" and "leave", both of which are on screen.
      event.preventDefault();
      event.stopPropagation();
      return;
    }

    if (event.key !== 'Tab') return;

    const dialog = dialogRef.current;
    if (!dialog) return;

    const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE));
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }

    const first = focusable[0] as HTMLElement;
    const last = focusable[focusable.length - 1] as HTMLElement;
    const active = document.activeElement;

    if (event.shiftKey && (active === first || active === dialog)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }, []);

  const handleConfirm = () => {
    if (persistConsent(cookieName)) {
      setCookiesBlocked(false);
      onConfirmed?.();
      return;
    }
    // Cookies refused. We do not fall back to a long-lived client store — that
    // would grant permanent consent on a machine the visitor may share — and we
    // do not let the caller reveal the content either. We say what is wrong and
    // leave both exits usable.
    setCookiesBlocked(true);
  };

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="age-gate-title"
      aria-describedby="age-gate-body"
      tabIndex={-1}
      onKeyDown={handleKeyDown}
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
        <p
          id="age-gate-body"
          style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 'var(--text-base)' }}
        >
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
        <p
          role="status"
          style={{
            margin: 0,
            color: 'var(--color-text-muted)',
            fontSize: 'var(--text-sm)',
          }}
        >
          {cookiesBlocked ? cookieNotice : null}
        </p>
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
