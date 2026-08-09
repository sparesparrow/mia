import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { i18n } from '@libertin/i18n';
import { THEME_STORAGE_KEY, ThemeToggle, applyTheme } from './index';

const toggle = () => screen.getByRole('button', { name: 'Noční režim' });
const themeAttr = () => document.documentElement.getAttribute('data-theme');

type Listener = (event: MediaQueryListEvent) => void;

/**
 * jsdom ships no matchMedia, which is exactly the "no system preference
 * available" case. Tests that need one install this controllable stub.
 */
function stubPrefersDark(matches: boolean) {
  const listeners = new Set<Listener>();
  const mql = {
    matches,
    media: '(prefers-color-scheme: dark)',
    addEventListener: (_: 'change', listener: Listener) => listeners.add(listener),
    removeEventListener: (_: 'change', listener: Listener) => listeners.delete(listener),
  };
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn(() => mql),
  });
  return {
    emit(next: boolean) {
      mql.matches = next;
      for (const listener of listeners) listener({ matches: next } as MediaQueryListEvent);
    },
    listenerCount: () => listeners.size,
  };
}

afterEach(() => {
  document.documentElement.removeAttribute('data-theme');
  Reflect.deleteProperty(window, 'matchMedia');
});

describe('ThemeToggle', () => {
  it('renders a labelled toggle button from i18n, not hardcoded copy', () => {
    render(<ThemeToggle />);
    expect(toggle()).toBeInTheDocument();
  });

  it('translates the label when the locale changes', async () => {
    await i18n.changeLanguage('en');
    render(<ThemeToggle />);
    expect(screen.getByRole('button', { name: 'Night mode' })).toBeInTheDocument();

    // Back to the suite default; the re-render it triggers must be awaited.
    await act(async () => {
      await i18n.changeLanguage('cs');
    });
    expect(toggle()).toBeInTheDocument();
  });

  it('starts unpressed in day mode and sets no data-theme attribute', () => {
    render(<ThemeToggle />);
    expect(toggle()).toHaveAttribute('aria-pressed', 'false');
    expect(themeAttr()).toBeNull();
  });

  it('switches <html> to the private theme and reports pressed', async () => {
    render(<ThemeToggle />);
    await userEvent.click(toggle());

    expect(themeAttr()).toBe('private');
    expect(screen.getByRole('button', { name: 'Noční režim', pressed: true })).toBeInTheDocument();
  });

  it('switches back to the default theme by removing the attribute', async () => {
    render(<ThemeToggle />);
    await userEvent.click(toggle());
    await userEvent.click(toggle());

    expect(themeAttr()).toBeNull();
    expect(toggle()).toHaveAttribute('aria-pressed', 'false');
  });

  it('persists the choice so the next visit keeps it', async () => {
    render(<ThemeToggle />);
    await userEvent.click(toggle());
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('private');

    await userEvent.click(toggle());
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('default');
  });

  it('restores a stored night choice on mount', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'private');
    render(<ThemeToggle />);

    expect(themeAttr()).toBe('private');
    expect(toggle()).toHaveAttribute('aria-pressed', 'true');
  });

  it('ignores a corrupted stored value instead of applying it', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'neon');
    render(<ThemeToggle />);

    expect(themeAttr()).toBeNull();
    expect(toggle()).toHaveAttribute('aria-pressed', 'false');
  });

  it('honours a custom storage key and leaves the default one alone', async () => {
    render(<ThemeToggle storageKey="libertin.testTheme" />);
    await userEvent.click(toggle());

    expect(window.localStorage.getItem('libertin.testTheme')).toBe('private');
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it('follows prefers-color-scheme: dark when nothing is stored', () => {
    stubPrefersDark(true);
    render(<ThemeToggle />);

    expect(themeAttr()).toBe('private');
    expect(toggle()).toHaveAttribute('aria-pressed', 'true');
    // The system preference alone is not a member decision, so nothing is written.
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it('lets an explicit choice override a dark system preference', async () => {
    stubPrefersDark(true);
    render(<ThemeToggle />);
    await userEvent.click(toggle());

    expect(themeAttr()).toBeNull();
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('default');
  });

  it('reacts to a system preference change while nothing is stored', () => {
    const media = stubPrefersDark(false);
    render(<ThemeToggle />);
    expect(themeAttr()).toBeNull();

    act(() => media.emit(true));
    expect(themeAttr()).toBe('private');
  });

  it('stops following the system once the member has chosen', async () => {
    const media = stubPrefersDark(false);
    render(<ThemeToggle />);
    await userEvent.click(toggle());
    expect(themeAttr()).toBe('private');

    act(() => media.emit(true));
    act(() => media.emit(false));
    expect(themeAttr()).toBe('private');
  });

  it('detaches the system listener on unmount', () => {
    const media = stubPrefersDark(false);
    const { unmount } = render(<ThemeToggle />);
    expect(media.listenerCount()).toBe(1);

    unmount();
    expect(media.listenerCount()).toBe(0);
  });

  it('is operable from the keyboard alone', async () => {
    render(<ThemeToggle />);
    await userEvent.tab();
    expect(toggle()).toHaveFocus();

    await userEvent.keyboard('{Enter}');
    expect(themeAttr()).toBe('private');

    await userEvent.keyboard(' ');
    expect(themeAttr()).toBeNull();
  });

  it('announces the new mode politely, and stays silent until asked', async () => {
    const { container } = render(<ThemeToggle />);
    const live = container.querySelector('[aria-live="polite"]');
    expect(live).not.toBeNull();
    expect(live?.textContent).toBe('');

    await userEvent.click(toggle());
    expect(live).toHaveTextContent('Noční režim zapnutý');

    await userEvent.click(toggle());
    expect(live).toHaveTextContent('Denní režim zapnutý');
  });

  it('keeps a label for screen readers when the text label is hidden', () => {
    render(<ThemeToggle showLabel={false} />);
    const button = toggle();
    expect(button).toHaveAttribute('aria-label', 'Noční režim');
    expect(button.textContent).toBe('');
  });

  it('notifies the host of every explicit switch', async () => {
    const onThemeChange = vi.fn();
    render(<ThemeToggle onThemeChange={onThemeChange} />);

    await userEvent.click(toggle());
    await userEvent.click(toggle());
    expect(onThemeChange.mock.calls).toEqual([['private'], ['default']]);
  });

  it('still switches for this page view when storage is blocked', async () => {
    const setItem = vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    const getItem = vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });

    render(<ThemeToggle />);
    await userEvent.click(toggle());
    expect(themeAttr()).toBe('private');

    setItem.mockRestore();
    getItem.mockRestore();
  });

  it('exposes applyTheme so a host can paint the theme before hydration', () => {
    applyTheme('private');
    expect(themeAttr()).toBe('private');
    applyTheme('default');
    expect(themeAttr()).toBeNull();
  });
});
