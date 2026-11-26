// Fails when the page scrolls sideways at the current viewport.
Cypress.Commands.add('assertNoHorizontalOverflow', () => {
    cy.document().then((doc) => {
        const root = doc.documentElement;
        expect(root.scrollWidth, 'document width').to.be.at.most(root.clientWidth + 1);
    });
});

// Fetches every same-origin href or src on the page that is not an in-page anchor and expects a 200.
Cypress.Commands.add('assertLocalLinksResolve', (selector = 'a[href], link[href], img[src], script[src]') => {
    cy.location('origin').then((origin) => {
        cy.get(selector).then(($els) => {
            const urls = [...new Set($els.toArray()
                .map((el) => el.href || el.src)
                .filter((url) => url && url.startsWith(origin) && !url.includes('#'))
                // MkDocs is built by a separate job and is not part of the local preview.
                .filter((url) => !new URL(url).pathname.includes('/docs/')))];
            urls.forEach((url) => {
                cy.request({ url, failOnStatusCode: false }).then((res) => expect(res.status, url).to.eq(200));
            });
        });
    });
});
