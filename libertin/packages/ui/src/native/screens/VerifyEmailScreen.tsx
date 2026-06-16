import React from 'react';
import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';
import { nativeTheme as t } from '@libertin/theme/native';
import { Screen } from '../Screen';
import { Button } from '../Button';

export interface VerifyEmailScreenProps {
  /** Interpolated into the body copy — never hardcode the address. */
  email: string;
  /** Mock/dev affordance to simulate the user clicking the link in their inbox. */
  onVerified: () => void;
  onResend?: () => void;
  loading?: boolean;
}

export function VerifyEmailScreen({ email, onVerified, onResend, loading }: VerifyEmailScreenProps) {
  const { t: translate } = useTranslation();

  return (
    <Screen centered>
      <Text style={styles.title}>{translate('verify.title')}</Text>
      <Text style={styles.body}>{translate('verify.body', { email })}</Text>

      <Button i18nKey="verify.verified" onPress={onVerified} loading={loading ?? false} />
      <Button variant="ghost" i18nKey="verify.resend" onPress={onResend} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: t.fontSize['3xl'], fontWeight: t.fontWeight.bold, color: t.colors.text },
  body: { fontSize: t.fontSize.base, color: t.colors.textMuted, lineHeight: 24 },
});
