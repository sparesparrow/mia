// Smoke test for the MIA web page generator.
// @req REQ-WEB-001 REQ-WEB-002 REQ-WEB-003 REQ-WEB-004 REQ-WEB-005
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
//   8. The hand-written homepages (web/index.html, web/en/index.html) offer the three voice guides: a crew
//      section with one card per guide, a distinct agent ID for each, one widget mount
//      point, the embed script and the cloud disclosure (REQ-WEB-003).
//   9. Every published page (generated pages and the homepage) has a skip link to one
//      <main id="main">, exactly one <h1> and Open Graph tags whose image exists; the
//      homepage lazy-loads the images below the hero; robots.txt points to sitemap.xml,
//      which lists every generated page in both languages (REQ-WEB-004).
//  10. dist/vercel.json sets the security headers for the Vercel mirror, and its report-only
//      Content-Security-Policy allows the sha256 of every inline script on the site (REQ-WEB-005).
//      It also redirects /mia/... to the root, so the shared 404 page's /mia/ links work on Vercel
//      without JavaScript and from GitHub-Pages-style URLs.
//  12. Every generated page has the mobile menu toggle and a brand link to its own homepage; the press kit's download links are described
//      (alt text and an aria-label); each segment's scenario cards use more than one icon (REQ-WEB-004).
//  11. The hand-written pages (web/index.html, web/404.html) pass check 3 too; the homepage links
//      to every audience and the documentation, and the 404 page links to the homepage and every
//      audience page with /mia/ paths plus the data-path its script rewrites them from (REQ-WEB-002).

'use strict';

const crypto = require('crypto');
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
const SITE_URL = 'https://mia-suzmatra.vercel.app/';
const OG_PROPERTIES = ['og:title', 'og:description', 'og:url', 'og:image'];
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

// Width and height from a baseline or progressive JPEG's SOF marker; null if the file isn't a JPEG.
function jpegSize(file) {
    let buf;
    try {
        buf = fs.readFileSync(file);
    } catch (_err) {
        return null;
    }
    if (buf.readUInt16BE(0) !== 0xffd8) {
        return null;
    }
    for (let i = 2; i + 9 < buf.length;) {
        if (buf[i] !== 0xff) {
            return null;
        }
        const marker = buf[i + 1];
        if ([0xc0, 0xc1, 0xc2].includes(marker)) {
            return { height: buf.readUInt16BE(i + 5), width: buf.readUInt16BE(i + 7) };
        }
        i += 2 + buf.readUInt16BE(i + 2);
    }
    return null;
}

// 9. Landmarks, headings, skip link and Open Graph tags (REQ-WEB-004).
function checkStructure(rel, html) {
    const mains = html.match(/<main\b[^>]*>/g) || [];
    check(mains.length === 1 && mains[0].includes('id="main"'), `${rel} has one <main id="main">`);
    check((html.match(/<h1\b/g) || []).length === 1, `${rel} has exactly one <h1>`);
    const firstLink = (html.match(/<body\b[^>]*>[\s\S]*?(<a\b[^>]*>)/) || [])[1] || '';
    check(firstLink.includes('class="skip-link"') && firstLink.includes('href="#main"'),
        `${rel} starts with a skip link to #main`);
    const missingOg = OG_PROPERTIES.filter((prop) => !new RegExp(`<meta property="${prop}" content="[^"]+">`).test(html));
    check(missingOg.length === 0, `${rel} has Open Graph tags` +
        (missingOg.length ? ` (missing: ${missingOg.join(', ')})` : ''));
    const image = (html.match(/<meta property="og:image" content="([^"]+)">/) || [])[1] || '';
    check(image.startsWith(SITE_URL) && fs.existsSync(path.join(WEB_ROOT, image.slice(SITE_URL.length))),
        `${rel} og:image points to a published image (${image.slice(SITE_URL.length)})`);
    const size = jpegSize(path.join(WEB_ROOT, image.slice(SITE_URL.length)));
    check(size && size.width === 1200 && size.height === 630
        && html.includes('<meta property="og:image:width" content="1200">')
        && html.includes('<meta property="og:image:height" content="630">'),
    `${rel} og:image is a 1200x630 JPEG and says so` + (size ? ` (${size.width}x${size.height})` : ''));
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

        checkStructure(rel, html);

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

// 8. Homepage voice guides (REQ-WEB-003). The Czech homepage is not generated, so read it from web/; the English
// homepage (a hand-maintained translation) is copied into dist/en/ by the generator.
const readWebFile = (file) => {
    try {
        return fs.readFileSync(path.join(WEB_ROOT, file), 'utf8');
    } catch (_err) {
        return '';
    }
};
const HOMEPAGES = [['index.html', readWebFile('index.html')], ['en/index.html', read('en/index.html')]];
for (const [file, home] of HOMEPAGES) {
    const guides = ['holly', 'rimmer', 'kryten'];
    check(home.includes('id="posadka"'), `${file} has the crew section (#posadka)`);
    const missingCards = guides.filter((g) => !home.includes(`data-crew="${g}"`));
    check(missingCards.length === 0, `${file} has a card for every voice guide` +
        (missingCards.length ? ` (missing: ${missingCards.join(', ')})` : ''));
    const ids = guides.map((g) => (home.match(new RegExp(`${g}:\\s*'(agent_[a-z0-9]+)'`)) || [])[1]);
    check(ids.every(Boolean) && new Set(ids).size === guides.length,
        `${file} maps every voice guide to a distinct agent ID`);
    check((home.match(/id="crew-widget"/g) || []).length === 1, `${file} has one widget mount point`);
    check(home.includes('https://unpkg.com/@elevenlabs/convai-widget-embed'),
        `${file} loads the widget embed script`);
    check(/ElevenLabs/.test(home) && home.includes('class="crew-note"'),
        `${file} says the guides run through ElevenLabs`);
}

// 9. Homepage structure, lazy images, robots.txt and sitemap.xml (REQ-WEB-004).
{
    for (const [file, home] of HOMEPAGES) {
        checkStructure(file, home);
        // The logo and the hero image are above the fold; every other image waits until it is needed.
        const eager = (home.match(/<img\b[^>]*>/g) || [])
            .filter((img) => !/suzmatra-brand\.svg|hero-dashboard\.jpg/.test(img) && !img.includes('loading="lazy"'));
        check(eager.length === 0, `${file} lazy-loads every image below the hero` +
            (eager.length ? ` (eager: ${eager.length})` : ''));
    }
    const [csHome, enHome] = HOMEPAGES.map(([, html]) => html);
    check(csHome.includes('href="en/"') && csHome.includes(`hreflang="en" href="${SITE_URL}en/"`),
        'index.html links to the English homepage');
    check(enHome.includes('<html lang="en"') && enHome.includes('href="../"')
        && enHome.includes(`hreflang="cs" href="${SITE_URL}"`) && enHome.includes(`rel="canonical" href="${SITE_URL}en/"`),
    'en/index.html is English and links back to the Czech homepage');

    const robots = read('robots.txt');
    check(robots.includes(`Sitemap: ${SITE_URL}sitemap.xml`), 'robots.txt points to sitemap.xml');
    const sitemap = read('sitemap.xml');
    const expected = ['', 'en/'].concat(PAGES.flatMap((page) => [`${page}/`, `${page}/en/`]));
    const unlisted = expected.filter((rel) => !sitemap.includes(`<loc>${SITE_URL}${rel}</loc>`));
    check(sitemap.startsWith('<?xml') && unlisted.length === 0, 'sitemap.xml lists the homepage and every page' +
        (unlisted.length ? ` (missing: ${unlisted.join(', ')})` : ''));
}

// 10. Security headers for the Vercel mirror (REQ-WEB-005).
{
    let config = null;
    try {
        config = JSON.parse(read('vercel.json'));
    } catch (_err) {
        config = null;
    }
    check(config && Array.isArray(config.headers), 'vercel.json exists and has a headers list');
    const headersFor = (source) => {
        const rule = ((config && config.headers) || []).find((r) => r.source === source);
        return Object.fromEntries(((rule && rule.headers) || []).map((h) => [h.key, h.value]));
    };
    const all = headersFor('/(.*)');
    check(all['X-Content-Type-Options'] === 'nosniff', 'vercel.json sets X-Content-Type-Options: nosniff');
    check(Boolean(all['Referrer-Policy']), 'vercel.json sets a Referrer-Policy');
    check(all['X-Frame-Options'] === 'SAMEORIGIN' && /frame-ancestors 'self'/.test(all['Content-Security-Policy'] || ''),
        'vercel.json forbids framing by other sites');
    check(!/microphone/.test(all['Permissions-Policy'] || ''), 'vercel.json leaves the microphone to the voice guides');
    const reportOnly = headersFor('/((?!docs/).*)')['Content-Security-Policy-Report-Only'] || '';
    const listHtml = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => e.isDirectory()
        ? listHtml(path.join(dir, e.name))
        : (e.name.endsWith('.html') ? [path.join(dir, e.name)] : []));
    const files = listHtml(DIST).concat(['index.html', '404.html'].map((f) => path.join(WEB_ROOT, f)));
    const missingHashes = files.flatMap((file) => [...fs.readFileSync(file, 'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)]
        .map((m) => crypto.createHash('sha256').update(m[1], 'utf8').digest('base64'))
        .filter((hash) => !reportOnly.includes(`'sha256-${hash}'`))
        .map(() => path.relative(WEB_ROOT, file)));
    const redirects = (config && config.redirects) || [];
    check(redirects.some((r) => r.source === '/mia/:path(.*)' && r.destination === '/:path')
        && redirects.some((r) => r.source === '/mia' && r.destination === '/'),
    'vercel.json redirects /mia/... to the root (404 page links without JavaScript)');
    check(reportOnly.includes("script-src 'self'") && missingHashes.length === 0,
        'vercel.json report-only CSP allows every inline script' +
            (missingHashes.length ? ` (missing: ${[...new Set(missingHashes)].join(', ')})` : ''));
}

// 11. Hand-written pages (REQ-WEB-002). They are copied next to dist/ by the publish workflow, so read them
// from web/.
{
    const readWeb = (file) => {
        try {
            return fs.readFileSync(path.join(WEB_ROOT, file), 'utf8');
        } catch (_err) {
            return '';
        }
    };
    const home = readWeb('index.html');
    const enHome = read('en/index.html');
    const notFound = readWeb('404.html');
    for (const [file, html] of [['index.html', home], ['en/index.html', enHome], ['404.html', notFound]]) {
        check(html.length > 0, `${file} exists and is non-empty`);
        const scrubbed = html.replace(ALLOWED_OLD_NAME, '');
        for (const { pattern, label } of FORBIDDEN) {
            check(!pattern.test(scrubbed), `${file} has no ${label}`);
        }
    }
    const homeAudiences = PAGES.map((s) => `${s}/`)
        .concat(Object.values(ROLE_REDIRECTS).map((t) => t.replace('../', '')));
    const homeMissing = homeAudiences.filter((a) => !home.includes(`href="${a}"`) && !home.includes(`href="${a}en/"`));
    check(homeMissing.length === 0 && home.includes('href="docs/"'),
        'index.html links to every audience and the documentation' +
            (homeMissing.length ? ` (missing: ${homeMissing.join(', ')})` : ''));
    const enMissing = PAGES.map((s) => `../${s}/en/`)
        .concat(Object.values(ROLE_REDIRECTS).map((t) => t.replace('../', '../')))
        .filter((a) => !enHome.includes(`href="${a}"`));
    check(enMissing.length === 0 && enHome.includes('href="../docs/"'),
        'en/index.html links to every English audience page and the documentation' +
            (enMissing.length ? ` (missing: ${enMissing.join(', ')})` : ''));
    // 404.html is served at any depth, so it links with absolute /mia/ paths. Its inline script rewrites each
    // link from data-path to the host's base; without JavaScript, vercel.json maps /mia/... to the root.
    const notFoundMissing = ['', ...PAGES.map((s) => `${s}/`)]
        .filter((rel) => !notFound.includes(`data-path="${rel}" href="/mia/${rel}"`));
    check(notFoundMissing.length === 0, '404.html links to the homepage and every audience page' +
        (notFoundMissing.length ? ` (missing: ${notFoundMissing.map((r) => `/mia/${r}`).join(', ')})` : ''));
    const relative = [...notFound.matchAll(/(?:href|src)="([^"]+)"/g)].map((m) => m[1])
        .filter((ref) => !/^(\/mia\/|https?:|#|mailto:|data:)/.test(ref));
    check(relative.length === 0, '404.html uses only /mia/ paths for local links' +
        (relative.length ? ` (found: ${relative.join(', ')})` : ''));
}

// 12. Mobile menu, described press downloads, scenario icons (REQ-WEB-004).
for (const page of PAGES) {
    for (const rel of [`${page}/index.html`, `${page}/en/index.html`]) {
        const html = read(rel);
        check(html.includes('class="mobile-menu-toggle"') && html.includes("querySelector('.mobile-menu-toggle')"),
            `${rel} has the mobile menu toggle and its script`);
        const homeHref = rel.includes('/en/') ? '../../en/' : '../';
        check(html.includes(`<h2><a href="${homeHref}"`), `${rel} brand links to its homepage (${homeHref})`);
        if (page === 'press') {
            const links = [...html.matchAll(/<a [^>]*download[^>]*>\s*<img [^>]*>/g)].map((m) => m[0]);
            const bare = links.filter((link) => !/aria-label="[^"]{8,}"/.test(link) || /alt=""/.test(link));
            check(links.length > 0 && bare.length === 0, `${rel} describes every image download` +
                (bare.length ? ` (${bare.length} without alt text or aria-label)` : ''));
        } else {
            const scenarios = html.slice(html.indexOf('id="scenarios"'), html.indexOf('id="today"'));
            const icons = new Set([...scenarios.matchAll(/<i class="(fa[^"]+)"/g)].map((m) => m[1]));
            check(icons.size > 1, `${rel} gives its scenario cards their own icons`);
        }
    }
}

if (failures > 0) {
    console.error(`\nSmoke test FAILED: ${failures} check(s) did not pass.`);
    process.exit(1);
}

console.log('\nSmoke test passed.');
