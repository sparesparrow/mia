export const theme = {
  colors: {
    primary: 'var(--color-primary)',
    primaryText: 'var(--color-primary-text)',
    onPrimary: 'var(--color-on-primary)',
    bg: 'var(--color-bg)',
    surface: 'var(--color-surface)',
    surfaceDark: 'var(--color-surface-dark)',
    text: 'var(--color-text)',
    textMuted: 'var(--color-text-muted)',
    info: 'var(--color-info)',
    success: 'var(--color-success)',
    error: 'var(--color-error)',
    border: 'var(--color-border)',
  },
  spacing: {
    1: 'var(--space-1)',
    2: 'var(--space-2)',
    3: 'var(--space-3)',
    4: 'var(--space-4)',
    6: 'var(--space-6)',
    8: 'var(--space-8)',
    12: 'var(--space-12)',
    16: 'var(--space-16)',
  },
  radius: {
    sm: 'var(--radius-sm)',
    md: 'var(--radius-md)',
    lg: 'var(--radius-lg)',
    full: 'var(--radius-full)',
  },
  fontSize: {
    xs: 'var(--text-xs)',
    sm: 'var(--text-sm)',
    base: 'var(--text-base)',
    lg: 'var(--text-lg)',
    '2xl': 'var(--text-2xl)',
    '3xl': 'var(--text-3xl)',
    '4xl': 'var(--text-4xl)',
  },
  fontWeight: {
    normal: 'var(--font-normal)',
    medium: 'var(--font-medium)',
    semibold: 'var(--font-semibold)',
    bold: 'var(--font-bold)',
  },
} as const;

export type Theme = typeof theme;
