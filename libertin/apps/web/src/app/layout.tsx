import './globals.css';
import type { Metadata } from 'next';
import { getDict } from '@libertin/i18n/dict';
import { AgeGate } from '@libertin/ui';
import { MswProvider } from '../lib/MswProvider';

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
  return (
    <html lang="cs">
      <body>
        <MswProvider />
        {children}
        <AgeGate
          title={dict.ageGate.title}
          body={dict.ageGate.body}
          confirmLabel={dict.ageGate.confirm}
          leaveLabel={dict.ageGate.leave}
        />
      </body>
    </html>
  );
}
