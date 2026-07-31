import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgeGate } from './index';

const STORAGE_KEY = 'libertin.ageConfirmed';

const labels = {
  title: 'Je vám 18 nebo více let?',
  body: 'Tento web obsahuje obsah určený výhradně dospělým.',
  confirmLabel: 'Je mi 18+, vstoupit',
  leaveLabel: 'Opustit web',
};

describe('AgeGate', () => {
  it('renders the gate when no consent is stored', async () => {
    render(<AgeGate {...labels} />);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: labels.title })).toBeInTheDocument();
  });

  it('marks itself as a modal dialog labelled by its heading', async () => {
    render(<AgeGate {...labels} />);
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    const heading = screen.getByRole('heading', { name: labels.title });
    expect(dialog).toHaveAttribute('aria-labelledby', heading.id);
  });

  it('hides after confirming and persists the consent flag', async () => {
    render(<AgeGate {...labels} />);
    await userEvent.click(await screen.findByRole('button', { name: labels.confirmLabel }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('1');
  });

  it('does not render at all when consent is already stored', async () => {
    window.localStorage.setItem(STORAGE_KEY, '1');
    render(<AgeGate {...labels} />);
    // The effect runs on mount; give React a tick before asserting absence.
    await Promise.resolve();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('honours a custom storage key and does not read the default one', async () => {
    window.localStorage.setItem(STORAGE_KEY, '1');
    render(<AgeGate {...labels} storageKey="libertin.testKey" />);

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: labels.confirmLabel }));
    expect(window.localStorage.getItem('libertin.testKey')).toBe('1');
  });

  it('treats any value other than "1" as no consent', async () => {
    window.localStorage.setItem(STORAGE_KEY, 'true');
    render(<AgeGate {...labels} />);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
  });

  it('still shows the gate when storage is blocked (private browsing)', async () => {
    const getItem = vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    render(<AgeGate {...labels} />);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    getItem.mockRestore();
  });

  it('lets the user in for the page view even if the consent write fails', async () => {
    const setItem = vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    render(<AgeGate {...labels} />);
    await userEvent.click(await screen.findByRole('button', { name: labels.confirmLabel }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    setItem.mockRestore();
  });

  it('offers an exit route away from the site', async () => {
    render(<AgeGate {...labels} leaveHref="https://example.org" />);
    await screen.findByRole('dialog');
    expect(screen.getByRole('link', { name: labels.leaveLabel })).toHaveAttribute(
      'href',
      'https://example.org',
    );
  });
});
