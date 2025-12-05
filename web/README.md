# MIA Web Pages Generator

This system generates multiple web page variants from a shared template using native web technologies and GitHub Actions.

## 🏗️ Architecture

### Native Web Technologies
- **HTML Templates**: Uses native `<template>` tags and JavaScript template literals
- **No Frameworks**: Pure JavaScript, HTML, and CSS
- **YAML Configuration**: Translation files for internationalization
- **GitHub Actions**: Automated build and deployment

### File Structure
```
web/
├── template.html              # Shared HTML template
├── scripts/
│   ├── generatePages.js      # Page generation script
│   └── cleanup.js            # Cleanup script
├── i18n/                     # Translation files
│   ├── common.yaml
│   ├── business.yaml
│   ├── family.yaml
│   ├── musicians.yaml
│   └── gonzo.yaml
├── dist/                     # Generated pages (output)
│   ├── business.html
│   ├── family.html
│   ├── musicians.html
│   ├── journalists.html
│   ├── i18n-loader.js
│   ├── app.js
│   └── styles.css
└── package.json
```

## 🚀 Usage

### Local Development
```bash
cd web
npm install
npm run build
```

### GitHub Actions
The workflow automatically triggers on any commit containing changes in the `web/` directory.

## 🔧 Template System

### Template Syntax
The template uses Handlebars-like syntax:

```html
<!-- Simple variables -->
<h1>{{hero.main_title}}</h1>

<!-- Loops -->
{{#each features.items}}
<div class="feature">
    <h3>{{this.title}}</h3>
    <p>{{this.description}}</p>
</div>
{{/each}}

<!-- Nested data access -->
<p>{{footer.copyright}}</p>
```

### Data Structure
Each page variant is generated from:
1. **Common translations** (`common.yaml`)
2. **Page-specific translations** (e.g., `business.yaml`)
3. **Customer configuration** (defined in `generatePages.js`)

## 🌐 Internationalization

### Translation Files
- YAML format with nested structure
- Support for multiple languages (en, cs)
- Namespace-based organization

### Usage in Templates
```html
<span data-i18n="navigation.features" data-i18n-ns="business">Features</span>
```

### JavaScript API
```javascript
// Get translation
const text = window.i18n.t('navigation.features', 'business');

// Switch language
window.i18n.switchLanguage('en');
```

## 📦 Generated Pages

### Business Page
- **URL**: `/business.html`
- **Namespace**: `business`
- **Target**: Business professionals

### Family Page
- **URL**: `/family.html`
- **Namespace**: `family`
- **Target**: Family safety

### Musicians Page
- **URL**: `/musicians.html`
- **Namespace**: `musicians`
- **Target**: DJs and musicians

### Journalists Page
- **URL**: `/journalists.html`
- **Namespace**: `journalists`
- **Target**: Investigative journalists

## 🔄 Build Process

1. **Template Processing**: Shared template is processed with customer-specific data
2. **YAML Loading**: Translation files are loaded and parsed
3. **Page Generation**: Individual HTML files are generated
4. **Asset Copying**: Shared assets (CSS, JS) are copied to dist
5. **Cleanup**: Redundant source files are removed

## 🛠️ Customization

### Adding New Page Variants
1. Add customer configuration in `generatePages.js`
2. Create corresponding YAML translation file
3. Update the `customers` array

### Modifying Templates
Edit `template.html` to change the shared structure. All variants will inherit the changes.

### Adding Translations
Add new keys to the appropriate YAML files in the `i18n/` directory.

## 🧹 Cleanup

After build completion, the following files are automatically removed:
- Individual customer HTML files
- Individual customer JS files
- Individual customer i18n loaders
- Shared template file
- Empty directories

## 📊 Benefits

1. **No Framework Dependencies**: Uses native web technologies
2. **Automated Builds**: GitHub Actions handles everything
3. **Maintainable**: Single template, multiple variants
4. **Internationalized**: Built-in i18n support
5. **Clean Output**: Automatic cleanup of redundant files
6. **Performance**: Optimized for production

## 🔍 Troubleshooting

### Build Failures
- Check YAML syntax in translation files
- Verify customer configurations in `generatePages.js`
- Ensure all required assets exist

### Translation Issues
- Verify namespace matches between template and YAML
- Check language codes (en, cs)
- Ensure translation keys exist in YAML files

### GitHub Actions Issues
- Check workflow file syntax
- Verify file paths in scripts
- Review action logs for detailed errors
