import type { Meta, StoryObj } from '@storybook/react';
import { AgeGate } from './index';

const meta: Meta<typeof AgeGate> = {
  title: 'Web/AgeGate',
  component: AgeGate,
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof AgeGate>;

export const Default: Story = {
  args: {
    title: 'Je vám 18 nebo více let?',
    body: 'Tento web obsahuje obsah určený výhradně dospělým. Pokračováním potvrzujete, že jste starší 18 let.',
    confirmLabel: 'Je mi 18+, vstoupit',
    leaveLabel: 'Opustit web',
    // Unique per-render key so the story always shows the gate.
    storageKey: `storybook.ageGate.${Math.random().toString(36).slice(2)}`,
  },
};
