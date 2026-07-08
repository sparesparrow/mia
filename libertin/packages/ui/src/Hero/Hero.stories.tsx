import type { Meta, StoryObj } from '@storybook/react';
import { Hero } from './index';

const meta: Meta<typeof Hero> = {
  title: 'Web/Hero',
  component: Hero,
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof Hero>;

export const Default: Story = {
  args: {
    title: 'Vaše komunita, vaše pravidla',
    subtitle: 'Diskrétní sociální síť pro dospělé.',
    ctaLabel: 'Vstoupit',
    ctaHref: '/login',
  },
};
