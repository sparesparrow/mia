import React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { Card } from './index';

const meta: Meta<typeof Card> = { title: 'UI/Card', component: Card };
export default meta;
type Story = StoryObj<typeof Card>;

export const Default: Story = { args: { children: <p style={{ margin: 0 }}>Obsah karty</p> } };
export const WithImage: Story = {
  args: {
    children: (
      <>
        <div style={{ background: 'var(--color-primary)', height: 120, borderRadius: 'var(--radius-md)' }} />
        <p style={{ marginTop: 'var(--space-3)', marginBottom: 0 }}>Popis obsahu</p>
      </>
    ),
  },
};
