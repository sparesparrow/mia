// @req REQ-WEB-004
// robots.txt and sitemap.xml are published and every listed page exists.
const SITE_URL = 'https://sparesparrow.github.io/mia/';

describe('robots.txt and sitemap.xml', () => {
    it('robots.txt points to the sitemap', () => {
        cy.request('/robots.txt').its('body').should('include', `Sitemap: ${SITE_URL}sitemap.xml`);
    });

    it('every page in the sitemap is served', () => {
        cy.request('/sitemap.xml').then((res) => {
            const locs = [...res.body.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
            expect(locs.length, 'sitemap entries').to.be.greaterThan(10);
            locs.map((loc) => `/${loc.slice(SITE_URL.length)}`)
                .filter((rel) => !rel.startsWith('/docs/'))
                .forEach((rel) => cy.request(rel).its('status').should('eq', 200));
        });
    });
});
