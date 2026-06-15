import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Libertin',
  description: 'Diskrétní komunitní sociální síť pro dospělé.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="cs">
      <body>{children}</body>
    </html>
  );
}
