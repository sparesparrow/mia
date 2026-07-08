'use client';

import { useEffect } from 'react';

// Starts the MSW service worker in development so the app boots with zero
// backend. Requires `pnpm --filter=@libertin/web msw:init` once (generates
// public/mockServiceWorker.js).
export function MswProvider() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;
    void import('@libertin/api/browser')
      .then(({ worker }) => worker.start({ onUnhandledRequest: 'bypass' }))
      .catch((err: unknown) => {
        console.warn(
          '[libertin] MSW worker failed to start — run `pnpm --filter=@libertin/web msw:init`.',
          err,
        );
      });
  }, []);

  return null;
}
