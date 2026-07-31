import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './index';

describe('Button', () => {
  it('renders its children when no i18n key is given', () => {
    render(<Button>Vstoupit</Button>);
    expect(screen.getByRole('button', { name: 'Vstoupit' })).toBeInTheDocument();
  });

  it('resolves i18nKey through the dictionary instead of showing the raw key', () => {
    render(<Button i18nKey="auth.login.submit" />);
    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Přihlásit se');
    expect(button).not.toHaveTextContent('auth.login.submit');
  });

  // Regression guard: a shipped build used `disabled ?? loading`, which left the
  // button clickable while a submit was in flight and allowed double posts.
  it('is disabled while loading even when `disabled` is not passed', () => {
    render(<Button loading i18nKey="auth.login.submit" />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('is disabled while loading even when `disabled={false}` is passed explicitly', () => {
    render(<Button loading disabled={false} i18nKey="auth.login.submit" />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('does not fire onClick while loading', async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Odeslat
      </Button>,
    );
    await userEvent.click(screen.getByRole('button'), { pointerEventsCheck: 0 });
    expect(onClick).not.toHaveBeenCalled();
  });

  it('fires onClick when idle and enabled', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Odeslat</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('replaces the label with a busy indicator while loading, hiding stale copy', () => {
    render(
      <Button loading i18nKey="auth.login.submit">
        Odeslat
      </Button>,
    );
    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('…');
    expect(button).not.toHaveTextContent('Odeslat');
    expect(button).not.toHaveTextContent('Přihlásit se');
  });

  it('is disabled when `disabled` is set and not loading', () => {
    render(<Button disabled>Odeslat</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('forwards the submit type so it can drive a form', () => {
    render(<Button type="submit">Odeslat</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
  });

  it('styles from theme tokens, never raw hex', () => {
    render(<Button>Odeslat</Button>);
    const style = screen.getByRole('button').getAttribute('style') ?? '';
    expect(style).toContain('var(--color-primary)');
    expect(style).not.toMatch(/#[0-9a-f]{3,8}/i);
  });

  it('lets a caller override styles without losing the token base', () => {
    render(<Button style={{ width: '100%' }}>Odeslat</Button>);
    const style = screen.getByRole('button').getAttribute('style') ?? '';
    expect(style).toContain('width: 100%');
    expect(style).toContain('var(--radius-md)');
  });
});
