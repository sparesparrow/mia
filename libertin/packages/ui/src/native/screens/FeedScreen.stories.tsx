import type { Meta, StoryObj } from '@storybook/react';
import { FeedScreen } from './FeedScreen';

const meta: Meta<typeof FeedScreen> = {
  title: 'Screens/Feed',
  component: FeedScreen,
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof FeedScreen>;

export const WithItems: Story = {
  args: {
    items: [
      { id: '1', author: 'Jan Novák', content: 'Vítejte v komunitě Libertin.' },
      { id: '2', author: 'Eva Nováková', content: null },
    ],
  },
};
export const Empty: Story = { args: { items: [] } };
export const Loading: Story = { args: { items: [], loading: true } };
