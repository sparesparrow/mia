import type { NextConfig } from 'next';
const config: NextConfig = {
  transpilePackages: ['@libertin/ui', '@libertin/theme', '@libertin/i18n', '@libertin/api'],
};
export default config;
