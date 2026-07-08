import React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { CategoryCard } from './index';

const meta: Meta<typeof CategoryCard> = {
  title: 'Web/CategoryCard',
  component: CategoryCard,
};
export default meta;
type Story = StoryObj<typeof CategoryCard>;

export const Naturists: Story = { args: { name: 'Naturisté', href: '/login' } };
export const Swingers: Story = { args: { name: 'Swingeři', href: '/login' } };
export const Bdsm: Story = { args: { name: 'BDSM', href: '/login' } };
export const Shibari: Story = { args: { name: 'Šibari', href: '/login' } };

export const Grid: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-4)' }}>
      <CategoryCard name="Naturisté" href="/login" />
      <CategoryCard name="Swingeři" href="/login" />
      <CategoryCard name="BDSM" href="/login" />
      <CategoryCard name="Šibari" href="/login" />
    </div>
  ),
};
