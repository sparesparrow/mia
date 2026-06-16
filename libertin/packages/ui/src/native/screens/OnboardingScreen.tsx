import React, { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { nativeTheme as t } from '@libertin/theme/native';
import { Screen } from '../Screen';
import { Button } from '../Button';

export interface OnboardingScreenProps {
  onFinish: () => void;
  onSkip?: () => void;
}

const STEP_KEYS = ['step1', 'step2', 'step3'] as const;

export function OnboardingScreen({ onFinish, onSkip }: OnboardingScreenProps) {
  const { t: translate } = useTranslation();
  const [step, setStep] = useState(0);
  const isLast = step === STEP_KEYS.length - 1;
  const key = STEP_KEYS[step] ?? STEP_KEYS[0];

  const handleNext = () => {
    if (isLast) {
      onFinish();
    } else {
      setStep((s) => s + 1);
    }
  };

  return (
    <Screen>
      <View style={styles.dots}>
        {STEP_KEYS.map((k, i) => (
          <View key={k} style={[styles.dot, i === step ? styles.dotActive : null]} />
        ))}
      </View>

      <View style={styles.body}>
        <Text style={styles.title}>{translate(`onboarding.${key}.title`)}</Text>
        <Text style={styles.copy}>{translate(`onboarding.${key}.body`)}</Text>
      </View>

      <View style={styles.actions}>
        <Button i18nKey={isLast ? 'onboarding.finish' : 'onboarding.next'} onPress={handleNext} />
        <Button variant="ghost" i18nKey="onboarding.skip" onPress={onSkip ?? onFinish} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  dots: { flexDirection: 'row', gap: t.spacing[2], justifyContent: 'center', marginTop: t.spacing[4] },
  dot: { width: 8, height: 8, borderRadius: t.radius.full, backgroundColor: t.colors.border },
  dotActive: { backgroundColor: t.colors.primary, width: 24 },
  body: { flex: 1, justifyContent: 'center', gap: t.spacing[3] },
  title: { fontSize: t.fontSize['3xl'], fontWeight: t.fontWeight.bold, color: t.colors.text },
  copy: { fontSize: t.fontSize.base, color: t.colors.textMuted, lineHeight: 24 },
  actions: { gap: t.spacing[1] },
});
