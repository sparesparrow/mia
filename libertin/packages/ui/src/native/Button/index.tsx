import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, ViewStyle } from 'react-native';
import { useTranslation } from 'react-i18next';
import { nativeTheme as t } from '@libertin/theme/native';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps {
  variant?: ButtonVariant | undefined;
  size?: ButtonSize | undefined;
  loading?: boolean | undefined;
  disabled?: boolean | undefined;
  /** i18next key resolved at render. Takes precedence over `title`. */
  i18nKey?: string | undefined;
  title?: string | undefined;
  onPress?: (() => void) | undefined;
  style?: ViewStyle | undefined;
  accessibilityLabel?: string | undefined;
}

const sizePadding: Record<ButtonSize, ViewStyle> = {
  sm: { paddingVertical: t.spacing[1] + 2, paddingHorizontal: t.spacing[3] },
  md: { paddingVertical: t.spacing[3], paddingHorizontal: t.spacing[6] },
  lg: { paddingVertical: t.spacing[4], paddingHorizontal: t.spacing[8] },
};

const sizeFont: Record<ButtonSize, number> = {
  sm: t.fontSize.sm,
  md: t.fontSize.base,
  lg: t.fontSize.lg,
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  i18nKey,
  title,
  onPress,
  style,
  accessibilityLabel,
}: ButtonProps) {
  const { t: translate } = useTranslation();
  const isDisabled = disabled || loading;
  const label = i18nKey ? translate(i18nKey) : (title ?? '');

  const containerStyle: ViewStyle = {
    ...styles.base,
    ...sizePadding[size],
    ...(variant === 'primary' ? styles.primary : variant === 'secondary' ? styles.secondary : styles.ghost),
    opacity: isDisabled ? 0.5 : 1,
  };

  const textColor = variant === 'primary' ? t.colors.onPrimary : t.colors.primaryText;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      style={({ pressed }) => [containerStyle, pressed && !isDisabled ? styles.pressed : null, style]}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <Text
          style={{
            color: textColor,
            fontSize: sizeFont[size],
            fontWeight: t.fontWeight.semibold,
            textDecorationLine: variant === 'ghost' ? 'underline' : 'none',
          }}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { borderRadius: t.radius.md, alignItems: 'center', justifyContent: 'center', flexDirection: 'row' },
  primary: { backgroundColor: t.colors.primary },
  secondary: { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: t.colors.primary },
  ghost: { backgroundColor: 'transparent' },
  pressed: { opacity: 0.8 },
});
