// @req REQ-WEB-001 REQ-WEB-002
// Language switch, audience links and the mobile menu.
import { PAGES } from '../support/e2e';

const SEGMENTS = PAGES.filter((page) => page !== 'press');

describe('Navigation', () => {
    PAGES.forEach((page) => {
        it(`${page}: the language switch goes Czech -> English -> Czech`, () => {
            cy.visit(`/${page}/`);
            cy.get('.lang-link[hreflang="en"]').click();
            cy.location('pathname').should('eq', `/${page}/en/`);
            cy.get('html').should('have.attr', 'lang', 'en');
            cy.get('.lang-link[hreflang="cs"]').click();
            cy.location('pathname').should('eq', `/${page}/`);
            cy.get('html').should('have.attr', 'lang', 'cs');
        });

        it(`${page}: the footer links to every audience in the same language`, () => {
            cy.visit(`/${page}/en/`);
            SEGMENTS.concat('press').forEach((target) => {
                cy.get(`#site-footer a[href$="${target}/en/"]`).should('exist');
            });
            ['developers', 'mechanics', 'testers'].forEach((role) => {
                cy.get(`#site-footer a[href*="docs/for/${role}/"]`).should('exist');
            });
        });
    });

    it('the homepage EN link opens the English journalists page', () => {
        cy.visit('/');
        cy.get('a[hreflang="en"]').first().click();
        cy.location('pathname').should('eq', '/journalists/en/');
        cy.get('html').should('have.attr', 'lang', 'en');
    });

    it('the mobile menu opens and closes on a segment page', () => {
        cy.viewport(390, 844);
        cy.visit('/business/');
        cy.get('.mobile-menu-toggle').should('be.visible').and('have.attr', 'aria-expanded', 'false');
        cy.get('.mobile-menu-toggle').click();
        cy.get('.mobile-menu-toggle').should('have.attr', 'aria-expanded', 'true');
        cy.get('.nav-menu').should('have.class', 'mobile-open');
        cy.get('.nav-menu a[href="#today"]').click();
        cy.get('.mobile-menu-toggle').should('have.attr', 'aria-expanded', 'false');
    });

    it('old flat URLs and role aliases redirect', () => {
        cy.visit('/customers/family.html');
        cy.location('pathname').should('eq', '/family/');
        cy.request('/developers/').its('body').should('include', 'url=../docs/for/developers/');
    });
});
