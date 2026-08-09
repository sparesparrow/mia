import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgeGate } from './index';

const COOKIE_NAME = 'libertin.age';

const labels = {
  title: 'Je vám 18 nebo více let?',
  body: 'Tento web obsahuje obsah určený výhradně dospělým.',
  confirmLabel: 'Je mi 18+, vstoupit',
  leaveLabel: 'Opustit web',
};

function clearCookies() {
  for (const pair of document.cookie.split(';')) {
    const name = pair.split('=')[0]?.trim();
    if (name) document.cookie = `${name}=; Path=/; Max-Age=0`;
  }
}

/** Simulates a browser that refuses cookies. Returns the restore function. */
function blockCookies() {
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    get: () => '',
    set: () => undefined,
  });
  return () => {
    Reflect.deleteProperty(document, 'cookie');
  };
}

describe('AgeGate', () => {
  beforeEach(() => {
    clearCookies();
  });

  it('renders the gate it was mounted for', () => {
    render(<AgeGate {...labels} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: labels.title })).toBeInTheDocument();
  });

  it('marks itself as a modal dialog labelled and described by its own content', () => {
    render(<AgeGate {...labels} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute(
      'aria-labelledby',
      screen.getByRole('heading', { name: labels.title }).id,
    );
    expect(document.getElementById(dialog.getAttribute('aria-describedby') ?? '')).toHaveTextContent(
      labels.body,
    );
  });

  it('moves focus into the dialog on open and restores it on close', () => {
    const opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();
    expect(document.activeElement).toBe(opener);

    const { unmount } = render(<AgeGate {...labels} />);
    expect(screen.getByRole('button', { name: labels.confirmLabel })).toHaveFocus();

    unmount();
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });

  it('locks background scroll while open and restores it on close', () => {
    document.body.style.overflow = 'auto';
    const { unmount } = render(<AgeGate {...labels} />);
    expect(document.body.style.overflow).toBe('hidden');

    unmount();
    expect(document.body.style.overflow).toBe('auto');
  });

  it('keeps Tab inside the dialog in both directions', async () => {
    const user = userEvent.setup();
    render(<AgeGate {...labels} />);
    const confirm = screen.getByRole('button', { name: labels.confirmLabel });
    const leave = screen.getByRole('link', { name: labels.leaveLabel });

    expect(confirm).toHaveFocus();
    await user.tab();
    expect(leave).toHaveFocus();
    // Last element -> wraps back to the first instead of escaping to the page.
    await user.tab();
    expect(confirm).toHaveFocus();
    // And backwards from the first element.
    await user.tab({ shift: true });
    expect(leave).toHaveFocus();
  });

  it('pulls focus back when something outside the dialog steals it', () => {
    render(<AgeGate {...labels} />);
    const outside = document.createElement('button');
    document.body.appendChild(outside);

    outside.focus();

    expect(screen.getByRole('button', { name: labels.confirmLabel })).toHaveFocus();
    outside.remove();
  });

  it('cannot be dismissed with Escape', async () => {
    const user = userEvent.setup();
    const onConfirmed = vi.fn();
    render(<AgeGate {...labels} onConfirmed={onConfirmed} />);

    await user.keyboard('{Escape}');

    // An age gate is not a dismissible dialog: Escape must not reveal anything.
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(onConfirmed).not.toHaveBeenCalled();
    expect(document.cookie).not.toContain(COOKIE_NAME);
  });

  it('records consent in a session cookie and hands the decision back to the host', async () => {
    const user = userEvent.setup();
    const onConfirmed = vi.fn();
    render(<AgeGate {...labels} onConfirmed={onConfirmed} />);

    await user.click(screen.getByRole('button', { name: labels.confirmLabel }));

    expect(onConfirmed).toHaveBeenCalledTimes(1);
    expect(document.cookie).toContain(`${COOKIE_NAME}=1`);
    // The gate stays mounted: only the server may reveal the content, and it
    // does so by re-rendering without this component.
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('writes no expiry, so consent dies with the browser session', async () => {
    const user = userEvent.setup();
    const written: string[] = [];
    const original = Object.getOwnPropertyDescriptor(
      Object.getPrototypeOf(document) as object,
      'cookie',
    );
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      get: (): string => (original?.get?.call(document) as string) ?? '',
      set: (value: string) => {
        written.push(value);
        original?.set?.call(document, value);
      },
    });

    render(<AgeGate {...labels} />);
    await user.click(screen.getByRole('button', { name: labels.confirmLabel }));
    Reflect.deleteProperty(document, 'cookie');

    const write = written.find((entry) => entry.startsWith(`${COOKIE_NAME}=`));
    expect(write).toBeDefined();
    // A persistent cookie would keep a shared or family machine unlocked for
    // as long as it lives; consent must not outlive the browser session.
    expect(write).not.toMatch(/max-age|expires/i);
    expect(write).toContain('SameSite=Lax');
    expect(write).toContain('Path=/');
  });

  it('honours a custom cookie name', async () => {
    const user = userEvent.setup();
    render(<AgeGate {...labels} cookieName="libertin.testGate" />);

    await user.click(screen.getByRole('button', { name: labels.confirmLabel }));

    expect(document.cookie).toContain('libertin.testGate=1');
    expect(document.cookie).not.toContain(`${COOKIE_NAME}=`);
  });

  it('does not fake consent when the browser refuses cookies', async () => {
    const user = userEvent.setup();
    const onConfirmed = vi.fn();
    const restore = blockCookies();

    render(
      <AgeGate {...labels} onConfirmed={onConfirmed} cookieNotice="Povolte prosím cookies." />,
    );
    await user.click(screen.getByRole('button', { name: labels.confirmLabel }));

    // No consent was recorded, so the host is not told to reveal anything…
    expect(onConfirmed).not.toHaveBeenCalled();
    // …and nothing long-lived is written behind the visitor's back.
    expect(window.localStorage.length).toBe(0);
    // …but the visitor is told why, rather than clicking a dead button.
    expect(screen.getByRole('status')).toHaveTextContent('Povolte prosím cookies.');
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    restore();
  });

  it('offers an exit route away from the site', () => {
    render(<AgeGate {...labels} leaveHref="https://example.org" />);
    expect(screen.getByRole('link', { name: labels.leaveLabel })).toHaveAttribute(
      'href',
      'https://example.org',
    );
  });
});
