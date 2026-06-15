import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
  as?: React.ElementType;
}

export function Card({ children, style, as: Tag = 'div' }: CardProps) {
  return (
    <Tag
      style={{
        borderRadius: 'var(--radius-lg)',
        backgroundColor: 'var(--color-surface)',
        boxShadow: 'var(--shadow-sm)',
        border: '1px solid var(--color-border)',
        padding: 'var(--space-4)',
        ...style,
      }}
    >
      {children}
    </Tag>
  );
}
