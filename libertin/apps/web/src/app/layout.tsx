import './globals.css';
import type { Metadata } from 'next';
import { getDict } from '@libertin/i18n/dict';
import { AgeGate } from '@libertin/ui';
import { MswProvider } from '../lib/MswProvider';

const dict = getDict('cs');

export const metadata: Metadata = {
  title: {
    default: `${dict.meta.title} — ${dict.meta.tagline}`,
    template: `%s | ${dict.meta.title}`,
  },
  description: dict.meta.description,
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
