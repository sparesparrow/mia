// @req REQ-WEB-001 REQ-WEB-002 REQ-WEB-004 REQ-WEB-005
// Read-only production smoke test: GET requests and page visits only, no clicks that submit anything.
//   npx cypress run --config baseUrl=https://mia-suzmatra.vercel.app --spec cypress/e2e/prod-smoke.cy.js
// Skipped when baseUrl is not https (local runs).
import { PAGE_URLS } from '../support/e2e';

const isProduction = /^https:/.test(Cypress.config('baseUrl') || '');
const isVercel = /vercel\.app/.test(Cypress.config('baseUrl') || '');

(isProduction ? describe : describe.skip)('Production smoke (read-only)', () => {
    PAGE_URLS.concat(['/docs/', '/robots.txt', '/sitemap.xml']).forEach((url) => {
        it(`GET ${url} returns 200`, () => {
            cy.request(url).its('status').should('eq', 200);
        });
    });

    it('the homepage renders with one h1 and the voice widget', () => {
        cy.visit('/');
        cy.get('h1').should('have.length', 1);
        cy.get('main#main').should('exist');
        cy.get('#crew-widget elevenlabs-convai').should('have.length', 1);
    });

    it('the homepage assets resolve', () => {
        cy.visit('/');
        cy.assertLocalLinksResolve('link[rel="stylesheet"][href], img[src], script[src]');
    });

    it('the 404 page links lead to real pages', () => {
        cy.visit('/this-page-does-not-exist/', { failOnStatusCode: false });
        cy.get('a[href]').should('have.length.at.least', 6);
        cy.assertLocalLinksResolve('a[href]');
    });

    (isVercel ? it : it.skip)('Vercel redirects GitHub Pages paths under /mia/ to the root', () => {
        cy.request({ url: '/mia/business/', followRedirect: false }).then((res) => {
            expect(res.status).to.be.oneOf([307, 308]);
            expect(res.headers.location).to.match(/^(https:\/\/mia-suzmatra\.vercel\.app)?\/business\/$/);
        });
        // Page URLs end in a slash; the first rule (`:path*`) missed exactly those.
        [['/mia', '/'], ['/mia/', '/'], ['/mia/journalists/en/', '/journalists/en/']].forEach(([from, to]) => {
            cy.request({ url: from, followRedirect: false }).its('headers.location')
                .should('match', new RegExp(`^(https://[^/]+)?${to.replace(/\//g, '\\/')}$`));
        });
    });

    (isVercel ? it : it.skip)('Vercel sends the security headers', () => {
        cy.request('/').then((res) => {
            expect(res.headers['strict-transport-security']).to.match(/max-age=\d+/);
            expect(res.headers['x-content-type-options']).to.eq('nosniff');
            expect(res.headers['x-frame-options']).to.eq('SAMEORIGIN');
            expect(res.headers['referrer-policy']).to.be.a('string');
            expect(res.headers['content-security-policy']).to.include("frame-ancestors 'self'");
            expect(res.headers['content-security-policy-report-only']).to.include("script-src 'self' 'sha256-");
        });
    });
});
