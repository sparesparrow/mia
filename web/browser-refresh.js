#!/usr/bin/env node
/**
 * Browser Refresh Script for Gonzo Monitor
 * Provides advanced browser automation for auto-refresh functionality
 */

const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

class BrowserRefresher {
    constructor(options = {}) {
        this.url = options.url || 'http://localhost:8080';
        this.browser = options.browser || 'default';
        this.refreshInterval = options.refreshInterval || 600000; // 10 minutes
        this.autoRefresh = options.autoRefresh || false;
        this.refreshCount = 0;
    }

    /**
     * Open browser with the specified URL
     */
    openBrowser() {
        const commands = {
            'chrome': `google-chrome --new-window "${this.url}"`,
            'firefox': `firefox --new-window "${this.url}"`,
            'safari': `open -a Safari "${this.url}"`,
            'edge': `microsoft-edge --new-window "${this.url}"`,
            'default': `xdg-open "${this.url}"` // Linux default
        };

        const command = commands[this.browser] || commands.default;
        
        console.log(`🌐 Opening browser: ${this.url}`);
        
        exec(command, (error, stdout, stderr) => {
            if (error) {
                console.error(`❌ Error opening browser: ${error.message}`);
                return;
            }
            if (stderr) {
                console.log(`Browser stderr: ${stderr}`);
            }
            console.log(`✅ Browser opened successfully`);
        });
    }

    /**
     * Refresh the browser page
     */
    refreshPage() {
        this.refreshCount++;
        console.log(`🔄 Refreshing page (refresh #${this.refreshCount}) at ${new Date().toLocaleTimeString()}`);
        
        // Try different methods to refresh the page
        this.tryRefreshMethods();
    }

    /**
     * Try different methods to refresh the browser
     */
    tryRefreshMethods() {
        // Method 1: Send refresh signal via HTTP request
        this.sendRefreshSignal();
        
        // Method 2: Use xdotool to send F5 key (Linux)
        this.sendKeyboardRefresh();
        
        // Method 3: Use AppleScript to refresh (macOS)
        this.sendAppleScriptRefresh();
    }

    /**
     * Send refresh signal via HTTP request
     */
    sendRefreshSignal() {
        const http = require('http');
        const url = require('url');
        
        const parsedUrl = url.parse(this.url);
        const options = {
            hostname: parsedUrl.hostname,
            port: parsedUrl.port || 80,
            path: '/refresh',
            method: 'GET',
            timeout: 5000
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    console.log(`✅ Refresh signal sent: ${response.status}`);
                } catch (e) {
                    console.log(`✅ Refresh signal sent (no JSON response)`);
                }
            });
        });

        req.on('error', (err) => {
            console.log(`⚠️  HTTP refresh signal failed: ${err.message}`);
        });

        req.on('timeout', () => {
            console.log(`⚠️  HTTP refresh signal timed out`);
            req.destroy();
        });

        req.end();
    }

    /**
     * Send F5 key using xdotool (Linux)
     */
    sendKeyboardRefresh() {
        if (process.platform !== 'linux') return;
        
        exec('which xdotool', (error) => {
            if (error) {
                console.log(`⚠️  xdotool not available for keyboard refresh`);
                return;
            }
            
            exec('xdotool key F5', (error, stdout, stderr) => {
                if (error) {
                    console.log(`⚠️  xdotool refresh failed: ${error.message}`);
                } else {
                    console.log(`✅ Keyboard refresh sent via xdotool`);
                }
            });
        });
    }

    /**
     * Send refresh using AppleScript (macOS)
     */
    sendAppleScriptRefresh() {
        if (process.platform !== 'darwin') return;
        
        const script = `
            tell application "Safari"
                if (count of windows) > 0 then
                    tell front window
                        set current tab to first tab whose URL contains "${this.url}"
                        do JavaScript "location.reload()" in current tab
                    end tell
                end if
            end tell
        `;
        
        exec(`osascript -e '${script}'`, (error, stdout, stderr) => {
            if (error) {
                console.log(`⚠️  AppleScript refresh failed: ${error.message}`);
            } else {
                console.log(`✅ Page refreshed via AppleScript`);
            }
        });
    }

    /**
     * Start auto-refresh mode
     */
    startAutoRefresh() {
        if (!this.autoRefresh) return;
        
        console.log(`🔄 Starting auto-refresh mode (every ${this.refreshInterval / 1000} seconds)`);
        
        setInterval(() => {
            this.refreshPage();
        }, this.refreshInterval);
    }

    /**
     * Start the browser refresher
     */
    start() {
        console.log(`🔥 GONZO BROWSER REFRESHER STARTING 🔥`);
        console.log(`URL: ${this.url}`);
        console.log(`Browser: ${this.browser}`);
        console.log(`Auto-refresh: ${this.autoRefresh ? 'Yes' : 'No'}`);
        console.log(`Refresh interval: ${this.refreshInterval / 1000} seconds`);
        console.log(`=====================================`);
        
        // Open browser
        this.openBrowser();
        
        // Start auto-refresh if enabled
        this.startAutoRefresh();
        
        // Keep the process alive
        if (!this.autoRefresh) {
            console.log(`Press Ctrl+C to stop`);
            process.on('SIGINT', () => {
                console.log(`\n🛑 Browser refresher stopped`);
                process.exit(0);
            });
        }
    }
}

// CLI interface
if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {};
    
    // Parse command line arguments
    for (let i = 0; i < args.length; i++) {
        switch (args[i]) {
            case '--url':
                options.url = args[++i];
                break;
            case '--browser':
                options.browser = args[++i];
                break;
            case '--interval':
                options.refreshInterval = parseInt(args[++i]) * 1000;
                break;
            case '--auto-refresh':
                options.autoRefresh = true;
                break;
            case '--help':
                console.log(`
Gonzo Browser Refresher

Usage: node browser-refresh.js [OPTIONS]

Options:
  --url URL              URL to open and refresh (default: http://localhost:8080)
  --browser BROWSER      Browser to use: chrome, firefox, safari, edge, default
  --interval SECONDS     Refresh interval in seconds (default: 600)
  --auto-refresh         Enable automatic refresh mode
  --help                 Show this help message

Examples:
  node browser-refresh.js --url http://localhost:3000 --browser chrome
  node browser-refresh.js --auto-refresh --interval 300
  node browser-refresh.js --browser firefox --url http://localhost:8080
                `);
                process.exit(0);
                break;
        }
    }
    
    // Create and start refresher
    const refresher = new BrowserRefresher(options);
    refresher.start();
}

module.exports = BrowserRefresher;


