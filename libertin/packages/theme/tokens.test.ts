// Parity guard: packages/theme/native.ts is a hand-maintained mirror of the
// literal values in tokens.css, because CSS custom properties do not resolve in
// React Native. Nothing else verifies the two agree, so a divergence would only
// surface visually on a device. This test makes the drift fail in CI instead.
//
// How tokens present in only ONE of the two files are treated — deliberate, not
// accidental:
//
//   * Web-only by design: `--shadow-*`. React Native has no box-shadow; it uses
//     a different model (elevation / shadowOffset+shadowRadius), so mirroring
//     the CSS string would be a lie. These live in WEB_ONLY_PREFIXES and are
//     asserted to be the ONLY unmirrored tokens — a new unmirrored CSS token
//     fails until someone classifies it here.
//   * There are currently no native-only tokens. `onPrimary` looks like one but
//     mirrors `--color-on-primary`; it just reads differently after the
//     kebab-case -> camelCase rename. Any genuinely new native key fails the
//     category/token completeness checks below.
//   * `[data-theme="private"]` (the authenticated night theme) is intentionally
//     NOT mirrored: native has no dark palette yet. Rather than skip it in
//     silence, the category check pins nativeTheme's top-level shape, so the
//     day a `private`/dark palette is added to native this test goes red and
//     has to be extended to cover it.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { nativeTheme } from './native';

const cssSource = readFileSync(new URL('./tokens.css', import.meta.url), 'utf8');

/** How a CSS custom-property prefix maps onto a nativeTheme category. */
interface Category {
  /** CSS custom-property prefix, e.g. `--color-`. */
  readonly prefix: string;
  /** Top-level key in nativeTheme, e.g. `colors`. */
  readonly nativeKey: string;
  /** How values on both sides are canonicalised before comparison. */
  readonly kind: 'color' | 'px' | 'weight';
}

const CATEGORIES: readonly Category[] = [
  { prefix: '--color-', nativeKey: 'colors', kind: 'color' },
  { prefix: '--space-', nativeKey: 'spacing', kind: 'px' },
  { prefix: '--radius-', nativeKey: 'radius', kind: 'px' },
  { prefix: '--text-', nativeKey: 'fontSize', kind: 'px' },
  { prefix: '--font-', nativeKey: 'fontWeight', kind: 'weight' },
];

/** CSS token families that are deliberately not mirrored in React Native. */
const WEB_ONLY_PREFIXES: readonly string[] = ['--shadow-'];

type TokenMap = Record<string, string>;

function stripComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, '');
}

/** Reads one rule block (`selector { ... }`) into a `--name` -> value map. */
function readBlock(css: string, selector: string): TokenMap {
  const start = css.indexOf(selector);
  if (start === -1) throw new Error(`tokens.css: selector "${selector}" not found`);
  const open = css.indexOf('{', start);
  const close = css.indexOf('}', open);
  if (open === -1 || close === -1) {
    throw new Error(`tokens.css: unterminated block for selector "${selector}"`);
  }

  const out: TokenMap = {};
  for (const declaration of css.slice(open + 1, close).split(';')) {
    const trimmed = declaration.trim();
    if (trimmed === '') continue;
    const separator = trimmed.indexOf(':');
    if (separator === -1) {
      throw new Error(`tokens.css: cannot parse declaration "${trimmed}" in "${selector}"`);
    }
    const name = trimmed.slice(0, separator).trim();
    const value = trimmed.slice(separator + 1).trim();
    if (!name.startsWith('--')) {
      throw new Error(`tokens.css: expected a custom property, got "${name}" in "${selector}"`);
    }
    out[name] = value;
  }
  return out;
}

const rootTokens = readBlock(stripComments(cssSource), ':root');
const privateTokens = readBlock(stripComments(cssSource), '[data-theme="private"]');

/** `text-muted` -> `textMuted`; leaves `2xl`, `sm` and numeric keys alone. */
function toCamelCase(name: string): string {
  return name.replace(/-([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}

function categoryOf(token: string): Category | undefined {
  return CATEGORIES.find((category) => token.startsWith(category.prefix));
}

/** Canonicalises a CSS literal so it can be compared with the native literal. */
function canonicaliseCss(kind: Category['kind'], token: string, value: string): string {
  switch (kind) {
    case 'color':
      return value.toLowerCase().replace(/\s+/g, ' ');
    case 'px': {
      const match = /^(-?\d+(?:\.\d+)?)px$/.exec(value);
      if (match === null || match[1] === undefined) {
        throw new Error(`tokens.css: ${token} = "${value}" is not a plain px value`);
      }
      return String(Number(match[1]));
    }
    case 'weight': {
      if (!/^\d+$/.test(value)) {
        throw new Error(`tokens.css: ${token} = "${value}" is not a numeric font weight`);
      }
      return String(Number(value));
    }
  }
}

/** Canonicalises a nativeTheme literal onto the same scale as the CSS one. */
function canonicaliseNative(kind: Category['kind'], path: string, value: unknown): string {
  switch (kind) {
    case 'color':
      if (typeof value !== 'string') {
        throw new Error(`native.ts: ${path} = ${JSON.stringify(value)} should be a colour string`);
      }
      return value.toLowerCase().replace(/\s+/g, ' ');
    case 'px':
      // RN sizes are unitless numbers; the CSS side carries the px suffix.
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new Error(`native.ts: ${path} = ${JSON.stringify(value)} should be a number`);
      }
      return String(value);
    case 'weight':
      // RN fontWeight is a string ('400'), CSS font-weight is a number (400).
      if (typeof value !== 'string' || !/^\d+$/.test(value)) {
        throw new Error(`native.ts: ${path} = ${JSON.stringify(value)} should be a numeric string`);
      }
      return String(Number(value));
  }
}

// nativeTheme is a deeply-literal `as const` object; indexing it by a string
// computed from CSS needs one widening cast rather than `any` at every use.
const native: Record<string, Record<string, unknown>> = nativeTheme as unknown as Record<
  string,
  Record<string, unknown>
>;

describe('tokens.css and native.ts do not drift apart', () => {
  it('every :root token is either mirrored in native.ts or explicitly web-only', () => {
    const unclassified = Object.keys(rootTokens).filter(
      (token) =>
        categoryOf(token) === undefined &&
        !WEB_ONLY_PREFIXES.some((prefix) => token.startsWith(prefix)),
    );

    // A new token family in tokens.css must be consciously mirrored or declared
    // web-only in this file. Silence is what let the two files drift.
    expect(unclassified, 'unclassified tokens in tokens.css :root').toEqual([]);
  });

  it('the tokens skipped as web-only are exactly the shadow family', () => {
    const webOnly = Object.keys(rootTokens).filter((token) =>
      WEB_ONLY_PREFIXES.some((prefix) => token.startsWith(prefix)),
    );
    expect(webOnly.sort()).toEqual(['--shadow-md', '--shadow-sm']);
  });

  it('nativeTheme exposes exactly the mirrored categories and nothing else', () => {
    // Pins the top-level shape: a new native category (e.g. a `private` dark
    // palette, or RN shadows) fails here until it is mapped above.
    expect(Object.keys(native).sort()).toEqual(
      CATEGORIES.map((category) => category.nativeKey).sort(),
    );
  });

  describe.each(CATEGORIES)('$nativeKey ($prefix)', ({ prefix, nativeKey, kind }) => {
    const cssEntries = Object.entries(rootTokens).filter(([token]) => token.startsWith(prefix));
    const nativeGroup = native[nativeKey] ?? {};

    it('is not empty (guards against a silently vacuous comparison)', () => {
      expect(cssEntries.length).toBeGreaterThan(0);
      expect(Object.keys(nativeGroup).length).toBe(cssEntries.length);
    });

    it('mirrors every token, with the same value', () => {
      const problems: string[] = [];
      const expectedNativeKeys = new Set<string>();

      for (const [token, cssValue] of cssEntries) {
        const key = toCamelCase(token.slice(prefix.length));
        expectedNativeKeys.add(key);

        if (!Object.prototype.hasOwnProperty.call(nativeGroup, key)) {
          problems.push(`${token}: missing from native.ts as ${nativeKey}.${key}`);
          continue;
        }

        const expected = canonicaliseCss(kind, token, cssValue);
        const actual = canonicaliseNative(kind, `${nativeKey}.${key}`, nativeGroup[key]);
        if (expected !== actual) {
          problems.push(
            `${token}: tokens.css has "${cssValue}" but native.ts ` +
              `${nativeKey}.${key} has ${JSON.stringify(nativeGroup[key])}`,
          );
        }
      }

      for (const key of Object.keys(nativeGroup)) {
        if (!expectedNativeKeys.has(key)) {
          problems.push(`${nativeKey}.${key}: present in native.ts but no ${prefix}* token in tokens.css`);
        }
      }

      // Listing the offending token names is the whole point — "not equal" at
      // 3am tells you nothing.
      expect(problems, `${nativeKey} drifted from tokens.css`).toEqual([]);
    });
  });

  it('the private night theme only overrides tokens that exist in :root', () => {
    // native.ts mirrors the light palette only (see header note). This keeps the
    // web-side override block honest in the meantime.
    const orphans = Object.keys(privateTokens).filter(
      (token) => !Object.prototype.hasOwnProperty.call(rootTokens, token),
    );
    expect(orphans, '[data-theme="private"] overrides an undefined token').toEqual([]);
  });
});
