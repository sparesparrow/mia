import type { Meta, StoryObj } from '@storybook/react';
import { LoginForm } from './index';

const meta: Meta<typeof LoginForm> = {
  title: 'Web/LoginForm',
  component: LoginForm,
  args: { onSubmit: () => {} },
};
export default meta;
type Story = StoryObj<typeof LoginForm>;

export const Default: Story = {};
export const Loading: Story = { args: { loading: true } };
export const WithError: Story = { args: { error: 'Nesprávný e-mail nebo heslo.' } };
