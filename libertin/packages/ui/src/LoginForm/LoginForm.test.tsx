import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from './index';

const emailField = () => screen.getByLabelText('E-mail');
const passwordField = () => screen.getByLabelText('Heslo');
const submitButton = () => screen.getByRole('button', { name: 'Přihlásit se' });

describe('LoginForm', () => {
  it('renders localised labels from the dictionary, not hardcoded copy', () => {
    render(<LoginForm onSubmit={vi.fn()} />);
    expect(screen.getByRole('heading', { name: 'Přihlášení' })).toBeInTheDocument();
    expect(emailField()).toBeInTheDocument();
    expect(passwordField()).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zapomenuté heslo?' })).toBeInTheDocument();
  });

  it('keeps submit disabled until both fields are filled', async () => {
    render(<LoginForm onSubmit={vi.fn()} />);
    expect(submitButton()).toBeDisabled();

    await userEvent.type(emailField(), 'a@example.com');
    expect(submitButton()).toBeDisabled();

    await userEvent.type(passwordField(), 'pw');
    expect(submitButton()).toBeEnabled();
  });

  it('re-disables submit when a field is cleared again', async () => {
    render(<LoginForm onSubmit={vi.fn()} />);
    await userEvent.type(emailField(), 'a@example.com');
    await userEvent.type(passwordField(), 'pw');
    expect(submitButton()).toBeEnabled();

    await userEvent.clear(passwordField());
    expect(submitButton()).toBeDisabled();
  });

  it('calls onSubmit exactly once with the typed credentials', async () => {
    const onSubmit = vi.fn();
    render(<LoginForm onSubmit={onSubmit} />);

    await userEvent.type(emailField(), 'clen@example.com');
    await userEvent.type(passwordField(), 'tajneheslo');
    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith('clen@example.com', 'tajneheslo');
  });

  it('does not submit while loading, so a slow request cannot be double-posted', async () => {
    const onSubmit = vi.fn();
    render(<LoginForm onSubmit={onSubmit} loading />);

    await userEvent.type(emailField(), 'clen@example.com');
    await userEvent.type(passwordField(), 'tajneheslo');
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();

    await userEvent.click(button, { pointerEventsCheck: 0 });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('announces an error through role="alert" so screen readers pick it up', () => {
    render(<LoginForm onSubmit={vi.fn()} error="Nesprávné přihlašovací údaje." />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Nesprávné přihlašovací údaje.');
  });

  it('renders no alert region when there is no error', () => {
    render(<LoginForm onSubmit={vi.fn()} />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('masks the password field and never exposes the typed secret as text', async () => {
    render(<LoginForm onSubmit={vi.fn()} />);
    const password = passwordField();
    expect(password).toHaveAttribute('type', 'password');
    await userEvent.type(password, 'tajneheslo');
    // Discretion: the secret must not leak into rendered text content anywhere.
    expect(document.body.textContent).not.toContain('tajneheslo');
  });

  it('uses the given hrefs for the recovery and registration links', () => {
    render(<LoginForm onSubmit={vi.fn()} forgotHref="/zapomenute" registerHref="/registrace" />);
    expect(screen.getByRole('link', { name: 'Zapomenuté heslo?' })).toHaveAttribute('href', '/zapomenute');
    expect(screen.getByRole('link', { name: 'Nemáte účet? Zaregistrujte se' })).toHaveAttribute(
      'href',
      '/registrace',
    );
  });
});
