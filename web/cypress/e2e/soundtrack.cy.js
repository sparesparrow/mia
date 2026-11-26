// @req REQ-WEB-004
// Homepage soundtrack: starts by itself, falls back to the first interaction when the browser blocks sound,
// gives way to the voice guides and remembers when the visitor switches it off. The media element is
// stubbed, so the tests check the page's policy, not the browser's audio stack.
const HOMEPAGES = ['/', '/en/'];

// Replaces play/pause/paused on every media element. With `blocked`, play() rejects until a gesture
// unblocks it, like a browser's autoplay policy.
const stubMedia = (win, { blocked }) => {
    const state = { playing: false, blocked };
    const proto = win.HTMLMediaElement.prototype;
    cy.stub(proto, 'paused').get(() => !state.playing);
    cy.stub(proto, 'play').as('play').callsFake(function play() {
        if (state.blocked) {
            return Promise.reject(new win.DOMException('blocked', 'NotAllowedError'));
        }
        state.playing = true;
        this.dispatchEvent(new win.Event('play'));
        return Promise.resolve();
    });
    cy.stub(proto, 'pause').as('pause').callsFake(function pause() {
        state.playing = false;
        this.dispatchEvent(new win.Event('pause'));
    });
    win.addEventListener('pointerdown', () => { state.blocked = false; }, true);
};

describe('Homepage soundtrack', () => {
    HOMEPAGES.forEach((url) => {
        it(`${url} starts the music by itself when the browser allows it`, () => {
            cy.visit(url, { onBeforeLoad: (win) => stubMedia(win, { blocked: false }) });
            cy.get('@play').should('have.been.calledOnce');
            cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'true');
        });
    });

    it('waits for the first click when the browser blocks sound', () => {
        cy.visit('/', { onBeforeLoad: (win) => stubMedia(win, { blocked: true }) });
        cy.get('@play').should('have.been.calledOnce');
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'false');
        cy.get('h1').click();
        cy.get('@play').should('have.been.calledTwice');
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'true');
    });

    it('a crew card pauses the music and never starts it', () => {
        cy.visit('/', { onBeforeLoad: (win) => stubMedia(win, { blocked: true }) });
        cy.get('@play').should('have.been.calledOnce');
        cy.get('.crew-card[data-crew="rimmer"]').click();
        cy.get('h1').click();
        cy.get('@play').should('have.been.calledOnce');
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'false');

        cy.visit('/', { onBeforeLoad: (win) => stubMedia(win, { blocked: false }) });
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'true');
        cy.get('.crew-card[data-crew="kryten"]').click();
        cy.get('@pause').should('have.been.called');
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'false');
    });

    it('remembers when the visitor switches it off, and the button turns it back on', () => {
        cy.visit('/', { onBeforeLoad: (win) => stubMedia(win, { blocked: false }) });
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'true').click();
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'false');
        cy.window().its('localStorage').invoke('getItem', 'mia-music').should('eq', 'off');

        cy.visit('/en/', { onBeforeLoad: (win) => stubMedia(win, { blocked: false }) });
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'false');
        cy.get('h1').click();
        cy.get('@play').should('not.have.been.called');

        cy.get('#audio-toggle').click();
        cy.get('#audio-toggle').should('have.attr', 'aria-pressed', 'true');
        cy.window().its('localStorage').invoke('getItem', 'mia-music').should('be.null');
    });
});
