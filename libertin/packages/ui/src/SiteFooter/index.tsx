import React from 'react';

export interface FooterLink {
  label: string;
  href: string;
}

export interface SiteFooterProps {
  brand: string;
  links: FooterLink[];
  ageNote: string;
}

export function SiteFooter({ brand, links, ageNote }: SiteFooterProps) {
  return (
    <footer
      style={{
        backgroundColor: 'var(--color-surface-dark)',
        color: 'var(--color-on-primary)',
        padding: 'var(--space-8) var(--space-6)',
        marginTop: 'var(--space-16)',
      }}
    >
      <div
        style={{
          maxWidth: 960,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <span style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>{brand}</span>
        <nav aria-label={brand}>
          <ul
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'center',
              gap: 'var(--space-4)',
              listStyle: 'none',
              margin: 0,
              padding: 0,
            }}
          >
            {links.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  style={{
                    color: 'var(--color-on-primary)',
                    opacity: 0.8,
                    textDecoration: 'none',
                    fontSize: 'var(--text-sm)',
                  }}
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <span style={{ fontSize: 'var(--text-xs)', opacity: 0.6 }}>{ageNote}</span>
      </div>
    </footer>
  );
}
