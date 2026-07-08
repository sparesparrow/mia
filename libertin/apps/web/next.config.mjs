// Security headers — direct response to the live-site audit
// (docs/live-audit.md): the old site ships none of these. Referrer-Policy
// `same-origin` is deliberate: discretion is a feature, external sites must
// never learn the visitor came from here.
const securityHeaders = [
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  { key: 'Referrer-Policy', value: 'same-origin' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
];

/** @type {import('next').NextConfig} */
const config = {
  transpilePackages: ['@libertin/ui', '@libertin/theme', '@libertin/i18n', '@libertin/api'],
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },
};

export default config;
