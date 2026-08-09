import React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { ThemeToggle } from './index';

const meta: Meta<typeof ThemeToggle> = {
  title: 'Web/ThemeToggle',
  component: ThemeToggle,
  parameters: { layout: 'centered' },
  decorators: [
    (Story) => (
      <div
        style={{
          backgroundColor: 'var(--color-bg)',
          color: 'var(--color-text)',
          padding: 'var(--space-8)',
          borderRadius: 'var(--radius-lg)',
        }}
      >
        <Story />
      </div>
    ),
  ],
};
export default meta;
type Story = StoryObj<typeof ThemeToggle>;

/** Unique per story so one story's choice does not leak into the next. */
const key = (name: string) => `storybook.theme.${name}`;

export const Default: Story = {
  args: { storageKey: key('default') },
};

/** Icon-only variant for dense headers — still labelled for screen readers. */
export const IconOnly: Story = {
  args: { storageKey: key('icon-only'), showLabel: false },
};

/**
 * Starts in night mode: the `private` tokens from packages/theme are applied to
 * `<html>`, so the whole surface follows, not just this control.
 */
export const NightMode: Story = {
  args: { storageKey: key('night') },
  loaders: [
    () => {
      window.localStorage.setItem(key('night'), 'private');
      return {};
    },
  ],
};
