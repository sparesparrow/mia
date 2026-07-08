import type { Metadata } from 'next';
import { getDict } from '@libertin/i18n/dict';
import { LoginPageClient } from './LoginPageClient';

const dict = getDict('cs');

export const metadata: Metadata = {
  title: dict.auth.login.title,
};

export default function LoginPage() {
  return <LoginPageClient />;
}
