import React, { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { nativeTheme as t } from '@libertin/theme/native';
import { Screen } from '../Screen';
import { Input } from '../Input';
import { Button } from '../Button';

export interface LoginScreenProps {
  onSubmit: (email: string, password: string) => void;
  onForgotPassword?: () => void;
  onRegister?: () => void;
  loading?: boolean;
  error?: string | undefined;
}

export function LoginScreen({ onSubmit, onForgotPassword, onRegister, loading, error }: LoginScreenProps) {
  const { t: translate } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <Screen centered>
      <Text style={styles.title}>{translate('auth.login.title')}</Text>

      <Input
        label={translate('auth.login.email')}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        textContentType="emailAddress"
        placeholder="vas@email.cz"
      />
      <Input
        label={translate('auth.login.password')}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        textContentType="password"
        placeholder="••••••••"
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Button
        i18nKey="auth.login.submit"
        onPress={() => onSubmit(email, password)}
        loading={loading ?? false}
        disabled={email.length === 0 || password.length === 0}
      />

      <View style={styles.links}>
        <Button variant="ghost" size="sm" i18nKey="auth.login.forgotPassword" onPress={onForgotPassword} />
        <Button variant="ghost" size="sm" i18nKey="auth.login.noAccount" onPress={onRegister} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: t.fontSize['3xl'], fontWeight: t.fontWeight.bold, color: t.colors.primary, marginBottom: t.spacing[2] },
  error: { color: t.colors.error, fontSize: t.fontSize.sm },
  links: { gap: t.spacing[1], alignItems: 'center', marginTop: t.spacing[2] },
});
