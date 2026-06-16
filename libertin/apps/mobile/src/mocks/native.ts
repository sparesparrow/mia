import { setupServer } from 'msw/native';
import { handlers } from '@libertin/api/handlers';

// MSW server for React Native (uses a fetch interceptor under the hood).
// Imports handlers via the subpath so we never pull in msw/node or msw/browser.
export const server = setupServer(...handlers);
