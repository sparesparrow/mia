import type { Meta, StoryObj } from '@storybook/react';
import { SiteFooter } from './index';

const meta: Meta<typeof SiteFooter> = {
  title: 'Web/SiteFooter',
  component: SiteFooter,
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof SiteFooter>;

export const Default: Story = {
  args: {
    brand: 'Libertin',
    links: [
      { label: 'O nás', href: '/o-nas' },
      { label: 'Kontakt', href: '/kontakt' },
      { label: 'Ochrana soukromí', href: '/soukromi' },
      { label: 'Podmínky použití', href: '/podminky' },
    ],
    ageNote: 'Pouze pro osoby starší 18 let',
  },
};
