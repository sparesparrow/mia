import type { Meta, StoryObj } from '@storybook/react';
import { AgeGate } from './index';

const meta: Meta<typeof AgeGate> = {
  title: 'Web/AgeGate',
  component: AgeGate,
  parameters: { layout: 'fullscreen' },
  args: {
    title: 'Je vám 18 nebo více let?',
    body: 'Tento web obsahuje obsah určený výhradně dospělým. Pokračováním potvrzujete, že jste starší 18 let.',
    confirmLabel: 'Je mi 18+, vstoupit',
    leaveLabel: 'Opustit web',
    // Per-story cookie name so confirming in one story does not silence the
    // others, and so the shared app cookie is never written from Storybook.
    cookieName: 'storybook.ageGate',
  },
};
export default meta;
type Story = StoryObj<typeof AgeGate>;

/**
 * How the gate looks to a visitor who has not confirmed yet. In the real app it
 * is rendered *instead of* the page, never over it — the server decides.
 */
export const Default: Story = {};

/**
 * What the visitor sees when the browser refuses cookies. Consent cannot be
 * recorded, so nothing is revealed and nothing permanent is written; the gate
 * explains itself instead of leaving a dead button.
 */
export const CookiesBlocked: Story = {
  args: {
    // A `__Secure-` cookie is rejected unless it is set over HTTPS with the
    // Secure attribute, and Storybook runs on http://localhost — so pressing
    // "confirm" here reproduces a refused cookie without touching browser
    // settings. Press the confirm button to see the state.
    cookieName: '__Secure-storybook.ageGate',
    cookieNotice:
      'Váš prohlížeč blokuje cookies, takže si potvrzení nemůžeme zapamatovat. Povolte je prosím pro tuto relaci.',
  },
};
