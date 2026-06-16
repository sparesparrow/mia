import type { Meta, StoryObj } from '@storybook/react';
import { VerifyEmailScreen } from './VerifyEmailScreen';

const meta: Meta<typeof VerifyEmailScreen> = {
  title: 'Screens/Auth/VerifyEmail',
  component: VerifyEmailScreen,
  args: { email: 'user@example.com', onVerified: () => {} },
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof VerifyEmailScreen>;

export const Default: Story = {};
export const Loading: Story = { args: { loading: true } };
