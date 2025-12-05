# 🔥 Gonzo Web Monitor 🔥

Real-time monitoring system for the journalists/gonzo variant of AI-SERVIS web pages. Automatically pulls changes from git, rebuilds the web pages, and refreshes the browser every 10 minutes.

## Features

- 🌐 **Web Server**: Serves the gonzo variant on localhost
- 🔄 **Auto Git Pull**: Pulls latest changes every 10 minutes
- 🔨 **Auto Rebuild**: Rebuilds web pages after each git pull
- 🌍 **Auto Browser Refresh**: Refreshes browser after rebuild
- 📊 **Real-time Monitoring**: Live logs of all operations
- 🎯 **Gonzo Variant**: Specifically serves the journalists/gonzo version

## Quick Start

### Option 1: Simple Launcher (Recommended)
```bash
cd web
./start-gonzo-monitor.sh
```

### Option 2: Direct Python Script
```bash
cd web
python3 monitor-gonzo.py
```

### Option 3: Custom Configuration
```bash
cd web
./start-gonzo-monitor.sh --port 3000 --interval 300 --no-browser
```

## Configuration Options

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--port PORT` | Port to serve on | 8080 |
| `--interval SECONDS` | Refresh interval in seconds | 600 (10 minutes) |
| `--no-browser` | Don't open browser automatically | false |

### Examples

```bash
# Start on port 3000 with 5-minute refresh
./start-gonzo-monitor.sh --port 3000 --interval 300

# Start without opening browser
./start-gonzo-monitor.sh --no-browser

# Start with custom settings
python3 monitor-gonzo.py --port 8080 --interval 600
```

## How It Works

1. **🌐 Web Server**: Starts HTTP server serving the gonzo variant
2. **🔄 Git Pull**: Every 10 minutes, pulls latest changes from `feature/journalists-audio-autoplay` branch
3. **🔨 Rebuild**: Runs `npm run build` to regenerate web pages
4. **📁 File Sync**: Copies gonzo files to dist directory
5. **🌍 Browser Refresh**: Refreshes browser to show latest changes
6. **📊 Logging**: Logs all operations to console and `gonzo-monitor.log`

## File Structure

```
web/
├── monitor-gonzo.py          # Main monitoring script
├── start-gonzo-monitor.sh    # Launcher script
├── browser-refresh.js        # Browser automation script
├── customers/journalists/    # Gonzo source files
│   ├── index-gonzo.html      # Gonzo HTML template
│   ├── gonzo-app.js          # Gonzo JavaScript
│   ├── gonzo-styles.css      # Gonzo CSS
│   └── background-music.mp3  # Background music
├── dist/                     # Generated files (served by web server)
│   ├── index.html            # Gonzo page (copied from index-gonzo.html)
│   ├── gonzo-app.js          # Gonzo JavaScript
│   ├── gonzo-styles.css      # Gonzo CSS
│   └── background-music.mp3  # Background music
└── gonzo-monitor.log         # Monitoring logs
```

## Browser Automation

The system includes advanced browser automation:

### Automatic Refresh Methods
1. **HTTP Signal**: Sends refresh signal to `/refresh` endpoint
2. **Keyboard Shortcut**: Uses `xdotool` to send F5 key (Linux)
3. **AppleScript**: Uses AppleScript to refresh Safari (macOS)
4. **WebDriver**: Can be extended with Selenium WebDriver

### Manual Browser Refresh
```bash
# Refresh using the browser automation script
node browser-refresh.js --url http://localhost:8080

# Auto-refresh mode
node browser-refresh.js --auto-refresh --interval 300
```

## Monitoring and Logs

### Real-time Monitoring
The system provides detailed logging:
- ✅ Successful operations
- ❌ Error messages
- 🔄 Status updates
- 📊 Performance metrics

### Log Files
- **Console**: Real-time output
- **gonzo-monitor.log**: Persistent log file

### Log Levels
- `INFO`: Normal operations
- `ERROR`: Error conditions
- `WARNING`: Non-critical issues

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
lsof -i :8080

# Kill the process
kill -9 <PID>

# Or use a different port
./start-gonzo-monitor.sh --port 3000
```

#### Git Pull Fails
- Ensure you're on the correct branch: `feature/journalists-audio-autoplay`
- Check git credentials and permissions
- Verify remote repository access

#### Build Fails
- Ensure Node.js and npm are installed
- Check `package.json` exists in web directory
- Verify all dependencies are installed

#### Browser Doesn't Open
- Check if default browser is configured
- Try specifying browser explicitly: `--browser chrome`
- Use `--no-browser` and open manually

### Debug Mode
```bash
# Run with verbose logging
python3 monitor-gonzo.py --port 8080 --interval 60

# Check logs
tail -f gonzo-monitor.log
```

## Advanced Usage

### Custom Browser
```bash
# Use specific browser
node browser-refresh.js --browser chrome --url http://localhost:8080
node browser-refresh.js --browser firefox --url http://localhost:8080
```

### Integration with CI/CD
```bash
# Start monitoring in background
nohup ./start-gonzo-monitor.sh --no-browser > monitor.log 2>&1 &

# Check status
ps aux | grep monitor-gonzo.py

# Stop monitoring
pkill -f monitor-gonzo.py
```

### Custom Refresh Logic
Modify `monitor-gonzo.py` to add custom refresh logic:
```python
def custom_refresh_logic(self):
    # Add your custom refresh logic here
    pass
```

## Requirements

### System Requirements
- Python 3.6+
- Node.js 12+
- Git
- Web browser

### Python Dependencies
- Built-in modules only (no external dependencies required)
- `http.server`, `threading`, `subprocess`, `logging`

### Optional Dependencies
- `xdotool` (Linux) - for keyboard automation
- `osascript` (macOS) - for AppleScript automation

## Security Notes

- The web server only binds to localhost (127.0.0.1)
- No external network access required
- Git operations use existing credentials
- No sensitive data is logged

## Contributing

To extend the monitoring system:

1. **Add New Refresh Methods**: Modify `refresh_browser()` in `monitor-gonzo.py`
2. **Custom Build Steps**: Modify `rebuild_web()` method
3. **Additional Monitoring**: Add new methods to `GonzoMonitor` class
4. **Browser Automation**: Extend `browser-refresh.js`

## License

Part of the AI-SERVIS project. See main project license.

---

🔥 **"When they watch you, you watch them back."** 🔥


