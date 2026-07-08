import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { dicts } from './dict';

export const defaultNS = 'common';

export const resources = dicts;

export type { Locale, Dict } from './dict';
export { getDict, dicts } from './dict';

export type Namespace = keyof typeof resources.cs;

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
