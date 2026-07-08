// Server-safe dictionary access. This module must stay free of react-i18next
// (which calls createContext at module scope and would crash React Server
// Components). Server components import from '@libertin/i18n/dict'.
import locales from './locales.json';

export const dicts = {
  cs: locales.cs,
  en: locales.en,
} as const;

export type Locale = keyof typeof dicts;
export type Dict = (typeof dicts)['cs'];

export function getDict(locale: Locale): Dict {
  return dicts[locale];
}
