import { describe, expect, it } from 'vitest';
import { dicts, getDict, type Locale } from './dict';
import { initI18n, i18n, resources, defaultNS } from './index';

type Tree = { [key: string]: string | Tree };

const LOCALES: Locale[] = ['cs', 'en'];

/** Flattens a dictionary into `a.b.c -> value` pairs. */
function flatten(tree: Tree, prefix = ''): Map<string, string> {
  const out = new Map<string, string>();
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') {
      out.set(path, value);
    } else {
      for (const [k, v] of flatten(value, path)) out.set(k, v);
    }
  }
  return out;
}

/** All i18next placeholders in a string: `{{email}}` and the legacy `{email}`. */
function placeholders(value: string): string[] {
  return [...value.matchAll(/\{\{?\s*([a-zA-Z0-9_]+)\s*\}?\}/g)]
    .map((m) => m[1] as string)
    .sort();
}

const flat = {
  cs: flatten(dicts.cs as unknown as Tree),
  en: flatten(dicts.en as unknown as Tree),
};

describe('locales.json — cs/en structural parity (contract B13)', () => {
  it('ships both contracted locales', () => {
    expect(Object.keys(dicts).sort()).toEqual(['cs', 'en']);
  });

  it('has no key present in cs but missing in en', () => {
    const missing = [...flat.cs.keys()].filter((k) => !flat.en.has(k));
    expect(missing).toEqual([]);
  });

  it('has no key present in en but missing in cs', () => {
    const missing = [...flat.en.keys()].filter((k) => !flat.cs.has(k));
    expect(missing).toEqual([]);
  });

  it('has an identical key structure in both trees', () => {
    expect([...flat.en.keys()].sort()).toEqual([...flat.cs.keys()].sort());
  });

  it('keeps the same top-level namespaces in both trees', () => {
    expect(Object.keys(dicts.en).sort()).toEqual(Object.keys(dicts.cs).sort());
  });

  it('has no leaf that is an object in one locale and a string in the other', () => {
    // flatten() only records string leaves, so a type mismatch shows up as a
    // key that exists in one map and not the other — plus this direct check.
    for (const key of flat.cs.keys()) {
      expect(typeof flat.en.get(key), `en.${key}`).toBe('string');
    }
  });

  it.each(LOCALES)('has no empty or whitespace-only string in %s', (locale) => {
    const empty = [...flat[locale].entries()]
      .filter(([, v]) => v.trim().length === 0)
      .map(([k]) => k);
    expect(empty).toEqual([]);
  });

  it.each(LOCALES)('has no untranslated placeholder marker (TODO/FIXME/XXX) in %s', (locale) => {
    const suspicious = [...flat[locale].entries()]
      .filter(([, v]) => /\b(TODO|FIXME|XXX)\b/i.test(v))
      .map(([k]) => k);
    expect(suspicious).toEqual([]);
  });
});

describe('locales.json — interpolation parity', () => {
  it('uses the same placeholder set for every key in cs and en', () => {
    const mismatches: string[] = [];
    for (const [key, csValue] of flat.cs) {
      const enValue = flat.en.get(key);
      if (enValue === undefined) continue;
      const csVars = placeholders(csValue);
      const enVars = placeholders(enValue);
      if (JSON.stringify(csVars) !== JSON.stringify(enVars)) {
        mismatches.push(`${key}: cs=[${csVars.join(',')}] en=[${enVars.join(',')}]`);
      }
    }
    expect(mismatches).toEqual([]);
  });

  it('uses the i18next double-brace form everywhere (single braces never interpolate)', () => {
    const singleBrace: string[] = [];
    for (const locale of LOCALES) {
      for (const [key, value] of flat[locale]) {
        if (/(^|[^{])\{[a-zA-Z0-9_]+\}/.test(value)) singleBrace.push(`${locale}.${key}`);
      }
    }
    expect(singleBrace).toEqual([]);
  });

  it('actually interpolates a value at runtime instead of rendering the raw token', async () => {
    await initI18n('cs');
    const rendered = i18n.t('verify.body', { email: 'clen@example.com' });
    expect(rendered).toContain('clen@example.com');
    expect(rendered).not.toContain('{{email}}');
  });
});

describe('locales.json — discretion and privacy', () => {
  it.each(LOCALES)('contains no real e-mail address in %s', (locale) => {
    const leaks = [...flat[locale].entries()]
      .filter(([, v]) => /[\w.+-]+@[\w-]+\.[\w.]+/.test(v))
      .filter(([, v]) => !/@example\.(com|org|net)\b/.test(v))
      .map(([k]) => k);
    expect(leaks).toEqual([]);
  });

  it.each(LOCALES)('contains no phone number in %s', (locale) => {
    const leaks = [...flat[locale].entries()]
      .filter(([, v]) => /(\+\d{1,3}[\s-]?)?(\d[\s-]?){9,}/.test(v))
      .map(([k]) => k);
    expect(leaks).toEqual([]);
  });

  it.each(LOCALES)('uses the unified Libertin brand, not the legacy domain, in %s', (locale) => {
    const stale = [...flat[locale].entries()]
      .filter(([, v]) => /swingerslife/i.test(v))
      .map(([k]) => k);
    expect(stale).toEqual([]);
  });

  it('does not reintroduce the corrected Czech wording ("svoji schránku")', () => {
    const bad = [...flat.cs.entries()]
      .filter(([, v]) => /\bsvoji\b/i.test(v))
      .map(([k]) => k);
    expect(bad).toEqual([]);
  });
});

describe('i18n runtime wiring', () => {
  it('exposes both locales under the single default namespace', () => {
    expect(Object.keys(resources).sort()).toEqual(['cs', 'en']);
    expect(resources.cs).toHaveProperty(defaultNS);
    expect(resources.en).toHaveProperty(defaultNS);
  });

  it('resolves plain dot paths across top-level groups', async () => {
    await initI18n('cs');
    expect(i18n.t('auth.login.title')).toBe('Přihlášení');
    expect(i18n.t('common.error')).not.toBe('common.error');
  });

  it('switches language and returns the other tree', async () => {
    await initI18n('cs');
    await i18n.changeLanguage('en');
    expect(i18n.t('auth.login.title')).toBe(getDict('en').auth.login.title);
    await i18n.changeLanguage('cs');
    expect(i18n.t('auth.login.title')).toBe(getDict('cs').auth.login.title);
  });

  it('returns the key itself for an unknown path, so gaps are visible', async () => {
    await initI18n('cs');
    expect(i18n.t('does.not.exist')).toBe('does.not.exist');
  });

  it('every key used by the UI resolves in both locales', async () => {
    // Keys hardcoded in packages/ui components — a rename in locales.json
    // without a component update must fail here, not in production.
    const usedKeys = [
      'auth.login.title',
      'auth.login.email',
      'auth.login.emailPlaceholder',
      'auth.login.password',
      'auth.login.submit',
      'auth.login.forgotPassword',
      'auth.login.noAccount',
      'ageGate.title',
      'ageGate.body',
      'ageGate.confirm',
      'ageGate.leave',
    ];
    for (const locale of LOCALES) {
      await initI18n(locale);
      await i18n.changeLanguage(locale);
      for (const key of usedKeys) {
        expect(i18n.t(key), `${locale}:${key}`).not.toBe(key);
      }
    }
  });
});
