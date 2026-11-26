// @req REQ-WEB-004
// Text contrast (WCAG 2.2 AA) on every published page, desktop and phone width. Text over gradients and
// images is skipped by the command and checked by eye (web/README.md).
import { PAGE_URLS } from '../support/e2e';

describe('Text contrast', () => {
    PAGE_URLS.forEach((url) => {
        it(`${url} has readable text over solid backgrounds`, () => {
            cy.visit(url);
            cy.assertTextContrast();
        });
    });

    // The homepage has its own menu.
    it('the open mobile menu on the generated pages has readable links', () => {
        cy.viewport(390, 844);
        PAGE_URLS.filter((url) => url !== '/').forEach((url) => {
            cy.visit(url);
            cy.get('.mobile-menu-toggle').click();
            cy.assertTextContrast();
        });
    });
});
