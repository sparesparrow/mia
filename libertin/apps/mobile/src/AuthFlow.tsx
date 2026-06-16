import React, { useCallback, useState } from 'react';
import { createClient } from '@libertin/api/client';
import {
  FeedScreen,
  LoginScreen,
  OnboardingScreen,
  SuccessScreen,
  VerifyEmailScreen,
  type FeedScreenItem,
} from '@libertin/ui/native';

// Matches the base URL the MSW handlers intercept.
const API_BASE = 'https://api.libertin.cz/v1';
const client = createClient(API_BASE);

type Step = 'login' | 'verify' | 'success' | 'onboarding' | 'feed';

export function AuthFlow() {
  const [step, setStep] = useState<Step>('login');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [feed, setFeed] = useState<FeedScreenItem[]>([]);

  const handleLogin = useCallback(async (inputEmail: string, password: string) => {
    setLoading(true);
    setError(undefined);
    try {
      const res = await client.auth.login({ email: inputEmail, password });
      setEmail(res.user.email);
      setToken(res.token);
      setStep(res.user.verified ? 'success' : 'verify');
    } catch {
      setError('Přihlášení se nezdařilo. Zkontrolujte údaje.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleVerified = useCallback(async () => {
    setLoading(true);
    try {
      const res = await client.auth.verify({ token: 'mock-verification-token' });
      if (res.success) setStep('success');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFinish = useCallback(async () => {
    setLoading(true);
    try {
      const res = await client.feed.get({ page: 1, limit: 20 }, token);
      setFeed(
        res.items.map((item) => ({
          id: item.id,
          author: item.author?.displayName ?? 'Anonym',
          content: item.content ?? null,
        })),
      );
    } finally {
      setLoading(false);
      setStep('feed');
    }
  }, [token]);

  switch (step) {
    case 'login':
      return <LoginScreen onSubmit={handleLogin} loading={loading} error={error} />;
    case 'verify':
      return <VerifyEmailScreen email={email} onVerified={handleVerified} loading={loading} />;
    case 'success':
      return <SuccessScreen onContinue={() => setStep('onboarding')} />;
    case 'onboarding':
      return <OnboardingScreen onFinish={handleFinish} />;
    case 'feed':
      return <FeedScreen items={feed} loading={loading} />;
  }
}
