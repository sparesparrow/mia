import type { Meta, StoryObj } from '@storybook/react';
import { SuccessScreen } from './SuccessScreen';

const meta: Meta<typeof SuccessScreen> = {
  title: 'Screens/Auth/Success',
  component: SuccessScreen,
  args: { onContinue: () => {} },
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof SuccessScreen>;

export const Default: Story = {};
