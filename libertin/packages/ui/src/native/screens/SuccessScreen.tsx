import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { nativeTheme as t } from '@libertin/theme/native';
import { Screen } from '../Screen';
import { Button } from '../Button';

export interface SuccessScreenProps {
  onContinue: () => void;
}

export function SuccessScreen({ onContinue }: SuccessScreenProps) {
  const { t: translate } = useTranslation();

  return (
    <Screen centered>
      <View style={styles.badge}>
        <Text style={styles.badgeMark}>✓</Text>
      </View>
      <Text style={styles.title}>{translate('success.title')}</Text>
      <Text style={styles.body}>{translate('success.body')}</Text>
      <Button i18nKey="success.continue" onPress={onContinue} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  badge: { width: 72, height: 72, borderRadius: t.radius.full, backgroundColor: t.colors.success, alignItems: 'center', justifyContent: 'center', alignSelf: 'center' },
  badgeMark: { color: t.colors.onPrimary, fontSize: t.fontSize['3xl'], fontWeight: t.fontWeight.bold },
  title: { fontSize: t.fontSize['3xl'], fontWeight: t.fontWeight.bold, color: t.colors.text, textAlign: 'center' },
  body: { fontSize: t.fontSize.base, color: t.colors.textMuted, textAlign: 'center', lineHeight: 24 },
});
