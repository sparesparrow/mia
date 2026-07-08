import React from 'react';

export interface CategoryCardProps {
  name: string;
  href: string;
}

export function CategoryCard({ name, href }: CategoryCardProps) {
  return (
    <a
      href={href}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 'var(--space-3)',
        padding: 'var(--space-6)',
        borderRadius: 'var(--radius-lg)',
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-sm)',
        textDecoration: 'none',
      }}
    >
      <span
        aria-hidden
        style={{
          width: 56,
          height: 56,
          borderRadius: 'var(--radius-full)',
          backgroundColor: 'var(--color-primary)',
          color: 'var(--color-on-primary)',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 'var(--text-2xl)',
          fontWeight: 700,
        }}
      >
        {name.charAt(0)}
      </span>
      <span
        style={{
          color: 'var(--color-text)',
          fontSize: 'var(--text-lg)',
          fontWeight: 600,
        }}
      >
        {name}
      </span>
    </a>
  );
}
