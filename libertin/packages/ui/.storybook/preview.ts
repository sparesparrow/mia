import type { Preview } from '@storybook/react';
import '@libertin/theme/tokens.css';

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
};

export default preview;
