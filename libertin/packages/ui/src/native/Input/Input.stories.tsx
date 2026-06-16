import type { Meta, StoryObj } from '@storybook/react';
import { Input } from './index';

const meta: Meta<typeof Input> = { title: 'Native/Input', component: Input };
export default meta;
type Story = StoryObj<typeof Input>;

export const Default: Story = { args: { label: 'E-mail', placeholder: 'vas@email.cz' } };
export const WithError: Story = { args: { label: 'E-mail', value: 'chybne', error: 'Neplatný e-mail' } };
export const Password: Story = { args: { label: 'Heslo', secureTextEntry: true, placeholder: '••••••••' } };
