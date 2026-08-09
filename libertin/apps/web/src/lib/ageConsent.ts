import { cookies } from 'next/headers';
import type { Dict } from '@libertin/i18n/dict';

/**
 * Session cookie that records the 18+ confirmation.
 *
 * Deliberately boring name: cookies are visible to anyone who opens devtools on
 * a borrowed laptop, so it must not describe what the site is. It carries no
 * value beyond `1` — no identity, no timestamp, nothing to correlate.
 */
export const AGE_CONSENT_COOKIE = 'libertin.age';

/**
 * Reads the consent decision on the server, before any HTML is produced.
 *
 * This is the fix for P3 in docs/privacy-review.md: the previous gate was a
 * client overlay, so the full landing page — including the words that name the
 * audience — was already in the response body and stayed visible until React
 * hydrated. Deciding here means the gated tree is never rendered, never
 * serialised and never sent.
 *
 * Cost, stated openly: `cookies()` opts the whole app out of static rendering.
 * That is unavoidable for a per-visitor decision, and the alternative (leaking
 * the page to unconfirmed visitors) is not a trade we are willing to make.
 *
 * Known residual, measured on `next build` + `next start` (Next 14.2.35): the
 * rendered markup of an unconfirmed response contains the gate and nothing
 * else, but Next still streams the child segment's RSC seed data inside a
 * `self.__next_f.push(...)` script, so the page tree is present in the response
 * *source* even though nothing renders it. That is structural — Next builds the
 * cache-node seed for child segments before the layout decides whether to
 * render them, so no layout-level change can suppress it. Closing it needs the
 * request to be stopped before routing, i.e. `apps/web/middleware.ts` rewriting
 * unconfirmed requests to a gate route. Tracked as a follow-up to E14-T5.
 */
export function hasAgeConsent(): boolean {
  return cookies().get(AGE_CONSENT_COOKIE)?.value === '1';
}

/**
 * Copy for the "your browser is refusing cookies" state.
 *
 * The key `ageGate.cookiesRequired` does not exist in `packages/i18n/locales.json`
 * yet and that file is owned by another role in this batch, so it is read
 * defensively rather than hardcoded here — hardcoding a Czech sentence in the
 * app would break the "no copy outside i18n" rule. Until the key lands the gate
 * simply stays closed, which is the safe direction: no content is revealed and
 * no consent is silently granted.
 */
export function cookiesRequiredNotice(gate: Dict['ageGate']): string | undefined {
  const value = (gate as Record<string, unknown>)['cookiesRequired'];
  return typeof value === 'string' ? value : undefined;
}
