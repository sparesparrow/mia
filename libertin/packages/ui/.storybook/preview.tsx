import React from 'react';
import type { Preview } from '@storybook/react';
import { initI18n } from '@libertin/i18n';
import '@libertin/theme/tokens.css';

// Initialize translations once so stories render real i18n copy (cs default).
void initI18n('cs');

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#FAFAF9' },
        { name: 'dark', value: '#222222' },
      ],
    },
  },
  globalTypes: {
    locale: {
      description: 'Language',
      defaultValue: 'cs',
      toolbar: {
        icon: 'globe',
        items: [
          { value: 'cs', title: 'Čeština' },
          { value: 'en', title: 'English' },
        ],
      },
    },
  },
  decorators: [
    (Story, context) => {
      const locale = context.globals.locale as 'cs' | 'en';
      void initI18n(locale);
      return <Story />;
    },
  ],
};

export default preview;
