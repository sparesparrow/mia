import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { dicts } from './dict';

// The whole dictionary lives under one namespace so call sites can use plain
// dot paths across top-level groups: t('auth.login.title'), t('common.error').
// (Multiple namespaces would require the 'auth:login.title' separator syntax.)
export const defaultNS = 'common';

export const resources = {
  cs: { common: dicts.cs },
  en: { common: dicts.en },
} as const;

export type { Locale, Dict } from './dict';
export { getDict, dicts } from './dict';

export type Namespace = keyof typeof dicts.cs;

export function initI18n(lng: keyof typeof resources = 'cs') {
  if (i18n.isInitialized) {
    return i18n.changeLanguage(lng);
  }
  return i18n.use(initReactI18next).init({
    lng,
    fallbackLng: 'en',
    resources,
    defaultNS,
    interpolation: { escapeValue: false },
  });
}

export { i18n };
