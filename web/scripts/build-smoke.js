// Smoke test for the MIA web page generator.
//
// Run via `npm test` (which calls `npm run build` first via the `pretest`
// hook). The goal is to catch obvious regressions in scripts/generatePages.js
// without pulling in a full test framework. Exit code 0 means success.
//
// Checks performed:
//   1. Every expected segment HTML file exists and is non-empty.
//   2. The output contains no leftover `{{...}}` template placeholders.
//   3. Per-customer styles.css landed under dist/<segment>/.
//   4. i18n YAML files were copied to dist/i18n/.
//   5. The duplicate-asset-copy bug fixed in this PR did not regress: the
//      build log line for "Copied shared asset" appears at most once per
//      asset/segment (verified indirectly by checking that the legacy
//      "shared asset" log message is gone).

'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const WEB_ROOT = path.resolve(__dirname, '..');
const DIST = path.join(WEB_ROOT, 'dist');
const SEGMENTS = ['business', 'family', 'musicians', 'journalists'];
const REQUIRED_YAML = ['common.yaml', 'business.yaml', 'family.yaml',
    'musicians.yaml', 'gonzo.yaml'];

let failures = 0;

function fail(message) {
    failures += 1;
    console.error(`  \u2717 ${message}`);
}

function pass(message) {
    console.log(`  \u2713 ${message}`);
}

function check(condition, message) {
    if (condition) {
        pass(message);
    } else {
        fail(message);
    }
}

function fileNonEmpty(filePath) {
    try {
        return fs.statSync(filePath).size > 0;
    } catch (_err) {
        return false;
    }
}

console.log('Smoke test: MIA web build');
console.log(`  dist: ${DIST}`);

// 1. Segment pages exist and are non-empty.
for (const segment of SEGMENTS) {
    const page = path.join(DIST, `${segment}.html`);
    check(fileNonEmpty(page), `dist/${segment}.html exists and is non-empty`);
}

// 2. No leftover template placeholders.
for (const segment of SEGMENTS) {
    const page = path.join(DIST, `${segment}.html`);
    if (!fileNonEmpty(page)) {
        continue;
    }
    const html = fs.readFileSync(page, 'utf8');
    // The template engine uses {{...}} for vars and {{#if}}/{{#each}} for control.
    // After rendering, none should remain in the output.
    const placeholderRegex = /\{\{[^}]+\}\}/g;
    const matches = html.match(placeholderRegex) || [];
    check(
        matches.length === 0,
        `dist/${segment}.html has no unrendered {{...}} placeholders` +
            (matches.length ? ` (found: ${matches.slice(0, 3).join(', ')}\u2026)` : '')
    );
}

// 3. Per-customer styles landed under dist/<segment>/.
for (const segment of SEGMENTS) {
    const css = path.join(DIST, segment, 'styles.css');
    check(fileNonEmpty(css), `dist/${segment}/styles.css exists and is non-empty`);
}

// 4. i18n YAML files copied.
for (const yaml of REQUIRED_YAML) {
    const target = path.join(DIST, 'i18n', yaml);
    check(fileNonEmpty(target), `dist/i18n/${yaml} exists and is non-empty`);
}

// 5. Sanity-check the generator log: re-run the build capturing stdout and
// assert the duplicate "shared asset" log line is gone. This guards the
// regression fixed in this PR.
try {
    const stdout = execFileSync(
        process.execPath,
        [path.join(WEB_ROOT, 'scripts', 'generatePages.js')],
        { cwd: WEB_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }
    );
    check(
        !stdout.includes('Copied shared asset'),
        'generator log no longer emits the duplicated "Copied shared asset" line'
    );
} catch (err) {
    fail(`generator failed to re-run: ${err.message}`);
}

if (failures > 0) {
    console.error(`\nSmoke test FAILED: ${failures} check(s) did not pass.`);
    process.exit(1);
}

console.log('\nSmoke test passed.');
