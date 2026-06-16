import type { Meta, StoryObj } from '@storybook/react';
import { OnboardingScreen } from './OnboardingScreen';

const meta: Meta<typeof OnboardingScreen> = {
  title: 'Screens/Auth/Onboarding',
  component: OnboardingScreen,
  args: { onFinish: () => {} },
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof OnboardingScreen>;

export const Default: Story = {};
