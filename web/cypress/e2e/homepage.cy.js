// @req REQ-WEB-003 REQ-WEB-004
// Homepage voice guides: switching guides swaps the widget without starting a conversation.
const CREW = ['holly', 'rimmer', 'kryten'];

describe('Homepage voice guides', () => {
    it('shows Holly first and switches the widget to each guide', () => {
        cy.visit('/');
        cy.get('#crew-widget elevenlabs-convai').should('have.length', 1).invoke('attr', 'agent-id').as('hollyId');
        cy.get('.crew-card[data-crew="holly"]').should('have.attr', 'aria-pressed', 'true');

        const seen = new Set();
        CREW.forEach((name) => {
            cy.get(`.crew-card[data-crew="${name}"]`).click();
            cy.get(`.crew-card[data-crew="${name}"]`).should('have.attr', 'aria-pressed', 'true');
            cy.get('.crew-card[aria-pressed="true"]').should('have.length', 1);
            cy.get('#crew-widget elevenlabs-convai').should('have.length', 1)
                .invoke('attr', 'agent-id').then((id) => {
                    expect(id).to.match(/^agent_[a-z0-9]+$/);
                    seen.add(id);
                });
        });
        cy.wrap(seen).its('size').should('eq', CREW.length);
    });

    it('says that the guides run in the ElevenLabs cloud', () => {
        cy.visit('/');
        cy.get('.crew-note').should('contain.text', 'ElevenLabs');
    });

    it('lazy-loads every image below the hero', () => {
        cy.visit('/');
        cy.get('img').not('.suzmatra-logo, .hero-bg-img').each(($img) => {
            expect($img.attr('loading'), $img.attr('src')).to.eq('lazy');
        });
    });
});
