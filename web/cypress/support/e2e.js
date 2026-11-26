import './commands';

// Every generated page in both languages, plus the hand-written Czech and English homepages (web/README.md site map).
export const PAGES = ['business', 'family', 'musicians', 'journalists', 'press'];
export const PAGE_URLS = ['/', '/en/'].concat(PAGES.flatMap((page) => [`/${page}/`, `/${page}/en/`]));

const isLocal = () => !/^https:/.test(Cypress.config('baseUrl') || '');

beforeEach(() => {
    if (isLocal()) {
        // Keep local runs hermetic: third-party scripts and fonts are stubbed, so no test depends on
        // unpkg, Google Fonts or ElevenLabs, and no voice conversation can start.
        cy.intercept({ hostname: 'unpkg.com' }, { statusCode: 200, body: '', headers: { 'content-type': 'text/javascript' } });
        cy.intercept({ hostname: 'fonts.googleapis.com' }, { statusCode: 200, body: '', headers: { 'content-type': 'text/css' } });
        cy.intercept({ hostname: 'cdnjs.cloudflare.com' }, { statusCode: 200, body: '', headers: { 'content-type': 'text/css' } });
        cy.intercept({ hostname: /elevenlabs\.io$/ }, { statusCode: 204, body: '' });
    }
});

// Cross-origin script errors carry no detail ("Script error."); anything from the site itself fails the test.
Cypress.on('uncaught:exception', (err) => !/^Script error\.?$/.test(err.message));
