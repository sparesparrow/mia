import React from 'react';

export interface HeroProps {
  title: string;
  subtitle: string;
  ctaLabel: string;
  ctaHref: string;
}

export function Hero({ title, subtitle, ctaLabel, ctaHref }: HeroProps) {
  return (
    <section
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        gap: 'var(--space-4)',
        padding: 'var(--space-16) var(--space-6) var(--space-12)',
      }}
    >
      <h1
        style={{
          color: 'var(--color-primary)',
          fontSize: 'var(--text-4xl)',
          fontWeight: 700,
          margin: 0,
          lineHeight: 1.15,
        }}
      >
        {title}
      </h1>
      <p
        style={{
          color: 'var(--color-text-muted)',
          fontSize: 'var(--text-lg)',
          margin: 0,
          maxWidth: 560,
        }}
      >
        {subtitle}
      </p>
      <a
        href={ctaHref}
        style={{
          display: 'inline-block',
          backgroundColor: 'var(--color-primary)',
          color: 'var(--color-on-primary)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 32px',
          fontSize: 'var(--text-lg)',
          fontWeight: 600,
          textDecoration: 'none',
          marginTop: 'var(--space-2)',
        }}
      >
        {ctaLabel}
      </a>
    </section>
  );
}
