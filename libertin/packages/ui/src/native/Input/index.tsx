import React from 'react';
import { StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle } from 'react-native';
import { nativeTheme as t } from '@libertin/theme/native';

export interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  containerStyle?: ViewStyle;
}

export function Input({ label, error, containerStyle, style, ...props }: InputProps) {
  return (
    <View style={[styles.container, containerStyle]}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <TextInput
        placeholderTextColor={t.colors.textMuted}
        {...props}
        style={[styles.input, error ? styles.inputError : null, style]}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: t.spacing[1], width: '100%' },
  label: { fontSize: t.fontSize.sm, fontWeight: t.fontWeight.medium, color: t.colors.text },
  input: {
    borderRadius: t.radius.md,
    borderWidth: 1,
    borderColor: t.colors.border,
    paddingVertical: t.spacing[3],
    paddingHorizontal: t.spacing[3],
    fontSize: t.fontSize.base,
    color: t.colors.text,
    backgroundColor: t.colors.surface,
  },
  inputError: { borderColor: t.colors.error },
  error: { fontSize: t.fontSize.xs, color: t.colors.error },
});
