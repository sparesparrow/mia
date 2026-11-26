// Cypress end-to-end tests for the published MIA site (REQ-WEB-001 to REQ-WEB-005).
// Local runs need the site assembled the way the publish-pages workflow does it and served on
// port 8080 (see web/README.md, "Browser tests"). cypress/e2e/prod-smoke.cy.js is read-only and only
// runs against an https baseUrl, for example:
//   npx cypress run --config baseUrl=https://mia-suzmatra.vercel.app --spec cypress/e2e/prod-smoke.cy.js
const { defineConfig } = require('cypress');

module.exports = defineConfig({
    e2e: {
        baseUrl: 'http://localhost:8080',
        specPattern: 'cypress/e2e/**/*.cy.js',
        supportFile: 'cypress/support/e2e.js',
        video: false,
        screenshotOnRunFailure: true,
        defaultCommandTimeout: 10000,
        requestTimeout: 10000,
        responseTimeout: 15000,
        viewportWidth: 1280,
        viewportHeight: 800
    }
});
