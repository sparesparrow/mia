import type { StorybookConfig } from '@storybook/react-vite';
import { mergeConfig } from 'vite';

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(ts|tsx)'],
  addons: ['@storybook/addon-essentials', '@storybook/addon-a11y'],
  framework: { name: '@storybook/react-vite', options: {} },
  // Render React Native components in the web Storybook via react-native-web.
  viteFinal: async (cfg) =>
    mergeConfig(cfg, {
      define: { __DEV__: 'true', global: 'window' },
      resolve: {
        alias: { 'react-native': 'react-native-web' },
        extensions: ['.web.tsx', '.web.ts', '.tsx', '.ts', '.web.js', '.js'],
      },
    }),
};

export default config;
