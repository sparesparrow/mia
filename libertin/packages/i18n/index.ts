import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import locales from './locales.json';

export const defaultNS = 'common';

export const resources = {
  cs: locales.cs,
  en: locales.en,
} as const;

export type Locale = keyof typeof resources;
export type Namespace = keyof typeof resources.cs;

export function initI18n(lng: Locale = 'cs') {
  return i18n.use(initReactI18next).init({
    lng,
    fallbackLng: 'en',
    resources,
    defaultNS,
    interpolation: { escapeValue: false },
  });
}

export { i18n };
