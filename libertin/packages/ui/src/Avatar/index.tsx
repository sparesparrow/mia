import React from 'react';

export interface AvatarProps {
  src?: string;
  alt?: string;
  size?: 'sm' | 'md' | 'lg';
  initials?: string;
}

const sizes: Record<NonNullable<AvatarProps['size']>, number> = { sm: 32, md: 48, lg: 80 };

export function Avatar({ src, alt = '', size = 'md', initials }: AvatarProps) {
  const px = sizes[size];
  const baseStyle: React.CSSProperties = {
    width: px, height: px, borderRadius: '50%', overflow: 'hidden',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'var(--color-primary)', color: 'var(--color-on-primary)',
    fontWeight: 600, fontSize: Math.round(px * 0.35), flexShrink: 0,
  };
  if (src) return <img src={src} alt={alt} style={{ ...baseStyle, objectFit: 'cover' }} />;
  return <span style={baseStyle} aria-label={alt}>{initials ?? '?'}</span>;
}
