import './globals.css';
import type { Metadata } from 'next';
import { getDict } from '@libertin/i18n/dict';
import { MswProvider } from '../lib/MswProvider';
import { AgeGateGuard } from '../lib/AgeGateGuard';
import { AGE_CONSENT_COOKIE, cookiesRequiredNotice, hasAgeConsent } from '../lib/ageConsent';

const dict = getDict('cs');

export const metadata: Metadata = {
  // Deliberately just the brand: the tagline names the audience, and a tab
  // title or browser-history entry is visible to anyone near the screen.
  // Authenticated views must never put content in <title> either.
  title: {
    default: dict.meta.title,
    template: `%s | ${dict.meta.title}`,
  },
  description: dict.meta.description,
  openGraph: { title: dict.meta.title, description: dict.meta.description },
  twitter: { title: dict.meta.title, description: dict.meta.description },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Decided on the server, before a byte of HTML exists. When consent is
  // missing we render the gate *instead of* `children`, not on top of it — an
  // element React never renders is never serialised, so the page content does
  // not reach the browser at all (docs/privacy-review.md, P3).
  const consented = hasAgeConsent();

  return (
    <html lang="cs">
      <body>
        <MswProvider />
        {consented ? (
          children
        ) : (
          <AgeGateGuard
            title={dict.ageGate.title}
            body={dict.ageGate.body}
            confirmLabel={dict.ageGate.confirm}
            leaveLabel={dict.ageGate.leave}
            cookieName={AGE_CONSENT_COOKIE}
            cookieNotice={cookiesRequiredNotice(dict.ageGate)}
          />
        )}
      </body>
    </html>
  );
}
