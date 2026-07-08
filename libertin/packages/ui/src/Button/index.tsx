'use client';

import React from 'react';
import { useTranslation } from 'react-i18next';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  i18nKey?: string;
}

const sizeStyles: Record<ButtonSize, React.CSSProperties> = {
  sm: { padding: '6px 12px', fontSize: 'var(--text-sm)' },
  md: { padding: '10px 20px', fontSize: 'var(--text-base)' },
  lg: { padding: '14px 28px', fontSize: 'var(--text-lg)' },
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  i18nKey,
  children,
  disabled,
  style,
  ...props
}: ButtonProps) {
  const { t } = useTranslation();

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 'var(--radius-md)',
    fontWeight: 600,
    border: 'none',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled || loading ? 0.5 : 1,
    transition: 'opacity 0.15s, filter 0.15s',
    ...sizeStyles[size],
  };

  const variantStyle: React.CSSProperties =
    variant === 'primary'
      ? { backgroundColor: 'var(--color-primary)', color: 'var(--color-on-primary)' }
      : variant === 'secondary'
        ? { backgroundColor: 'transparent', border: '1.5px solid var(--color-primary)', color: 'var(--color-primary-text)' }
        : { backgroundColor: 'transparent', color: 'var(--color-primary-text)', textDecoration: 'underline' };

  return (
    <button
      {...props}
      disabled={disabled || loading}
      style={{ ...baseStyle, ...variantStyle, ...style }}
    >
      {loading ? '…' : i18nKey ? t(i18nKey) : children}
    </button>
  );
}
