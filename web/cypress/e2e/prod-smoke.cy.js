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
