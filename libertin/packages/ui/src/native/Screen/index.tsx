import React from 'react';
import { ScrollView, StyleSheet, View, ViewStyle } from 'react-native';
import { nativeTheme as t } from '@libertin/theme/native';

export interface ScreenProps {
  children: React.ReactNode;
  /** Vertically center content (auth/success screens). */
  centered?: boolean;
  style?: ViewStyle;
}

export function Screen({ children, centered = false, style }: ScreenProps) {
  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[styles.content, centered ? styles.centered : null, style]}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.inner}>{children}</View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: t.colors.bg },
  content: { flexGrow: 1, padding: t.spacing[6] },
  centered: { justifyContent: 'center' },
  inner: { width: '100%', maxWidth: 480, alignSelf: 'center', gap: t.spacing[4] },
});
