import type { Meta, StoryObj } from '@storybook/react';
import { Avatar } from './index';

const meta: Meta<typeof Avatar> = { title: 'UI/Avatar', component: Avatar };
export default meta;
type Story = StoryObj<typeof Avatar>;

export const WithInitials: Story = { args: { initials: 'JN', size: 'md' } };
export const Small: Story = { args: { initials: 'AB', size: 'sm' } };
export const Large: Story = { args: { initials: 'KP', size: 'lg' } };
export const WithImage: Story = { args: { src: 'https://placehold.co/80', alt: 'Profil', size: 'md' } };
