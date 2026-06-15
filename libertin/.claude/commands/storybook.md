Start Storybook for packages/ui and verify all stories load.

Run: pnpm --filter=@libertin/ui storybook

Then verify all 4 component stories are present and render without errors:
- UI/Button (Primary, Secondary, Ghost, Loading, Disabled)
- UI/Input (Default, WithError, Password)
- UI/Card (Default, WithImage)
- UI/Avatar (WithInitials, Small, Large)

Report any missing stories or console errors.
