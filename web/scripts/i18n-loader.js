// Universal i18n Loader for AI-SERVIS Web Pages
// Loads YAML translation files and provides i18n functionality

class I18nLoader {
    constructor() {
        this.translations = {};
        this.currentLanguage = 'cs';
        this.loadedNamespaces = new Set();
        this.defaultNamespace = this.detectNamespace();
    }

    detectNamespace() {
        // Detect namespace from current page
        const path = window.location.pathname;
        if (path.includes('business')) return 'business';
        if (path.includes('family')) return 'family';
        if (path.includes('musicians')) return 'musicians';
        if (path.includes('journalists')) return 'journalists';
        return 'common';
    }

    async loadTranslations() {
        try {
            // Load common translations
            await this.loadNamespace('common', './i18n/common.yaml');
            
            // Load page-specific translations
            if (this.defaultNamespace !== 'common') {
                await this.loadNamespace(this.defaultNamespace, `./i18n/${this.defaultNamespace}.yaml`);
            }
            
            console.log('Translations loaded successfully');
            this.initializePage();
        } catch (error) {
            console.error('Failed to load translations:', error);
            this.fallbackToHardcoded();
        }
    }

    async loadNamespace(namespace, url) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to load ${url}: ${response.status}`);
            }
            
            const yamlText = await response.text();
            const yamlData = this.parseYAML(yamlText);
            
            this.translations[namespace] = yamlData[namespace];
            this.loadedNamespaces.add(namespace);
            
            console.log(`Loaded namespace: ${namespace}`);
        } catch (error) {
            console.error(`Failed to load namespace ${namespace}:`, error);
            throw error;
        }
    }

    parseYAML(yamlText) {
        // Simple YAML parser for our specific format
        const lines = yamlText.split('\n');
        const result = {};
        let currentSection = null;
        let currentSubsection = null;
        let currentKey = null;
        let indentLevel = 0;
        let currentPath = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            
            if (!trimmedLine || trimmedLine.startsWith('#')) {
                continue;
            }

            const currentIndent = line.length - line.trimStart().length;
            const isKeyValue = trimmedLine.includes(':') && !trimmedLine.endsWith(':');
            
            if (isKeyValue) {
                const [key, ...valueParts] = trimmedLine.split(':');
                const value = valueParts.join(':').trim();
                
                if (currentIndent === 0) {
                    // Top-level section
                    currentSection = key.trim();
                    if (!result[currentSection]) {
                        result[currentSection] = {};
                    }
                    currentPath = [currentSection];
                } else if (currentIndent === 2) {
                    // Second level
                    currentSubsection = key.trim();
                    if (!result[currentSection][currentSubsection]) {
                        result[currentSection][currentSubsection] = {};
                    }
                    currentPath = [currentSection, currentSubsection];
                } else if (currentIndent === 4) {
                    // Third level
                    currentKey = key.trim();
                    if (!result[currentSection][currentSubsection][currentKey]) {
                        result[currentSection][currentSubsection][currentKey] = {};
                    }
                    currentPath = [currentSection, currentSubsection, currentKey];
                } else if (currentIndent === 6) {
                    // Fourth level - language values
                    const langKey = key.trim();
                    const langValue = value.replace(/^["']|["']$/g, ''); // Remove quotes
                    
                    if (!result[currentSection][currentSubsection][currentKey][langKey]) {
                        result[currentSection][currentSubsection][currentKey][langKey] = langValue;
                    }
                }
            }
        }

        return result;
    }

    t(key, namespace = null, params = {}) {
        const targetNamespace = namespace || this.defaultNamespace;
        const keys = key.split('.');
        let value = this.translations[targetNamespace];

        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k];
            } else {
                console.warn(`Translation key not found: ${targetNamespace}.${key}`);
                return key; // Return the key if translation not found
            }
        }

        if (typeof value === 'object' && value[this.currentLanguage]) {
            let translation = value[this.currentLanguage];
            
            // Replace parameters
            Object.keys(params).forEach(param => {
                translation = translation.replace(`{${param}}`, params[param]);
            });
            
            return translation;
        }

        console.warn(`Translation not found for language ${this.currentLanguage}: ${targetNamespace}.${key}`);
        return key;
    }

    switchLanguage(lang) {
        this.currentLanguage = lang;
        this.updatePageContent();
        localStorage.setItem('preferred-language', lang);
    }

    updatePageContent() {
        // Update all elements with data-i18n attributes
        const elements = document.querySelectorAll('[data-i18n]');
        
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const namespace = element.getAttribute('data-i18n-ns') || this.defaultNamespace;
            
            if (key) {
                const translation = this.t(key, namespace);
                
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    element.placeholder = translation;
                } else if (element.tagName === 'IMG') {
                    element.alt = translation;
                } else if (element.hasAttribute('title')) {
                    element.title = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });

        // Update document title and meta description
        const titleElement = document.querySelector('title[data-i18n]');
        if (titleElement) {
            document.title = this.t(titleElement.getAttribute('data-i18n'), titleElement.getAttribute('data-i18n-ns'));
        }

        const metaDesc = document.querySelector('meta[name="description"][data-i18n]');
        if (metaDesc) {
            metaDesc.content = this.t(metaDesc.getAttribute('data-i18n'), metaDesc.getAttribute('data-i18n-ns'));
        }
    }

    initializePage() {
        // Set initial language
        const savedLang = localStorage.getItem('preferred-language') || 'cs';
        this.currentLanguage = savedLang;
        
        // Update language switcher buttons
        const langButtons = document.querySelectorAll('.lang-btn');
        langButtons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-lang') === savedLang) {
                btn.classList.add('active');
            }
        });

        // Update page content
        this.updatePageContent();
    }

    fallbackToHardcoded() {
        console.log('Using hardcoded translations as fallback');
        // This would contain hardcoded translations as a fallback
        // For now, we'll just log the error and continue
    }
}

// Global i18n instance
window.i18n = new I18nLoader();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.i18n.loadTranslations();
});

// Language switcher function
function switchLanguage(lang) {
    window.i18n.switchLanguage(lang);
}
