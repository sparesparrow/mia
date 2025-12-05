#!/usr/bin/env python3
"""
Gonzo Web Monitor - Real-time monitoring with auto-pull, rebuild, and browser refresh
Serves the journalists/gonzo variant and monitors changes every 10 minutes
"""

import os
import sys
import time
import subprocess
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gonzo-monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GonzoMonitor:
    def __init__(self, port=8080, refresh_interval=600):  # 10 minutes = 600 seconds
        self.port = port
        self.refresh_interval = refresh_interval
        self.web_dir = Path(__file__).parent
        self.dist_dir = self.web_dir / "dist"
        self.gonzo_file = self.web_dir / "customers" / "journalists" / "index-gonzo.html"
        self.server = None
        self.monitor_thread = None
        self.running = False
        
        # Ensure dist directory exists
        self.dist_dir.mkdir(exist_ok=True)
        
        # Copy gonzo files to dist for serving
        self.setup_gonzo_files()
        
    def setup_gonzo_files(self):
        """Copy gonzo files to dist directory for serving"""
        try:
            # Copy the gonzo HTML file
            if self.gonzo_file.exists():
                gonzo_dest = self.dist_dir / "index.html"
                gonzo_dest.write_text(self.gonzo_file.read_text())
                logger.info(f"Copied gonzo HTML to {gonzo_dest}")
            
            # Copy gonzo assets
            gonzo_assets = self.web_dir / "customers" / "journalists"
            for asset in gonzo_assets.glob("*"):
                if asset.is_file():
                    dest = self.dist_dir / asset.name
                    dest.write_bytes(asset.read_bytes())
                    logger.info(f"Copied asset {asset.name}")
            
            # Copy shared assets if they exist
            shared_assets = self.web_dir / "assets" / "journalists"
            if shared_assets.exists():
                dest_assets = self.dist_dir / "assets"
                dest_assets.mkdir(exist_ok=True)
                for asset in shared_assets.glob("*"):
                    if asset.is_file():
                        dest = dest_assets / asset.name
                        dest.write_bytes(asset.read_bytes())
                        logger.info(f"Copied shared asset {asset.name}")
                        
        except Exception as e:
            logger.error(f"Error setting up gonzo files: {e}")
    
    def git_pull(self):
        """Pull latest changes from git"""
        try:
            logger.info("🔄 Pulling latest changes from git...")
            result = subprocess.run(
                ["git", "pull", "origin", "feature/journalists-audio-autoplay"],
                cwd=self.web_dir.parent,  # Go to project root
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✅ Git pull successful")
                if result.stdout.strip():
                    logger.info(f"Changes: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"❌ Git pull failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Git pull timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Git pull error: {e}")
            return False
    
    def rebuild_web(self):
        """Rebuild the web pages"""
        try:
            logger.info("🔨 Rebuilding web pages...")
            
            # Run npm build if package.json exists
            package_json = self.web_dir / "package.json"
            if package_json.exists():
                result = subprocess.run(
                    ["npm", "run", "build"],
                    cwd=self.web_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    logger.info("✅ NPM build successful")
                else:
                    logger.error(f"❌ NPM build failed: {result.stderr}")
                    return False
            
            # Copy gonzo files again after rebuild
            self.setup_gonzo_files()
            
            logger.info("✅ Web rebuild completed")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Build timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Build error: {e}")
            return False
    
    def refresh_browser(self):
        """Refresh the browser page"""
        try:
            # Try to refresh using browser automation
            # This is a simple approach - in production you might want to use selenium
            logger.info("🔄 Refreshing browser...")
            
            # Open browser if not already open
            url = f"http://localhost:{self.port}"
            webbrowser.open(url)
            
            # Send a refresh signal via a simple HTTP request
            import urllib.request
            try:
                urllib.request.urlopen(f"{url}/refresh", timeout=5)
            except:
                pass  # Ignore if refresh endpoint doesn't exist
                
            logger.info("✅ Browser refresh initiated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Browser refresh error: {e}")
            return False
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info(f"🚀 Starting monitoring loop (every {self.refresh_interval} seconds)")
        
        while self.running:
            try:
                logger.info("=" * 50)
                logger.info(f"🕐 Monitoring cycle started at {datetime.now()}")
                
                # Step 1: Git pull
                if self.git_pull():
                    # Step 2: Rebuild web
                    if self.rebuild_web():
                        # Step 3: Refresh browser
                        self.refresh_browser()
                        logger.info("✅ Complete cycle successful")
                    else:
                        logger.error("❌ Rebuild failed, skipping browser refresh")
                else:
                    logger.error("❌ Git pull failed, skipping rebuild and refresh")
                
                logger.info(f"💤 Waiting {self.refresh_interval} seconds until next cycle...")
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
            
            # Wait for next cycle
            for _ in range(self.refresh_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def start_server(self):
        """Start the HTTP server"""
        try:
            os.chdir(self.dist_dir)
            dist_dir_path = str(self.dist_dir)
            
            class GonzoHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=dist_dir_path, **kwargs)
                
                def do_GET(self):
                    # Serve index.html for root path
                    if self.path == '/':
                        self.path = '/index.html'
                    elif self.path == '/refresh':
                        # Simple refresh endpoint
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            'status': 'refreshed',
                            'timestamp': datetime.now().isoformat()
                        }).encode())
                        return
                    super().do_GET()
                
                def log_message(self, format, *args):
                    logger.info(f"HTTP: {format % args}")
            
            self.server = HTTPServer(('localhost', self.port), GonzoHandler)
            logger.info(f"🌐 Server starting on http://localhost:{self.port}")
            logger.info(f"📁 Serving from: {self.dist_dir}")
            
            # Start server in a separate thread
            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            return False
    
    def start_monitoring(self):
        """Start the complete monitoring system"""
        logger.info("🔥 GONZO MONITOR STARTING UP 🔥")
        logger.info("=" * 60)
        
        # Start web server
        if not self.start_server():
            logger.error("❌ Failed to start web server")
            return False
        
        # Open browser
        url = f"http://localhost:{self.port}"
        logger.info(f"🌐 Opening browser: {url}")
        webbrowser.open(url)
        
        # Start monitoring loop
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("✅ Gonzo monitor started successfully!")
        logger.info("Press Ctrl+C to stop monitoring")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down Gonzo monitor...")
            self.stop_monitoring()
        
        return True
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.running = False
        
        if self.server:
            self.server.shutdown()
            logger.info("🛑 Web server stopped")
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            logger.info("🛑 Monitor thread stopped")
        
        logger.info("✅ Gonzo monitor stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gonzo Web Monitor - Real-time monitoring with auto-pull and refresh')
    parser.add_argument('--port', type=int, default=8080, help='Port to serve on (default: 8080)')
    parser.add_argument('--interval', type=int, default=600, help='Refresh interval in seconds (default: 600 = 10 minutes)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    
    args = parser.parse_args()
    
    # Create and start monitor
    monitor = GonzoMonitor(port=args.port, refresh_interval=args.interval)
    
    if not args.no_browser:
        monitor.start_monitoring()
    else:
        # Just start server without monitoring
        if monitor.start_server():
            logger.info(f"🌐 Server running on http://localhost:{args.port}")
            logger.info("Press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.stop_monitoring()

if __name__ == "__main__":
    main()
