// Smoke test for the MIA web page generator.
// @req REQ-WEB-001 REQ-WEB-002 REQ-WEB-003
//
// Run via `npm test` (which calls `npm run build` first via the `pretest`
// hook). CI runs it in .github/workflows/publish-pages.yml. Exit code 0 means
// success.
//
// Checks performed:
//   1. Every audience page exists in Czech (<page>/index.html) and English
//      (<page>/en/index.html) and is non-empty.
//   2. No page contains a leftover `{{...}}` template placeholder.
//   3. No page uses the old AI-SERVIS name, or shows prices or the unsourced
//      performance figures removed under REQ-WEB-002.
//   4. Each page links to its other language, to the documentation, and to every
//      audience (customer segments, professional aliases and the press kit).
//   5. Old flat URLs (customers/<segment>.html) and the professional aliases
//      redirect to the right place.
//   6. Every local stylesheet and image a page references exists in dist/.
//   7. No page carries the old prototype status banner, and on every segment page the
//      use cases (#scenarios) come before "what works today" (#today).
//   8. The hand-written homepage (web/index.html) offers the three voice guides: a crew
//      section with one card per guide, a distinct agent ID for each, one widget mount
//      point, the embed script and the cloud disclosure (REQ-WEB-003).

'use strict';

const fs = require('fs');
const path = require('path');

const WEB_ROOT = path.resolve(__dirname, '..');
const DIST = path.join(WEB_ROOT, 'dist');
const SEGMENTS = ['business', 'family', 'musicians', 'journalists'];
const PAGES = [...SEGMENTS, 'press'];
const ROLE_REDIRECTS = {
    developers: '../docs/for/developers/',
    mechanics: '../docs/for/mechanics/',
    testers: '../docs/for/testers/'
};
const FORBIDDEN = [
    { pattern: /AI-SERVIS/i, label: 'old AI-SERVIS name' },
    { pattern: /Kč|\bCZK\b|€/, label: 'prices' },
    { pattern: /\b(300|93|70-93)\s?%/, label: 'unsourced percentages' },
    { pattern: /id="pricing"|href="#pricing"/, label: 'pricing section' }
];
// Text that may legitimately mention the old name (the press kit explains the rename).
const ALLOWED_OLD_NAME = /dříve pod názvem AI-SERVIS|previously called AI-SERVIS|starý název AI-SERVIS|old AI-SERVIS name/g;

let failures = 0;

function fail(message) {
    failures += 1;
    console.error(`  ✗ ${message}`);
}

function pass(message) {
    console.log(`  ✓ ${message}`);
}

function check(condition, message) {
    if (condition) {
        pass(message);
    } else {
        fail(message);
    }
}

function read(relPath) {
    try {
        return fs.readFileSync(path.join(DIST, relPath), 'utf8');
    } catch (_err) {
        return '';
    }
}

console.log('Smoke test: MIA web build');
console.log(`  dist: ${DIST}`);

for (const page of PAGES) {
    for (const [lang, rel] of [['cs', `${page}/index.html`], ['en', `${page}/en/index.html`]]) {
        const html = read(rel);
        // 1. Exists.
        check(html.length > 0, `${rel} exists and is non-empty`);
        if (!html) {
            continue;
        }
        check(html.includes(`<html lang="${lang}">`), `${rel} declares lang="${lang}"`);

        // 2. No unrendered placeholders.
        const placeholders = html.match(/\{\{[^}]+\}\}/g) || [];
        check(placeholders.length === 0,
            `${rel} has no unrendered {{...}} placeholders` +
                (placeholders.length ? ` (found: ${placeholders.slice(0, 3).join(', ')})` : ''));

        // 3. No old brand, prices or unsourced figures.
        const scrubbed = html.replace(ALLOWED_OLD_NAME, '');
        for (const { pattern, label } of FORBIDDEN) {
            check(!pattern.test(scrubbed), `${rel} has no ${label}`);
        }

        // 4. Links.
        const otherHref = lang === 'cs' ? 'href="en/"' : 'href="../"';
        check(html.includes(otherHref), `${rel} links to its other language (${otherHref})`);
        check(/href="(\.\.\/)+docs\/"/.test(html), `${rel} links to the documentation`);
        const audiences = [...SEGMENTS, 'press'].map((s) => `${s}/`)
            .concat(Object.values(ROLE_REDIRECTS).map((t) => t.replace('../', '')));
        const missing = audiences.filter((a) => !html.includes(`${a}"`) && !html.includes(`${a}en/"`));
        check(missing.length === 0, `${rel} links to every audience` +
            (missing.length ? ` (missing: ${missing.join(', ')})` : ''));

        // 7. No status banner; use cases before "what works today".
        check(!html.includes('status-banner'), `${rel} has no status banner`);
        if (page !== 'press') {
            const scenarios = html.indexOf('id="scenarios"');
            const today = html.indexOf('id="today"');
            check(scenarios !== -1 && today !== -1 && scenarios < today,
                `${rel} shows #scenarios before #today`);
        }

        // 6. Local assets exist.
        const pageDir = path.dirname(path.join(DIST, rel));
        const refs = [...html.matchAll(/(?:href|src)="([^"#:]+\.(?:css|jpg|png))"/g)].map((m) => m[1]);
        const broken = refs.filter((ref) => !fs.existsSync(path.resolve(pageDir, ref)));
        check(broken.length === 0, `${rel} references only existing local assets` +
            (broken.length ? ` (missing: ${broken.join(', ')})` : ''));
    }
}

// 5. Redirect stubs.
for (const segment of SEGMENTS) {
    const html = read(`customers/${segment}.html`);
    check(html.includes(`url=../${segment}/"`), `customers/${segment}.html redirects to ${segment}/`);
}
for (const [role, target] of Object.entries(ROLE_REDIRECTS)) {
    const html = read(`${role}/index.html`);
    check(html.includes(`url=${target}"`), `${role}/ redirects to ${target.replace('../', '')}`);
}

// 8. Homepage voice guides (REQ-WEB-003). The homepage is not generated, so read it from web/.
{
    let home = '';
    try {
        home = fs.readFileSync(path.join(WEB_ROOT, 'index.html'), 'utf8');
    } catch (_err) {
        home = '';
    }
    const guides = ['holly', 'rimmer', 'kryten'];
    check(home.includes('id="posadka"'), 'index.html has the crew section (#posadka)');
    const missingCards = guides.filter((g) => !home.includes(`data-crew="${g}"`));
    check(missingCards.length === 0, 'index.html has a card for every voice guide' +
        (missingCards.length ? ` (missing: ${missingCards.join(', ')})` : ''));
    const ids = guides.map((g) => (home.match(new RegExp(`${g}:\\s*'(agent_[a-z0-9]+)'`)) || [])[1]);
    check(ids.every(Boolean) && new Set(ids).size === guides.length,
        'index.html maps every voice guide to a distinct agent ID');
    check((home.match(/id="crew-widget"/g) || []).length === 1, 'index.html has one widget mount point');
    check(home.includes('https://unpkg.com/@elevenlabs/convai-widget-embed'),
        'index.html loads the widget embed script');
    check(/ElevenLabs/.test(home) && home.includes('class="crew-note"'),
        'index.html says the guides run through ElevenLabs');
}

if (failures > 0) {
    console.error(`\nSmoke test FAILED: ${failures} check(s) did not pass.`);
    process.exit(1);
}

console.log('\nSmoke test passed.');
