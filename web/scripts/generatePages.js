const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

// Ensure dist directory exists
const distDir = path.join(__dirname, '..', 'dist');
if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
}

// Load the shared template
const templatePath = path.join(__dirname, '..', 'template.html');
const template = fs.readFileSync(templatePath, 'utf8');

// Define customer configurations
const customers = [
    {
        name: 'business',
        namespace: 'business',
        language: 'cs',
        yamlFile: 'business.yaml',
        imageDir: 'business'
    },
    {
        name: 'family',
        namespace: 'family', 
        language: 'cs',
        yamlFile: 'family.yaml',
        imageDir: 'family'
    },
    {
        name: 'musicians',
        namespace: 'musicians',
        language: 'cs', 
        yamlFile: 'musicians.yaml',
        imageDir: 'musicians'
    },
    {
        name: 'journalists',
        namespace: 'journalists',
        language: 'cs',
        yamlFile: 'gonzo.yaml',
        imageDir: 'journalists'
    }
];

// Simple template engine using Handlebars-like syntax
function renderTemplate(template, data) {
    let result = template;
    
    // Replace simple variables {{variable}}
    result = result.replace(/\{\{([^}]+)\}\}/g, (match, key) => {
        const value = getNestedValue(data, key.trim());
        return value !== undefined ? value : match;
    });
    
    // Handle {{#each}} loops
    result = result.replace(/\{\{#each\s+([^}]+)\}\}([\s\S]*?)\{\{\/each\}\}/g, (match, arrayKey, loopTemplate) => {
        const array = getNestedValue(data, arrayKey.trim());
        if (!Array.isArray(array)) return '';
        
        return array.map(item => {
            let itemTemplate = loopTemplate;
            // Replace {{this.property}} with item.property
            itemTemplate = itemTemplate.replace(/\{\{this\.([^}]+)\}\}/g, (m, prop) => {
                return getNestedValue(item, prop.trim()) || '';
            });
            // Replace {{../property}} with parent data
            itemTemplate = itemTemplate.replace(/\{\{\.\.\/([^}]+)\}\}/g, (m, prop) => {
                return getNestedValue(data, prop.trim()) || '';
            });
            return itemTemplate;
        }).join('');
    });
    
    return result;
}

function getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
        return current && current[key] !== undefined ? current[key] : undefined;
    }, obj);
}

// Load YAML data
function loadYamlData(yamlPath) {
    try {
        const yamlContent = fs.readFileSync(yamlPath, 'utf8');
        return yaml.load(yamlContent);
    } catch (error) {
        console.error(`Error loading YAML file ${yamlPath}:`, error);
        return {};
    }
}

// Generate page data structure
function generatePageData(customer, yamlData) {
    const namespace = customer.namespace;
    const data = yamlData[namespace] || {};
    
    return {
        language: customer.language,
        namespace: namespace,
        page: {
            title: data.page?.title?.[customer.language] || `${namespace} - AI-SERVIS`,
            description: data.page?.description?.[customer.language] || 'AI-SERVIS solution'
        },
        navigation: {
            main_title: data.navigation?.business_intelligence_on_wheels?.[customer.language] || 
                       data.navigation?.family_protection_first?.[customer.language] ||
                       data.navigation?.mobile_music_revolution?.[customer.language] ||
                       data.navigation?.gonzo_journalism?.[customer.language] || 'AI-SERVIS',
            features: data.navigation?.features?.[customer.language] || 'Features',
            use_cases: data.navigation?.solutions?.[customer.language] || 
                      data.navigation?.performances?.[customer.language] ||
                      data.navigation?.safety?.[customer.language] ||
                      data.navigation?.stories?.[customer.language] || 'Use Cases',
            pricing: data.navigation?.pricing?.[customer.language] || 'Pricing',
            technology: data.navigation?.technology?.[customer.language] || 'Technology',
            cta_button: data.navigation?.get_demo?.[customer.language] ||
                       data.navigation?.start_creating?.[customer.language] ||
                       data.navigation?.protect_family?.[customer.language] ||
                       data.navigation?.start_investigating?.[customer.language] || 'Get Started'
        },
        hero: {
            main_title: data.hero?.aipowered_business_vehicle_intelligence?.[customer.language] ||
                       data.hero?.comprehensive_family_safety?.[customer.language] ||
                       data.hero?.studiograde_features?.[customer.language] ||
                       data.hero?.main_title?.[customer.language] || 'AI-SERVIS',
            subtitle: data.hero?.productivity_boost?.[customer.language] ||
                     data.hero?.stalker_detection?.[customer.language] ||
                     data.hero?.rtpmidi_network?.[customer.language] ||
                     data.hero?.subtitle?.[customer.language] || 'Advanced AI Solution',
            image: `assets/${customer.imageDir}/hero-image.jpg`,
            image_alt: data.hero?.main_title?.[customer.language] || 'AI-SERVIS',
            stats: [
                {
                    value: '300%',
                    label: data.hero?.productivity_boost?.[customer.language] || 'Productivity'
                },
                {
                    value: '24/7',
                    label: data.hero?.business_hours?.[customer.language] || 'Monitoring'
                },
                {
                    value: '100%',
                    label: data.hero?.handsfree?.[customer.language] || 'Hands-Free'
                }
            ],
            primary_button: data.hero?.schedule_demo?.[customer.language] ||
                           data.hero?.start_family_protection?.[customer.language] ||
                           data.hero?.start_creating_music?.[customer.language] ||
                           data.hero?.buttons?.join_resistance?.[customer.language] || 'Get Started',
            secondary_button: data.hero?.download_brochure?.[customer.language] ||
                             data.hero?.schedule_family_demo?.[customer.language] ||
                             data.hero?.book_studio_demo?.[customer.language] ||
                             data.hero?.buttons?.watch_manifesto?.[customer.language] || 'Learn More'
        },
        features: {
            title: data.features?.professional_features?.[customer.language] ||
                   data.features?.stay_connected_stay_safe?.[customer.language] ||
                   data.features?.mobile_dj_revolution?.[customer.language] ||
                   data.features?.key_features?.[customer.language] || 'Key Features',
            items: [
                {
                    icon: 'fas fa-microphone',
                    title: data.features?.voice_ai_assistant?.[customer.language] || 'Voice AI Assistant',
                    description: data.features?.voice_assistant_description?.[customer.language] || 'Advanced voice control'
                },
                {
                    icon: 'fas fa-shield-alt',
                    title: data.features?.enterprise_security?.[customer.language] || 'Security',
                    description: data.features?.enterprise_security?.[customer.language] || 'Enterprise-grade security'
                },
                {
                    icon: 'fas fa-route',
                    title: data.features?.smart_navigation?.[customer.language] || 'Smart Navigation',
                    description: data.features?.smart_navigation?.[customer.language] || 'Intelligent routing'
                },
                {
                    icon: 'fas fa-chart-line',
                    title: data.features?.business_analytics?.[customer.language] || 'Analytics',
                    description: data.features?.business_analytics?.[customer.language] || 'Advanced analytics'
                }
            ]
        },
        use_cases: {
            title: data.solutions?.business_solutions?.[customer.language] ||
                   data.scenarios?.parent_child_safety?.[customer.language] ||
                   data.features?.mobile_dj_revolution?.[customer.language] ||
                   data.stories?.title?.[customer.language] || 'Use Cases',
            items: [
                {
                    id: 'primary-use-case',
                    layout: '',
                    title: data.solutions?.sales_teams?.[customer.language] ||
                           data.scenarios?.parent_child_safety?.[customer.language] ||
                           data.features?.mobile_dj_revolution?.[customer.language] ||
                           data.stories?.gonzo_investigator?.title?.[customer.language] || 'Primary Use Case',
                    description: data.solutions?.handsfree_crm_access?.[customer.language] ||
                               data.scenarios?.teen_driver_monitoring?.[customer.language] ||
                               data.features?.remote_deck_synchronization?.[customer.language] ||
                               data.stories?.gonzo_investigator?.description?.[customer.language] || 'Description',
                    features: [
                        data.solutions?.handsfree_crm_access?.[customer.language] || 'Feature 1',
                        data.solutions?.voicetotext_meeting_notes?.[customer.language] || 'Feature 2',
                        data.solutions?.lead_tracking_and_routing?.[customer.language] || 'Feature 3'
                    ],
                    icon: 'fas fa-handshake',
                    badge: data.solutions?.sales_excellence?.[customer.language] ||
                           data.scenarios?.parent?.[customer.language] ||
                           data.features?.live_streaming_capabilities?.[customer.language] ||
                           data.stories?.gonzo_investigator?.title?.[customer.language] || 'Badge'
                }
            ]
        },
        pricing: {
            title: data.pricing?.business_pricing?.[customer.language] ||
                   data.pricing?.family_basic?.[customer.language] ||
                   data.pricing?.studio_starter?.[customer.language] ||
                   data.pricing?.title?.[customer.language] || 'Pricing',
            plans: [
                {
                    title: data.pricing?.business_starter?.[customer.language] ||
                           data.pricing?.family_basic?.[customer.language] ||
                           data.pricing?.studio_starter?.[customer.language] ||
                           data.pricing?.phone_rebel?.title?.[customer.language] || 'Starter',
                    subtitle: data.pricing?.essential_business_features?.[customer.language] ||
                             data.pricing?.essential_family_protection?.[customer.language] ||
                             data.pricing?.essential_recording_tools?.[customer.language] ||
                             data.pricing?.phone_rebel?.description?.[customer.language] || 'Essential Features',
                    price: '35000',
                    price_range: data.pricing?.price_55000?.[customer.language] || '- 55.000',
                    features: [
                        data.pricing?.voice_assistant_calls?.[customer.language] || 'Voice Assistant',
                        data.pricing?.basic_navigation?.[customer.language] || 'Basic Navigation',
                        data.pricing?.email_integration?.[customer.language] || 'Email Integration',
                        data.pricing?.obd_diagnostics?.[customer.language] || 'OBD Diagnostics'
                    ],
                    button_text: data.pricing?.get_quote?.[customer.language] || 'Get Quote',
                    button_class: 'btn-outline'
                },
                {
                    title: data.pricing?.business_professional?.[customer.language] ||
                           data.pricing?.family_complete?.[customer.language] ||
                           data.pricing?.performance_pro?.[customer.language] ||
                           data.pricing?.hybrid_warrior?.title?.[customer.language] || 'Professional',
                    subtitle: data.pricing?.complete_business_solution?.[customer.language] ||
                             data.pricing?.full_family_safety_suite?.[customer.language] ||
                             data.pricing?.complete_mobile_studio?.[customer.language] ||
                             data.pricing?.hybrid_warrior?.description?.[customer.language] || 'Complete Solution',
                    price: '65000',
                    price_range: data.pricing?.price_105000?.[customer.language] || '- 105.000',
                    featured: 'featured',
                    badge: data.pricing?.most_popular?.[customer.language] || 'Most Popular',
                    features: [
                        data.pricing?.everything_in_starter?.[customer.language] || 'Everything in Starter',
                        data.pricing?.crm_integration?.[customer.language] || 'CRM Integration',
                        data.pricing?.advanced_navigation?.[customer.language] || 'Advanced Navigation',
                        data.pricing?.priority_support?.[customer.language] || 'Priority Support'
                    ],
                    button_text: data.pricing?.get_quote?.[customer.language] || 'Get Quote',
                    button_class: 'btn-primary'
                },
                {
                    title: data.pricing?.enterprise_fleet?.[customer.language] ||
                           data.pricing?.extended_family?.[customer.language] ||
                           data.pricing?.band_master?.[customer.language] ||
                           data.pricing?.pro_resistance?.title?.[customer.language] || 'Enterprise',
                    subtitle: data.pricing?.fleet_management_solution?.[customer.language] ||
                             data.pricing?.multigeneration_protection?.[customer.language] ||
                             data.pricing?.multiartist_collaboration?.[customer.language] ||
                             data.pricing?.pro_resistance?.description?.[customer.language] || 'Enterprise Solution',
                    price: '125000',
                    price_range: data.pricing?.price_195000?.[customer.language] || '- 195.000',
                    features: [
                        data.pricing?.everything_in_professional?.[customer.language] || 'Everything in Professional',
                        data.pricing?.fleet_management_api?.[customer.language] || 'Fleet Management API',
                        data.pricing?.advanced_anpr_tracking?.[customer.language] || 'Advanced Tracking',
                        data.pricing?.dedicated_support?.[customer.language] || 'Dedicated Support'
                    ],
                    button_text: data.pricing?.contact_sales?.[customer.language] || 'Contact Sales',
                    button_class: 'btn-outline'
                }
            ]
        },
        technology: {
            title: data.technology?.enterprise_technology?.[customer.language] ||
                   data.technology?.cuttingedge_technology?.[customer.language] || 'Technology',
            items: [
                {
                    title: data.technology?.enterprise_security?.[customer.language] || 'Security',
                    description: data.technology?.api_integration?.[customer.language] || 'Advanced security features'
                },
                {
                    title: data.technology?.api_integration?.[customer.language] || 'API Integration',
                    description: data.technology?.fleet_management?.[customer.language] || 'Seamless integration'
                },
                {
                    title: data.technology?.fleet_management?.[customer.language] || 'Management',
                    description: data.technology?.reliability_247?.[customer.language] || 'Centralized management'
                },
                {
                    title: data.technology?.reliability_247?.[customer.language] || 'Reliability',
                    description: data.technology?.reliability_247?.[customer.language] || '24/7 reliability'
                }
            ]
        },
        cta: {
            title: data.cta?.ready_to_transform_your_business_fleet?.[customer.language] ||
                   data.cta?.give_your_family_the_protection_they_deserve?.[customer.language] ||
                   data.cta?.ready_to_make_music_everywhere?.[customer.language] ||
                   data.cta?.ready_to_investigate?.[customer.language] || 'Ready to Get Started?',
            description: data.cta?.join_the_revolution?.[customer.language] || 'Join the AI revolution',
            primary_button: data.cta?.schedule_enterprise_demo?.[customer.language] ||
                           data.cta?.start_family_protection?.[customer.language] ||
                           data.cta?.start_creating_music?.[customer.language] ||
                           data.cta?.start_investigative_journalism?.[customer.language] || 'Get Started',
            secondary_button: data.cta?.download_case_studies?.[customer.language] ||
                             data.cta?.schedule_family_demo?.[customer.language] ||
                             data.cta?.book_studio_demo?.[customer.language] ||
                             data.cta?.book_surveillance_demo?.[customer.language] || 'Learn More'
        },
        footer: {
            brand: {
                subtitle: data.footer?.brand?.subtitle?.[customer.language] || 'AI-SERVIS Solution'
            },
            links: [
                {
                    title: data.footer?.product?.[customer.language] || 'Product',
                    items: [
                        { text: data.footer?.documentation?.[customer.language] || 'Documentation', url: '#' },
                        { text: data.footer?.support?.[customer.language] || 'Support', url: '#' },
                        { text: data.footer?.help_center?.[customer.language] || 'Help Center', url: '#' }
                    ]
                },
                {
                    title: data.footer?.company?.[customer.language] || 'Company',
                    items: [
                        { text: data.footer?.about?.[customer.language] || 'About', url: '#' },
                        { text: data.footer?.blog?.[customer.language] || 'Blog', url: '#' },
                        { text: data.footer?.careers?.[customer.language] || 'Careers', url: '#' }
                    ]
                }
            ],
            copyright: data.footer?.copyright?.[customer.language] || '© 2025 AI-SERVIS. All rights reserved.'
        }
    };
}

// Copy shared assets
const assetsToCopy = [
    'styles.css',
    'app.js',
    'i18n-loader.js'
];

// Generate pages for each customer
customers.forEach(customer => {
    console.log(`Generating page for ${customer.name}...`);
    
    // Load YAML data
    const yamlPath = path.join(__dirname, '..', 'i18n', customer.yamlFile);
    const yamlData = loadYamlData(yamlPath);
    
    // Generate page data
    const pageData = generatePageData(customer, yamlData);
    
    // Render template
    const html = renderTemplate(template, pageData);
    
    // Write to dist directory
    const outputPath = path.join(distDir, `${customer.name}.html`);
    fs.writeFileSync(outputPath, html);
    
    console.log(`✓ Generated ${customer.name}.html`);

    // Copy customer-specific assets
    assetsToCopy.forEach(asset => {
        const sourcePath = path.join(__dirname, '..', 'customers', `${customer.name}`, asset);
        const destPath = path.join(distDir, `${customer.name}`, asset);
        
        if (fs.existsSync(sourcePath)) {
            // Ensure destination directory exists
            fs.mkdirSync(path.dirname(destPath), { recursive: true });
            fs.copyFileSync(sourcePath, destPath);
            console.log(`✓ Copied ${asset}`);
        }
    });

    // Copy shared assets from web/assets to dist/customer/
    const sharedAssetsDir = path.join(__dirname, '..', 'assets');
    const destAssetsDir = path.join(distDir, `${customer.name}`, 'assets');

    const custAssetsDir = path.join(__dirname, '..', 'assets', `${customer.name}`);
    if (fs.existsSync(custAssetsDir)) {
        // Ensure destination directory exists
        fs.mkdirSync(destAssetsDir, { recursive: true });
        fs.readdirSync(custAssetsDir).forEach(assetFile => {
            const assetSourcePath = path.join(custAssetsDir, assetFile);
            const assetDestPath = path.join(destAssetsDir, assetFile);
            if (fs.statSync(assetSourcePath).isFile()) {
                fs.copyFileSync(assetSourcePath, assetDestPath);
                console.log(`✓ Copied shared asset ${assetFile} to ${customer.name}/assets/`);
            }
        });
    }

    if (fs.existsSync(custAssetsDir)) {
        // Ensure destination directory exists
        fs.mkdirSync(destAssetsDir, { recursive: true });
        fs.readdirSync(custAssetsDir).forEach(assetFile => {
            const assetSourcePath = path.join(custAssetsDir, assetFile);
            const assetDestPath = path.join(destAssetsDir, assetFile);
            if (fs.statSync(assetSourcePath).isFile()) {
                fs.copyFileSync(assetSourcePath, assetDestPath);
                console.log(`✓ Copied customer asset ${assetFile} to ${customer.name}/assets/`);
            }
        });
    }
});


// Copy i18n files
const i18nSourceDir = path.join(__dirname, '..', 'i18n');
const i18nDestDir = path.join(distDir, 'i18n');

if (!fs.existsSync(i18nDestDir)) {
    fs.mkdirSync(i18nDestDir, { recursive: true });
}

fs.readdirSync(i18nSourceDir).forEach(file => {
    if (file.endsWith('.yaml')) {
        const sourcePath = path.join(i18nSourceDir, file);
        const destPath = path.join(i18nDestDir, file);
        fs.copyFileSync(sourcePath, destPath);
        console.log(`✓ Copied i18n/${file}`);
    }
});

console.log('🎉 All pages generated successfully!');
