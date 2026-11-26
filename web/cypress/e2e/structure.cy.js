// @req REQ-WEB-001 REQ-WEB-004
// Page structure on every published page: language, landmarks, headings, skip link, Open Graph, images.
import { PAGE_URLS } from '../support/e2e';

const expectedLang = (url) => (url === '/' || !url.endsWith('/en/') ? 'cs' : 'en');

describe('Page structure', () => {
    PAGE_URLS.forEach((url) => {
        it(`${url} has one main landmark, one h1 and a working skip link`, () => {
            cy.visit(url);
            cy.get('html').should('have.attr', 'lang', expectedLang(url));
            cy.get('main#main').should('have.length', 1);
            cy.get('h1').should('have.length', 1).and('not.be.empty');
            cy.get('body a').first().should('have.class', 'skip-link').and('have.attr', 'href', '#main');
            cy.get('.skip-link').focus();
            cy.get('.skip-link').then(($link) => {
                const box = $link[0].getBoundingClientRect();
                expect(box.top, 'focused skip link is on screen').to.be.at.least(0);
                expect(box.height, 'focused skip link has a size').to.be.greaterThan(0);
            });
        });

        it(`${url} has Open Graph tags and alt text on every image`, () => {
            cy.visit(url);
            ['og:title', 'og:description', 'og:url', 'og:image'].forEach((prop) => {
                cy.get(`meta[property="${prop}"]`).should('have.attr', 'content').and('not.be.empty');
            });
            cy.get('img').each(($img) => {
                expect($img[0].hasAttribute('alt'), $img.attr('src')).to.eq(true);
            });
        });

        it(`${url} fits a 390 px phone screen and its local links resolve`, () => {
            cy.viewport(390, 844);
            cy.visit(url);
            cy.assertNoHorizontalOverflow();
            cy.assertLocalLinksResolve();
        });
    });
});
