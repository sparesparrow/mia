// Test-only type support: registers the @testing-library/jest-dom matchers
// (toBeDisabled, toBeInTheDocument, …) on Vitest's `expect` so the component
// tests type-check. The matchers themselves are installed in vitest.setup.ts.
import '@testing-library/jest-dom/vitest';
