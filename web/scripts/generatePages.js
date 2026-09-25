// Generates the audience landing pages and the press kit for the published site.
//
// Every page is rendered once per language: Czech at <page>/index.html and English
// at <page>/en/index.html, so the language switch is a plain link and the pages
// need no runtime i18n. Old flat URLs (customers/<segment>.html) and the short
// professional aliases (developers/, mechanics/, testers/) become redirect stubs.
//
// Output goes to dist/, which .github/workflows/publish-pages.yml copies to the
// site root. See web/README.md for the full site map.

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const WEB_ROOT = path.join(__dirname, '..');
const distDir = path.join(WEB_ROOT, 'dist');
const SITE_URL = 'https://sparesparrow.github.io/mia/';
const LANGUAGES = ['cs', 'en'];
const DEFAULT_LANGUAGE = 'cs';
const PILOT_URL = 'https://github.com/sparesparrow/mia/issues/new?title=';

fs.mkdirSync(distDir, { recursive: true });

const pageTemplate = fs.readFileSync(path.join(WEB_ROOT, 'template.html'), 'utf8');
const pressTemplate = fs.readFileSync(path.join(WEB_ROOT, 'press-template.html'), 'utf8');

function loadYaml(file) {
    return yaml.load(fs.readFileSync(path.join(WEB_ROOT, 'i18n', file), 'utf8'));
}

const site = loadYaml('site.yaml').site;

// Segment pages. Text paths point into the segment's YAML namespace; each scenario
// has a title and either bullet `items` or a `text` paragraph.
const segments = [
    {
        name: 'business',
        yamlFile: 'business.yaml',
        stylesheet: 'customers/business/styles.css',
        heroImage: 'business.jpg',
        tagline: 'navigation.business_intelligence_on_wheels',
        heroTitle: 'hero.aipowered_business_vehicle_intelligence',
        heroSubtitle: 'page.description',
        scenariosTitle: 'solutions.business_solutions',
        scenarios: [
            {
                title: 'solutions.sales_teams',
                items: ['solutions.handsfree_crm_access', 'solutions.voicetotext_meeting_notes',
                    'solutions.lead_tracking_and_routing', 'solutions.territory_optimization']
            },
            {
                title: 'solutions.field_service_professionals',
                items: ['solutions.job_dispatch_integration', 'solutions.voiceactivated_checklists',
                    'solutions.realtime_eta_updates', 'solutions.service_report_generation']
            },
            {
                title: 'solutions.executive_transportation',
                items: ['solutions.secure_voice_encryption', 'solutions.executive_calendar_sync',
                    'solutions.document_voice_review', 'solutions.privacyfirst_design']
            }
        ],
        pilotTitle: 'cta.ready_to_transform_your_business_fleet'
    },
    {
        name: 'family',
        yamlFile: 'family.yaml',
        stylesheet: 'customers/family/styles.css',
        heroImage: 'family.jpg',
        tagline: 'navigation.family_protection_first',
        heroTitle: 'hero.comprehensive_family_safety',
        heroSubtitle: 'page.description',
        scenariosTitle: 'content.protection_scenarios',
        scenarios: [
            {
                title: 'scenarios.parent_child_safety',
                items: ['scenarios.teen_driver_monitoring', 'scenarios.family_arrival_notifications',
                    'scenarios.safe_driving_alerts', 'scenarios.emergency_contact_system']
            },
            {
                title: 'scenarios.partner_safety',
                items: ['scenarios.coupled_location_sharing', 'scenarios.mutual_safety_alerts',
                    'scenarios.trusted_partner_network', 'scenarios.privacy_controls']
            },
            {
                title: 'scenarios.senior_family_care',
                items: ['scenarios.independence_monitoring', 'scenarios.health_safety_alerts',
                    'scenarios.battery_system_monitoring', 'scenarios.trusted_caregiver_network']
            }
        ],
        pilotTitle: 'cta.give_your_family_the_protection_they_deserve'
    },
    {
        name: 'musicians',
        yamlFile: 'musicians.yaml',
        stylesheet: 'customers/musicians/styles.css',
        heroImage: 'mobile-dj.jpg',
        bodyClass: 'theme-dark',
        tagline: 'navigation.mobile_music_revolution',
        heroTitle: 'hero.studiograde_features',
        heroSubtitle: 'page.description',
        scenariosTitle: 'navigation.performances',
        scenarios: [
            {
                title: 'features.mobile_dj_revolution',
                items: ['features.remote_deck_synchronization', 'features.live_streaming_capabilities',
                    'features.multicar_collaboration', 'features.emergency_backup_systems']
            },
            {
                title: 'features.band_collaboration',
                items: ['features.realtime_audio_sync', 'features.distributed_recording',
                    'features.cloud_collaboration', 'features.mobile_mixing_desk']
            },
            {
                title: 'features.solo_artist_freedom',
                items: ['features.creative_access_247', 'features.instant_recording_setup',
                    'features.mobile_performance_rig', 'features.creative_freedom']
            }
        ],
        pilotTitle: 'cta.ready_to_make_music_everywhere'
    },
    {
        name: 'journalists',
        yamlFile: 'gonzo.yaml',
        namespace: 'journalists',
        stylesheet: 'customers/journalists/styles.css',
        heroImage: 'investigator.jpg',
        bodyClass: 'theme-dark',
        tagline: 'navigation.gonzo_journalism',
        heroTitle: 'hero.main_title',
        heroSubtitle: 'hero.subtitle',
        scenariosTitle: 'weaponry.title',
        scenarios: [
            { title: 'weaponry.anti_stalker_protocol.title', text: 'weaponry.anti_stalker_protocol.description' },
            { title: 'weaponry.covert_ops_interface.title', text: 'weaponry.covert_ops_interface.description' },
            { title: 'weaponry.gonzo_command_center.title', text: 'weaponry.gonzo_command_center.description' },
            { title: 'weaponry.matrix_tracking_map.title', text: 'weaponry.matrix_tracking_map.description' },
            { title: 'stories.gonzo_investigator.title', text: 'stories.gonzo_investigator.description' },
            { title: 'stories.mobile_dj_revolution.title', text: 'stories.mobile_dj_revolution.description' }
        ],
        pilotTitle: 'cta.ready_to_investigate'
    }
];

// Short aliases for the professional audiences; their content lives in MkDocs.
const roleRedirects = {
    developers: 'docs/for/developers/',
    mechanics: 'docs/for/mechanics/',
    testers: 'docs/for/testers/'
};

const pressImages = [
    'telemetry-flow.jpg', 'pi-wiring.jpg', 'business.jpg', 'family.jpg',
    'hero-dashboard.jpg', 'investigator.jpg', 'mobile-dj.jpg', 'command-center.jpg'
];

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function getPath(obj, dotted) {
    return dotted.split('.').reduce((node, key) => (node == null ? undefined : node[key]), obj);
}

// Resolve a {cs, en} entry. A missing key or language fails the build rather than
// shipping a raw key or the wrong language.
function tr(entry, lang, where) {
    if (!entry || typeof entry !== 'object' || typeof entry[lang] !== 'string') {
        throw new Error(`Missing ${lang} text for ${where}`);
    }
    return entry[lang];
}

function textAt(data, dotted, lang, where) {
    return tr(getPath(data, dotted), lang, `${where}.${dotted}`);
}

// {{name}} placeholders only; values are inserted as-is, so callers escape text
// and pass ready-made HTML for the repeated blocks.
function renderTemplate(template, values) {
    return template.replace(/\{\{([a-z_]+)\}\}/g, (match, key) => {
        if (!(key in values)) {
            throw new Error(`Template placeholder {{${key}}} has no value`);
        }
        return values[key];
    });
}

function langSuffix(lang) {
    return lang === DEFAULT_LANGUAGE ? '' : `${lang}/`;
}

function otherLanguage(lang) {
    return lang === 'cs' ? 'en' : 'cs';
}

// Path from a page in <dir>/<lang suffix> back to the site root.
function rootFor(lang) {
    return lang === DEFAULT_LANGUAGE ? '../' : '../../';
}

function writeFile(relPath, content) {
    const target = path.join(distDir, relPath);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content);
    console.log(`✓ Wrote ${relPath}`);
}

function copyFile(srcRel, destRel) {
    const target = path.join(distDir, destRel);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(path.join(WEB_ROOT, srcRel), target);
}

function redirectPage(target) {
    const href = escapeHtml(target);
    return `<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="robots" content="noindex">
    <meta http-equiv="refresh" content="0; url=${href}">
    <link rel="canonical" href="${href}">
    <title>MIA</title>
</head>
<body>
    <p><a href="${href}">MIA</a></p>
</body>
</html>
`;
}

function sharedValues(lang, pageDir) {
    const root = rootFor(lang);
    const other = otherLanguage(lang);
    const t = (entry, where) => escapeHtml(tr(entry, lang, `site.${where}`));
    const audience = (name) => t(site.audiences[name], `audiences.${name}`);
    const suffix = langSuffix(lang);

    const customerLinks = segments
        .map((s) => `<li><a href="${root}${s.name}/${suffix}">${audience(s.name)}</a></li>`)
        .join('');
    const professionalLinks = Object.keys(roleRedirects)
        .map((role) => `<li><a href="${root}${roleRedirects[role]}">${audience(role)}</a></li>`)
        .concat(`<li><a href="${root}press/${suffix}">${audience('press')}</a></li>`)
        .join('');
    const projectLinks = [
        `<li><a href="${root}">${t(site.footer.manifesto, 'footer.manifesto')}</a></li>`,
        `<li><a href="${root}docs/">${t(site.footer.documentation, 'footer.documentation')}</a></li>`,
        `<li><a href="https://github.com/sparesparrow/mia">${t(site.footer.source, 'footer.source')}</a></li>`
    ].join('');

    const column = (title, links) =>
        `<div class="footer-column"><h4>${title}</h4><ul>${links}</ul></div>`;

    return {
        lang,
        root,
        lang_suffix: suffix,
        other_lang: other,
        other_lang_href: lang === DEFAULT_LANGUAGE ? `${other}/` : '../',
        canonical: `${SITE_URL}${pageDir}/${suffix}`,
        url_cs: `${SITE_URL}${pageDir}/`,
        url_en: `${SITE_URL}${pageDir}/en/`,
        language_switch: t(site.language_switch, 'language_switch'),
        status_banner: t(site.status_banner, 'status_banner'),
        site_tagline: t(site.tagline, 'tagline'),
        nav_all_pages: t(site.nav.all_pages, 'nav.all_pages'),
        docs_button: t(site.pilot.docs, 'pilot.docs'),
        today_title: t(site.today.title, 'today.title'),
        today_link: t(site.today.link, 'today.link'),
        copyright: t(site.footer.copyright, 'footer.copyright'),
        footer_html: [
            column(t(site.footer.customers, 'footer.customers'), customerLinks),
            column(t(site.footer.professionals, 'footer.professionals'), professionalLinks),
            column(t(site.footer.project, 'footer.project'), projectLinks)
        ].join('\n                    ')
    };
}

function renderSegment(segment, lang) {
    const data = loadYaml(segment.yamlFile)[segment.namespace || segment.name];
    const where = segment.name;
    const text = (dotted) => escapeHtml(textAt(data, dotted, lang, where));
    const t = (entry, name) => escapeHtml(tr(entry, lang, `site.${name}`));

    const card = (icon, title, body) =>
        `<div class="feature-card"><div class="feature-icon"><i class="${icon}" aria-hidden="true"></i></div>` +
        `<h3>${title}</h3>${body}</div>`;
    const todayIcons = ['fas fa-gauge-high', 'fas fa-car', 'fas fa-id-card', 'fas fa-microphone',
        'fas fa-mobile-screen', 'fas fa-microchip'];

    const values = Object.assign(sharedValues(lang, segment.name), {
        segment: segment.name,
        body_class: segment.bodyClass || '',
        segment_base: lang === DEFAULT_LANGUAGE ? '' : '../',
        title: `${text('page.title')}`,
        description: text('page.description'),
        tagline: text(segment.tagline),
        hero_image: segment.heroImage,
        hero_title: text(segment.heroTitle),
        hero_subtitle: text(segment.heroSubtitle),
        facts_html: site.facts
            .map((fact, i) => `<li>${t(fact, `facts.${i}`)}</li>`)
            .join('\n                    '),
        nav_today: t(site.nav.today, 'nav.today'),
        nav_scenarios: t(site.nav.scenarios, 'nav.scenarios'),
        nav_technology: t(site.nav.technology, 'nav.technology'),
        nav_pilot: t(site.nav.pilot, 'nav.pilot'),
        today_intro: t(site.today.intro, 'today.intro'),
        today_html: site.today.items
            .map((item, i) => card(todayIcons[i % todayIcons.length],
                t(item.title, `today.items.${i}.title`),
                `<p>${t(item.text, `today.items.${i}.text`)}</p>`))
            .join('\n                '),
        scenarios_label: t(site.scenarios.label, 'scenarios.label'),
        scenarios_title: text(segment.scenariosTitle),
        scenarios_note: t(site.scenarios.note, 'scenarios.note'),
        scenarios_html: segment.scenarios
            .map((scenario) => {
                const body = scenario.items
                    ? `<ul>${scenario.items.map((item) => `<li>${text(item)}</li>`).join('')}</ul>`
                    : `<p>${text(scenario.text)}</p>`;
                return card('fas fa-route', text(scenario.title), body);
            })
            .join('\n                '),
        technology_title: t(site.technology.title, 'technology.title'),
        technology_html: site.technology.items
            .map((item, i) =>
                `<div class="tech-card"><h3>${t(item.title, `technology.items.${i}.title`)}</h3>` +
                `<p>${t(item.text, `technology.items.${i}.text`)}</p></div>`)
            .join('\n                '),
        pilot_title: text(segment.pilotTitle),
        pilot_text: t(site.pilot.text, 'pilot.text'),
        pilot_button: t(site.pilot.button, 'pilot.button'),
        pilot_href: escapeHtml(PILOT_URL + encodeURIComponent(`Pilot: ${segment.name}`))
    });

    return renderTemplate(pageTemplate, values);
}

function renderPress(lang) {
    const press = site.press;
    const t = (entry, name) => escapeHtml(tr(entry, lang, `site.press.${name}`));
    const root = rootFor(lang);

    const values = Object.assign(sharedValues(lang, 'press'), {
        title: t(press.title, 'title'),
        description: t(press.description, 'description'),
        lead: t(press.lead, 'lead'),
        facts_title: t(press.facts_title, 'facts_title'),
        facts_html: press.facts
            .map((fact, i) => `<tr><th scope="row">${t(fact.label, `facts.${i}.label`)}</th>` +
                `<td>${t(fact.value, `facts.${i}.value`)}</td></tr>`)
            .join('\n                    '),
        today_html: site.today.items
            .map((item, i) => `<li><strong>${escapeHtml(tr(item.title, lang, `today.${i}`))}.</strong> ` +
                `${escapeHtml(tr(item.text, lang, `today.${i}`))}</li>`)
            .join('\n                '),
        tone_title: t(press.tone_title, 'tone_title'),
        tone_text: t(press.tone_text, 'tone_text'),
        privacy_title: t(press.privacy_title, 'privacy_title'),
        privacy_text: t(press.privacy_text, 'privacy_text'),
        privacy_link: t(press.privacy_link, 'privacy_link'),
        images_title: t(press.images_title, 'images_title'),
        images_note: t(press.images_note, 'images_note'),
        images_html: pressImages
            .map((file) => `<a href="${root}assets/site/${file}" download>` +
                `<img src="${root}assets/site/${file}" alt="" loading="lazy"></a>`)
            .join('\n                '),
        contact_title: t(press.contact_title, 'contact_title'),
        contact_text: t(press.contact_text, 'contact_text'),
        contact_button: t(press.contact_button, 'contact_button'),
        contact_href: escapeHtml(PILOT_URL + encodeURIComponent('Press enquiry'))
    });

    return renderTemplate(pressTemplate, values);
}

for (const segment of segments) {
    console.log(`Generating ${segment.name}...`);
    for (const lang of LANGUAGES) {
        writeFile(path.join(segment.name, langSuffix(lang), 'index.html'), renderSegment(segment, lang));
    }
    copyFile(segment.stylesheet, path.join(segment.name, 'styles.css'));
    // Keep the old flat URLs working.
    writeFile(path.join('customers', `${segment.name}.html`), redirectPage(`../${segment.name}/`));
}

console.log('Generating press kit...');
for (const lang of LANGUAGES) {
    writeFile(path.join('press', langSuffix(lang), 'index.html'), renderPress(lang));
}

for (const [role, target] of Object.entries(roleRedirects)) {
    writeFile(path.join(role, 'index.html'), redirectPage(`../${target}`));
}

// Shared stylesheet and the images the pages reference, so dist/ previews on its own.
copyFile('site.css', 'site.css');
const siteAssets = path.join(WEB_ROOT, 'assets', 'site');
for (const file of fs.readdirSync(siteAssets)) {
    copyFile(path.join('assets', 'site', file), path.join('assets', 'site', file));
}

console.log('🎉 All pages generated successfully!');
