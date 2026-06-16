// Native (React Native) design tokens.
// CSS custom properties don't resolve in RN, so this mirrors tokens.css with
// concrete values. Components import from here instead of hardcoding hex/sizes.

export const nativeTheme = {
  colors: {
    primary: '#F20B49',
    primaryText: '#C40A3C',
    bg: '#FAFAF9',
    surface: '#FFFFFF',
    surfaceDark: '#222222',
    text: '#1E1B1B',
    textMuted: '#6B6868',
    info: '#0264FB',
    success: '#15803D',
    error: '#C40A3C',
    border: 'rgba(30, 27, 27, 0.15)',
    onPrimary: '#FFFFFF',
  },
  spacing: { 1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32, 12: 48, 16: 64 },
  radius: { sm: 4, md: 8, lg: 16, full: 9999 },
  fontSize: { xs: 12, sm: 14, base: 16, lg: 18, '2xl': 24, '3xl': 32, '4xl': 40 },
  fontWeight: { normal: '400', medium: '500', semibold: '600', bold: '700' },
} as const;

export type NativeTheme = typeof nativeTheme;
