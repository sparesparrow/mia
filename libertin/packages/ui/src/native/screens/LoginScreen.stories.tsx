import type { Meta, StoryObj } from '@storybook/react';
import { LoginScreen } from './LoginScreen';

const meta: Meta<typeof LoginScreen> = {
  title: 'Screens/Auth/Login',
  component: LoginScreen,
  args: { onSubmit: () => {} },
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof LoginScreen>;

export const Default: Story = {};
export const Loading: Story = { args: { loading: true } };
export const WithError: Story = { args: { error: 'Nesprávný e-mail nebo heslo.' } };
