import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from './index';

describe('Input', () => {
  it('associates the label with the control so getByLabelText / a11y work', () => {
    render(<Input label="E-mail" />);
    const field = screen.getByLabelText('E-mail');
    expect(field.tagName).toBe('INPUT');
  });

  it('derives a slug id from a multi-word label', () => {
    render(<Input label="Nové heslo" />);
    expect(screen.getByLabelText('Nové heslo')).toHaveAttribute('id', 'nové-heslo');
  });

  it('prefers an explicit id over the derived one', () => {
    render(<Input label="E-mail" id="login-email" />);
    expect(screen.getByLabelText('E-mail')).toHaveAttribute('id', 'login-email');
  });

  it('renders the error message as visible text', () => {
    render(<Input label="E-mail" error="Neplatný e-mail." />);
    expect(screen.getByText('Neplatný e-mail.')).toBeInTheDocument();
  });

  it('does not leak the error prop into the DOM as an attribute', () => {
    render(<Input label="E-mail" error="Neplatný e-mail." />);
    expect(screen.getByLabelText('E-mail')).not.toHaveAttribute('error');
  });

  it('signals the error state with the error token, not a raw colour', () => {
    render(<Input label="E-mail" error="Neplatný e-mail." />);
    const style = screen.getByLabelText('E-mail').getAttribute('style') ?? '';
    expect(style).toContain('var(--color-error)');
    expect(style).not.toMatch(/#[0-9a-f]{3,8}/i);
  });

  it('reports every keystroke to onChange', async () => {
    const onChange = vi.fn();
    render(<Input label="E-mail" value="" onChange={onChange} />);
    await userEvent.type(screen.getByLabelText('E-mail'), 'abc');
    expect(onChange).toHaveBeenCalledTimes(3);
  });

  it('renders the controlled value it is given', () => {
    const { rerender } = render(<Input label="E-mail" value="" onChange={() => undefined} />);
    expect(screen.getByLabelText('E-mail')).toHaveValue('');
    rerender(<Input label="E-mail" value="a@example.com" onChange={() => undefined} />);
    expect(screen.getByLabelText('E-mail')).toHaveValue('a@example.com');
  });

  it('renders without a label when none is given', () => {
    render(<Input placeholder="Hledat" />);
    expect(screen.getByPlaceholderText('Hledat')).toBeInTheDocument();
    expect(document.querySelectorAll('label')).toHaveLength(0);
  });
});
