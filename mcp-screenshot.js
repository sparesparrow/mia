const { spawn } = require('child_process');
const fs = require('fs');

// Create screenshots directory
if (!fs.existsSync('screenshots')) {
    fs.mkdirSync('screenshots');
}

// Start Playwright MCP server
const mcpServer = spawn('npx', ['@playwright/mcp', '--headless', '--output-dir', './screenshots'], {
    stdio: ['pipe', 'pipe', 'pipe']
});

// Wait a moment for server to start
setTimeout(async () => {
    const pages = [
        { name: 'business', url: 'http://localhost:8080/business.html' },
        { name: 'family', url: 'http://localhost:8080/family.html' },
        { name: 'musicians', url: 'http://localhost:8080/musicians.html' },
        { name: 'journalists', url: 'http://localhost:8080/journalists.html' }
    ];

    for (const pageInfo of pages) {
        try {
            console.log(`Taking screenshot of ${pageInfo.name}...`);
            
            // Send MCP commands to navigate and take screenshot
            const navigateCmd = {
                jsonrpc: "2.0",
                id: 1,
                method: "tools/call",
                params: {
                    name: "browser_navigate",
                    arguments: {
                        url: pageInfo.url
                    }
                }
            };
            
            const screenshotCmd = {
                jsonrpc: "2.0",
                id: 2,
                method: "tools/call",
                params: {
                    name: "browser_take_screenshot",
                    arguments: {
                        filename: `${pageInfo.name}.png`
                    }
                }
            };

            // Send commands
            mcpServer.stdin.write(JSON.stringify(navigateCmd) + '\n');
            await new Promise(resolve => setTimeout(resolve, 2000)); // Wait for navigation
            
            mcpServer.stdin.write(JSON.stringify(screenshotCmd) + '\n');
            await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for screenshot
            
            console.log(`✓ Screenshot saved: screenshots/${pageInfo.name}.png`);
        } catch (error) {
            console.error(`Error taking screenshot of ${pageInfo.name}:`, error.message);
        }
    }

    // Close MCP server
    mcpServer.kill();
    console.log('All screenshots completed!');
}, 3000);

// Handle server output
mcpServer.stdout.on('data', (data) => {
    console.log('MCP Server:', data.toString());
});

mcpServer.stderr.on('data', (data) => {
    console.error('MCP Server Error:', data.toString());
});

mcpServer.on('close', (code) => {
    console.log(`MCP Server exited with code ${code}`);
});
