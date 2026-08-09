'use client';

import { useRouter } from 'next/navigation';
import { AgeGate } from '@libertin/ui';

export interface AgeGateGuardProps {
  title: string;
  body: string;
  confirmLabel: string;
  leaveLabel: string;
  cookieName: string;
  cookieNotice?: string | undefined;
}

/**
 * The only client-side part of the age gate: it takes the click, writes the
 * session cookie and then asks the server to render again.
 *
 * `router.refresh()` re-runs the layout, which now sees the cookie and returns
 * the real page. The content therefore still arrives only after the server has
 * seen consent — the client never unhides anything it was already holding,
 * because it was never given it.
 */
export function AgeGateGuard({ cookieNotice, ...labels }: AgeGateGuardProps) {
  const router = useRouter();

  return <AgeGate {...labels} cookieNotice={cookieNotice} onConfirmed={() => router.refresh()} />;
}
