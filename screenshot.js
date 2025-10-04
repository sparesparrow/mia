const puppeteer = require('puppeteer');
const path = require('path');

async function takeScreenshots() {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
    
    const pages = [
        { name: 'business', url: 'http://localhost:8080/business.html' },
        { name: 'family', url: 'http://localhost:8080/family.html' },
        { name: 'musicians', url: 'http://localhost:8080/musicians.html' },
        { name: 'journalists', url: 'http://localhost:8080/journalists.html' }
    ];
    
    for (const pageInfo of pages) {
        try {
            console.log(`Taking screenshot of ${pageInfo.name}...`);
            await page.goto(pageInfo.url, { waitUntil: 'networkidle0' });
            await page.screenshot({
                path: `screenshots/${pageInfo.name}.png`,
                fullPage: true
            });
            console.log(`✓ Screenshot saved: screenshots/${pageInfo.name}.png`);
        } catch (error) {
            console.error(`Error taking screenshot of ${pageInfo.name}:`, error.message);
        }
    }
    
    await browser.close();
    console.log('All screenshots completed!');
}

takeScreenshots().catch(console.error);
