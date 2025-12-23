#!/bin/bash

# Mobile Intelligent Assistant (MIA) - Car Assistant Agent Deployment Script
# This script deploys the complete Car Assistant Agent to a Raspberry Pi for production use

set -e

echo "🚗 Deploying Mobile Intelligent Assistant (MIA) - Car Assistant Agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
TARGET_HOST="${TARGET_HOST:-localhost}"
TARGET_USER="${TARGET_USER:-mia}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/mia-car-assistant}"
BACKUP_DIR="${BACKUP_DIR:-/opt/mia-backups}"
LOG_DIR="${LOG_DIR:-/var/log/mia}"
MIA_WEB_URL="${MIA_WEB_URL:-http://$(hostname -I | awk '{print $1}'):8080}"
# Support both GitHub releases and Cloudsmith packages
MIA_APK_URL="${MIA_APK_URL:-https://github.com/sparesparrow/mia/releases/latest/download/mia-car-assistant.apk}"
MIA_APK_CLOUDSMITH_URL="${MIA_APK_CLOUDSMITH_URL:-}"
SPARETOOLS_DEV_TOOLS_VERSION="${SPARETOOLS_DEV_TOOLS_VERSION:-2.0.3}"

# Function to run commands on target system
run_remote() {
    if [ "$TARGET_HOST" = "localhost" ]; then
        bash -c "$1"
    else
        ssh "$TARGET_USER@$TARGET_HOST" "$1"
    fi
}

# Function to get bundled Python command (uses SpareTools bundled CPython if available)
get_bundled_python_cmd() {
    echo "
        if [ -x /opt/mia-python/bin/python3 ]; then
            echo '/opt/mia-python/bin/python3'
        else
            echo 'python3'
        fi
    "
}

# Function to setup Python environment for SpareTools utilities
setup_python_env_for_sparetools() {
    echo "
        export TARGET_USER=$TARGET_USER
        export DEPLOY_DIR=$DEPLOY_DIR
        export MIA_WEB_URL=$MIA_WEB_URL
        export MIA_APK_URL=$MIA_APK_URL
        
        # Find SpareTools utilities in Conan cache (similar to bootstrap scripts)
        CONAN_CACHE=\"\$HOME/.conan2/p\"
        SPARETOOLS_UTILS=\$(find \"\$CONAN_CACHE\" -type d -path \"*/sparetools-shared-dev-tools*/package/*/shared_dev_tools\" 2>/dev/null | head -1)
        
        # Build PYTHONPATH with actual paths (find real directories, no wildcards)
        PYTHONPATH=\"\"
        
        # Add venv site-packages (find actual Python version)
        if [ -d \"$DEPLOY_DIR/venv/lib\" ]; then
            VENV_SITE=\$(find \"$DEPLOY_DIR/venv/lib\" -type d -name \"site-packages\" 2>/dev/null | head -1)
            if [ -n \"\$VENV_SITE\" ]; then
                PYTHONPATH=\"\$VENV_SITE\"
            fi
        fi
        
        # Add bundled Python site-packages if available
        if [ -x /opt/mia-python/bin/python3 ] && [ -d /opt/mia-python/lib ]; then
            BUNDLED_SITE=\$(find /opt/mia-python/lib -type d -name \"site-packages\" 2>/dev/null | head -1)
            if [ -n \"\$BUNDLED_SITE\" ]; then
                PYTHONPATH=\"\$BUNDLED_SITE:\$PYTHONPATH\"
            fi
        fi
        
        # Add SpareTools utilities from Conan cache
        if [ -n \"\$SPARETOOLS_UTILS\" ]; then
            PYTHONPATH=\"\$(dirname \$SPARETOOLS_UTILS):\$PYTHONPATH\"
        fi
        
        export PYTHONPATH
    "
}

# Function to copy files to target system
copy_to_target() {
    local src="$1"
    local dst="$2"
    if [ "$TARGET_HOST" = "localhost" ]; then
        cp "$src" "$dst"
    else
        scp "$src" "$TARGET_USER@$TARGET_HOST:$dst"
    fi
}

# Function to check if we're running on Raspberry Pi
check_raspberry_pi() {
    if run_remote "grep -q 'Raspberry Pi' /proc/cpuinfo"; then
        echo -e "${GREEN}✓${NC} Running on Raspberry Pi"
        return 0
    else
        echo -e "${YELLOW}!${NC} Not running on Raspberry Pi - some features may not work"
        return 1
    fi
}

# Function to install system dependencies
install_system_dependencies() {
    echo -e "${BLUE}Installing system dependencies...${NC}"

    run_remote "sudo apt update"
    run_remote "sudo apt install -y python3 python3-pip python3-venv nodejs npm git build-essential"

    # Install ZeroMQ and other required libraries
    run_remote "sudo apt install -y libzmq3-dev libflatbuffers-dev"

    # Install hardware-specific packages if on Raspberry Pi
    if check_raspberry_pi; then
        run_remote "sudo apt install -y python3-rpi.gpio python3-smbus i2c-tools"
    fi

    # Install Conan and SpareTools bundled Python and shared dev tools (no global pip installs)
    run_remote '
      echo "🔧 Setting up SpareTools bundled Python and dev tools..."

      # Ensure Conan 2.x is available (best-effort, user-local)
      if ! command -v conan >/dev/null 2>&1; then
        pip3 install --user "conan>=2.0.0,<3.0.0" 2>/dev/null || \
        pip3 install --user --break-system-packages "conan>=2.0.0,<3.0.0" 2>/dev/null || true
        export PATH="$HOME/.local/bin:$PATH"
      fi

      if command -v conan >/dev/null 2>&1; then
        conan profile detect --force || true
        conan remote add sparesparrow-conan \
          "https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/" \
          --force || true

        # Install sparetools-shared-dev-tools for deployment utilities
        if conan install --tool-requires="sparetools-shared-dev-tools/2.0.3@" --build=missing 2>/dev/null; then
          echo "  ✓ SpareTools shared dev tools installed"
        else
          echo "  ⚠ sparetools-shared-dev-tools not available from Conan"
        fi

        # Try to install sparetools-cpython (best-effort)
        if conan install --tool-requires="sparetools-cpython/3.12.7@" --build=missing; then
          CONAN_CACHE="$HOME/.conan2/p"
          CPY_BIN="$(find "$CONAN_CACHE" -type f -path "*/sparetools-cpython*/package/*/bin/python3" 2>/dev/null | head -1 || true)"
          if [ -n "$CPY_BIN" ]; then
            CPY_ROOT="$(cd "$(dirname "$CPY_BIN")/.." && pwd)"
            echo "  Using bundled CPython from: $CPY_ROOT"
            sudo mkdir -p /opt/mia-python
            sudo rm -rf /opt/mia-python/*
            sudo mkdir -p /opt/mia-python/bin /opt/mia-python/lib
            # Symlink binaries and libs into /opt/mia-python (zero-copy)
            for f in "$CPY_ROOT"/bin/*; do
              sudo ln -sf "$f" "/opt/mia-python/bin/$(basename "$f")"
            done
            if [ -d "$CPY_ROOT/lib" ]; then
              for f in "$CPY_ROOT"/lib/*; do
                sudo ln -sf "$f" "/opt/mia-python/lib/$(basename "$f")"
              done
            fi
            sudo chown -R '"$TARGET_USER:$TARGET_USER"' /opt/mia-python
            echo "  ✓ Bundled Python available at /opt/mia-python"
          else
            echo "  ⚠ sparetools-cpython installed but python3 binary not found in cache; using distro python3 for fallback only"
          fi
        else
          echo "  ⚠ sparetools-cpython not available from Conan; using distro python3 for fallback only"
        fi
      else
        echo "  ⚠ Conan not available; using distro python3 for fallback only"
      fi
    '

    echo -e "${GREEN}✓${NC} System dependencies installed; bundled Python configured if available"
}

# Function to install Python dependencies
install_python_dependencies() {
    echo -e "${BLUE}Installing Python dependencies...${NC}"

    # Create deployment directory first (needed for venv)
    run_remote "sudo mkdir -p $DEPLOY_DIR"
    run_remote "sudo chown $TARGET_USER:$TARGET_USER $DEPLOY_DIR"

    # Create dedicated venv for MIA using bundled CPython if available (no global site-packages)
    run_remote '
      PY_CMD="python3"
      if [ -x /opt/mia-python/bin/python3 ]; then
        PY_CMD="/opt/mia-python/bin/python3"
      fi

      echo "  Using Python for venv: $PY_CMD"
      mkdir -p "'"$DEPLOY_DIR"'/venv"
      "$PY_CMD" -m venv "'"$DEPLOY_DIR"'/venv"

      source "'"$DEPLOY_DIR"'/venv/bin/activate"
      pip install --upgrade pip
      pip install tinymcp zmq flatbuffers paho-mqtt mcp
      
      # Install sparetools-shared-dev-tools with version (from env or default)
      DEV_TOOLS_VERSION="${SPARETOOLS_DEV_TOOLS_VERSION:-2.0.3}"
      pip install "sparetools-shared-dev-tools==${DEV_TOOLS_VERSION}" || \
        pip install sparetools-shared-dev-tools
      
      deactivate
    '

    # Install MCP prompts package globally
    run_remote "sudo npm install -g @sparesparrow/mcp-prompts"

    echo -e "${GREEN}✓${NC} Python dependencies installed"
}

# Function to deploy MIA codebase
deploy_mia_codebase() {
    echo -e "${BLUE}Deploying MIA codebase...${NC}"

    # Create deployment directory
    run_remote "sudo mkdir -p $DEPLOY_DIR"
    run_remote "sudo chown $TARGET_USER:$TARGET_USER $DEPLOY_DIR"

    # Copy MIA modules
    run_remote "cp -r mia/modules $DEPLOY_DIR/"
    run_remote "cp -r mcp-prompts $DEPLOY_DIR/"

    # Copy configuration files
    run_remote "mkdir -p $DEPLOY_DIR/config"
    copy_to_target "mia/modules/core-orchestrator/car_assistant_config.py" "$DEPLOY_DIR/config/"
    copy_to_target "mcp-prompts/data/prompts/public/car-assistant-driver.json" "$DEPLOY_DIR/config/"

    # Create log directory
    run_remote "sudo mkdir -p $LOG_DIR"
    run_remote "sudo chown $TARGET_USER:$TARGET_USER $LOG_DIR"

    echo -e "${GREEN}✓${NC} MIA codebase deployed"
}

# Function to configure MCP
configure_mcp() {
    echo -e "${BLUE}Configuring MCP...${NC}"

    # Create Cursor MCP configuration
    run_remote "mkdir -p ~/.cursor"

    cat > /tmp/mcp.json << EOF
{
  "mcpServers": {
    "car-assistant-mia": {
      "command": "$DEPLOY_DIR/venv/bin/python",
      "args": ["$DEPLOY_DIR/modules/hardware-bridge/hardware_server.py"],
      "env": {
        "GPIO_WORKER_ADDRESS": "tcp://127.0.0.1:5555",
        "OBD_WORKER_ADDRESS": "tcp://127.0.0.1:5556",
        "RF_WORKER_ADDRESS": "tcp://127.0.0.1:5557",
        "LOG_LEVEL": "INFO",
        "MCP_MODE": "car_assistant"
      }
    },
    "mcp-prompts-memory": {
      "command": "npx",
      "args": ["-y", "@sparesparrow/mcp-prompts", "start", "--config", "$DEPLOY_DIR/config/car-assistant-driver.json"],
      "env": {
        "STORAGE_TYPE": "memory",
        "LOG_LEVEL": "info",
        "MCP_MODE": "car_assistant",
        "DEFAULT_PROMPT": "car-assistant-driver"
      }
    },
    "mia-core-orchestrator": {
      "command": "$DEPLOY_DIR/venv/bin/python",
      "args": ["$DEPLOY_DIR/modules/core-orchestrator/main.py"],
      "env": {
        "MCP_DISCOVERY_PORT": "8080",
        "MQTT_BROKER": "tcp://127.0.0.1:1883",
        "LOG_LEVEL": "INFO",
        "CAR_ASSISTANT_MODE": "true"
      }
    }
  }
}
EOF

    copy_to_target "/tmp/mcp.json" "~/.cursor/mcp.json"
    run_remote "chmod 644 ~/.cursor/mcp.json"

    echo -e "${GREEN}✓${NC} MCP configuration complete"
}

# Function to install systemd services
install_systemd_services() {
    echo -e "${BLUE}Installing systemd services...${NC}"

    # Copy service files
    run_remote "sudo cp mia/services/mia-mcp-server.service /etc/systemd/system/"
    run_remote "sudo cp mia/services/mia-gpio-worker.service /etc/systemd/system/"
    run_remote "sudo cp mia/services/mia-obd-worker.service /etc/systemd/system/"
    run_remote "sudo cp mia/services/mia-broker.service /etc/systemd/system/"

    # Create car assistant service
    cat > /tmp/mia-car-assistant.service << EOF
[Unit]
Description=MIA Car Assistant Agent
After=network.target
Wants=mia-broker.service mia-gpio-worker.service mia-obd-worker.service

[Service]
Type=simple
User=$TARGET_USER
WorkingDirectory=$DEPLOY_DIR
Environment=PYTHONPATH=$DEPLOY_DIR
ExecStart=$DEPLOY_DIR/venv/bin/python $DEPLOY_DIR/modules/hardware-bridge/hardware_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    copy_to_target "/tmp/mia-car-assistant.service" "/tmp/mia-car-assistant.service"
    run_remote "sudo mv /tmp/mia-car-assistant.service /etc/systemd/system/"

    # Reload systemd and enable services
    run_remote "sudo systemctl daemon-reload"
    run_remote "sudo systemctl enable mia-car-assistant"
    run_remote "sudo systemctl enable mia-mcp-server"
    run_remote "sudo systemctl enable mia-broker"
    run_remote "sudo systemctl enable mia-gpio-worker"
    run_remote "sudo systemctl enable mia-obd-worker"

    echo -e "${GREEN}✓${NC} Systemd services installed"
}

# Function to configure Raspberry Pi specific settings
configure_raspberry_pi() {
    if ! check_raspberry_pi; then
        return 0
    fi

    echo -e "${BLUE}Configuring Raspberry Pi specific settings...${NC}"

    # Enable I2C and SPI
    run_remote "sudo raspi-config nonint do_i2c 0"
    run_remote "sudo raspi-config nonint do_spi 0"

    # Configure GPIO permissions
    run_remote "sudo usermod -a -G gpio $TARGET_USER"

    # Set up power management
    run_remote "echo 'dtoverlay=gpio-poweroff,gpiopin=26' | sudo tee -a /boot/config.txt"

    echo -e "${GREEN}✓${NC} Raspberry Pi configuration complete"
}

# Function to create startup scripts
create_startup_scripts() {
    echo -e "${BLUE}Creating startup scripts...${NC}"

    # Create production startup script
    cat > /tmp/start_car_assistant_prod.sh << 'EOF'
#!/bin/bash
# Production startup script for MIA Car Assistant Agent

DEPLOY_DIR="/opt/mia-car-assistant"
LOG_DIR="/var/log/mia"

echo "🚗 Starting MIA Car Assistant Agent (Production)"

# Start systemd services
sudo systemctl start mia-broker
sudo systemctl start mia-gpio-worker
sudo systemctl start mia-obd-worker
sudo systemctl start mia-mcp-server
sudo systemctl start mia-car-assistant

# Start MCP prompts service
npx @sparesparrow/mcp-prompts start --config "$DEPLOY_DIR/config/car-assistant-driver.json" \
    --storage-type memory --log-level info > "$LOG_DIR/mcp-prompts.log" 2>&1 &

echo "✓ MIA Car Assistant Agent started"
echo "Check status with: sudo systemctl status mia-car-assistant"
EOF

    # Create production stop script
    cat > /tmp/stop_car_assistant_prod.sh << 'EOF'
#!/bin/bash
# Production stop script for MIA Car Assistant Agent

echo "🛑 Stopping MIA Car Assistant Agent (Production)"

# Stop MCP prompts
pkill -f "mcp-prompts start" || true

# Stop systemd services
sudo systemctl stop mia-car-assistant
sudo systemctl stop mia-mcp-server
sudo systemctl stop mia-obd-worker
sudo systemctl stop mia-gpio-worker
sudo systemctl stop mia-broker

echo "✓ MIA Car Assistant Agent stopped"
EOF

    copy_to_target "/tmp/start_car_assistant_prod.sh" "$DEPLOY_DIR/start_production.sh"
    copy_to_target "/tmp/stop_car_assistant_prod.sh" "$DEPLOY_DIR/stop_production.sh"

    run_remote "chmod +x $DEPLOY_DIR/start_production.sh"
    run_remote "chmod +x $DEPLOY_DIR/stop_production.sh"

    echo -e "${GREEN}✓${NC} Startup scripts created"
}

# Function to run tests
run_deployment_tests() {
    echo -e "${BLUE}Running deployment tests...${NC}"

    # Test Python imports
    run_remote "source $DEPLOY_DIR/venv/bin/activate && python -c 'import tinymcp, zmq, flatbuffers, mcp; print(\"✓ Python dependencies OK\")'"

    # Test MCP configuration
    run_remote "test -f ~/.cursor/mcp.json && echo '✓ MCP configuration exists'"

    # Test systemd services
    run_remote "sudo systemctl list-units --type=service | grep -q mia-car-assistant && echo '✓ Systemd services configured'"

    echo -e "${GREEN}✓${NC} Deployment tests passed"
}

# Function to setup VNC server using SpareTools utilities
setup_vnc_server() {
    echo -e "${BLUE}Setting up VNC server for touchscreen mobile access using SpareTools utilities...${NC}"

    # Create Python script for VNC server setup
    cat > /tmp/setup_vnc_server.py << 'EOF'
#!/usr/bin/env python3
"""
Setup VNC server using SpareTools shared dev tools utilities.
"""

import sys
import os
import subprocess
from pathlib import Path

# Find SpareTools shared dev tools from Conan cache (similar to bootstrap scripts)
def find_sparetools_utils():
    """Find sparetools-shared-dev-tools in Conan cache."""
    import glob
    conan_cache = os.path.expanduser('~/.conan2/p')
    if os.path.exists(conan_cache):
        # Find sparetools-shared-dev-tools package directory
        pattern = os.path.join(conan_cache, 'sparetools-shared-dev-tools*', 'package', '*', 'shared_dev_tools')
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return None

# Add SpareTools shared dev tools to path
utils_path = find_sparetools_utils()
if utils_path:
    sys.path.insert(0, utils_path)

# Also check venv and bundled Python site-packages
for path_pattern in [
    '/opt/mia-python/lib/python3.*/site-packages',
    os.path.join(os.path.expanduser('~'), '.local', 'lib', 'python3.*', 'site-packages')
]:
    import glob
    matches = glob.glob(path_pattern)
    for match in matches:
        if match not in sys.path:
            sys.path.insert(0, match)

try:
    from shared_dev_tools.util.execute_command import execute_command
    from shared_dev_tools.util.file_operations import ensure_directory_exists
    from shared_dev_tools.core.utilities import setup_logging

    setup_logging("INFO")

    def install_vnc_packages():
        """Install VNC and desktop packages."""
        print("Installing VNC and desktop packages...")

        packages = [
            "tigervnc-standalone-server",
            "x11vnc",
            "xfce4",
            "xfce4-goodies",
            "onboard"
        ]

        # Update package list
        execute_command(["sudo", "apt", "update"])

        # Install packages
        result = execute_command(["sudo", "apt", "install", "-y"] + packages)
        return result[0] == 0

    def configure_vnc_user(username):
        """Configure VNC for the specified user."""
        print(f"Configuring VNC for user: {username}")

        home_dir = Path(f"/home/{username}")
        vnc_dir = home_dir / ".vnc"

        # Create VNC directory
        ensure_directory_exists(vnc_dir)

        # Set password (use username as password for simplicity)
        passwd_file = vnc_dir / "passwd"
        result = execute_command(["sudo", "-u", username, "bash", "-c", f"echo '{username}' | vncpasswd -f > {passwd_file}"])
        if result[0] == 0:
            execute_command(["sudo", "chmod", "600", str(passwd_file)])

        # Create xstartup script
        xstartup_content = """#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec /usr/bin/startxfce4 &
"""
        xstartup_file = vnc_dir / "xstartup"
        with open(xstartup_file, 'w') as f:
            f.write(xstartup_content)
        execute_command(["sudo", "chmod", "+x", str(xstartup_file)])
        execute_command(["sudo", "chown", f"{username}:{username}", str(xstartup_file)])

        print(f"Configured VNC for user {username}")
        return True

    def create_vnc_service(username):
        """Create systemd service for VNC."""
        print(f"Creating VNC systemd service for user: {username}")

        service_content = f"""[Unit]
Description=VNC Server for {username} (Mobile/Touchscreen Optimized)
After=syslog.target network.target

[Service]
Type=forking
User={username}
Group={username}
WorkingDirectory=/home/{username}
ExecStartPre=-/usr/bin/vncserver -kill :1
# Mobile-optimized: 1280x720 for tablets, depth 24, pixel format optimized for mobile VNC clients
ExecStart=/usr/bin/vncserver :1 -geometry 1280x720 -depth 24 -pixelformat RGB888 -dpi 96
ExecStop=/usr/bin/vncserver -kill :1

[Install]
WantedBy=multi-user.target
"""

        service_file = f"/etc/systemd/system/vncserver@{username}.service"
        with open("/tmp/vnc_service", 'w') as f:
            f.write(service_content)

        execute_command(["sudo", "mv", "/tmp/vnc_service", service_file])
        execute_command(["sudo", "systemctl", "daemon-reload"])
        execute_command(["sudo", "systemctl", "enable", f"vncserver@{username}"])

        print(f"Created and enabled VNC service for {username}")
        return True

    if __name__ == "__main__":
        username = os.environ.get("TARGET_USER", "mia")

        success = True
        success &= install_vnc_packages()
        success &= configure_vnc_user(username)
        success &= create_vnc_service(username)

        if success:
            print(f"✓ VNC server configured successfully for user {username}")
            sys.exit(0)
        else:
            print(f"✗ Failed to configure VNC server for user {username}")
            sys.exit(1)

except ImportError as e:
    print(f"SpareTools utilities not available: {e}")
    print("Falling back to shell-based VNC setup...")

    # Fallback to shell commands
    username = os.environ.get("TARGET_USER", "mia")

    # Install packages
    subprocess.run(["sudo", "apt", "update"], check=True)
    subprocess.run(["sudo", "apt", "install", "-y",
                   "tigervnc-standalone-server", "x11vnc",
                   "xfce4", "xfce4-goodies", "onboard"], check=True)

    # Configure VNC for user
    home_dir = f"/home/{username}"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", f"{home_dir}/.vnc"], check=True)
    subprocess.run(["sudo", "-u", username, "bash", "-c",
                   f"echo '{username}' | vncpasswd -f > {home_dir}/.vnc/passwd"], check=True)
    subprocess.run(["sudo", "chmod", "600", f"{home_dir}/.vnc/passwd"], check=True)

    # Create xstartup
    xstartup_content = """#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec /usr/bin/startxfce4 &
"""
    with open("/tmp/xstartup", 'w') as f:
        f.write(xstartup_content)
    subprocess.run(["sudo", "mv", "/tmp/xstartup", f"{home_dir}/.vnc/xstartup"], check=True)
    subprocess.run(["sudo", "chmod", "+x", f"{home_dir}/.vnc/xstartup"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{home_dir}/.vnc/xstartup"], check=True)

    # Create systemd service
    service_content = f"""[Unit]
Description=VNC Server for {username}
After=syslog.target network.target

[Service]
Type=forking
User={username}
Group={username}
WorkingDirectory=/home/{username}
ExecStartPre=-/usr/bin/vncserver -kill :1
ExecStart=/usr/bin/vncserver :1 -geometry 1280x720
ExecStop=/usr/bin/vncserver -kill :1

[Install]
WantedBy=multi-user.target
"""
    with open("/tmp/vnc_service", 'w') as f:
        f.write(service_content)
    subprocess.run(["sudo", "mv", "/tmp/vnc_service", f"/etc/systemd/system/vncserver@{username}.service"], check=True)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", f"vncserver@{username}"], check=True)

    print(f"✓ VNC server configured for user {username} (fallback method)")
    sys.exit(0)
EOF

    run_remote "
        $(setup_python_env_for_sparetools)
        PY_CMD=\$($(get_bundled_python_cmd))
        \$PY_CMD /tmp/setup_vnc_server.py
    "

    echo -e "${GREEN}✓${NC} VNC server setup complete using SpareTools utilities"
}

# Function to configure touchscreen desktop using SpareTools utilities
configure_touchscreen_desktop() {
    echo -e "${BLUE}Configuring touchscreen-friendly desktop using SpareTools utilities...${NC}"

    # Create Python script for desktop configuration
    cat > /tmp/configure_touchscreen_desktop.py << 'EOF'
#!/usr/bin/env python3
"""
Configure touchscreen desktop using SpareTools shared dev tools utilities.
"""

import sys
import os
from pathlib import Path

# Find SpareTools shared dev tools from Conan cache (similar to bootstrap scripts)
def find_sparetools_utils():
    """Find sparetools-shared-dev-tools in Conan cache."""
    import glob
    conan_cache = os.path.expanduser('~/.conan2/p')
    if os.path.exists(conan_cache):
        # Find sparetools-shared-dev-tools package directory
        pattern = os.path.join(conan_cache, 'sparetools-shared-dev-tools*', 'package', '*', 'shared_dev_tools')
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return None

# Add SpareTools shared dev tools to path
utils_path = find_sparetools_utils()
if utils_path:
    sys.path.insert(0, utils_path)

# Also check venv and bundled Python site-packages
for path_pattern in [
    '/opt/mia-python/lib/python3.*/site-packages',
    os.path.join(os.path.expanduser('~'), '.local', 'lib', 'python3.*', 'site-packages')
]:
    import glob
    matches = glob.glob(path_pattern)
    for match in matches:
        if match not in sys.path:
            sys.path.insert(0, match)

try:
    from shared_dev_tools.util.execute_command import execute_command
    from shared_dev_tools.util.file_operations import ensure_directory_exists
    from shared_dev_tools.core.utilities import setup_logging

    setup_logging("INFO")

    def configure_xfce_settings(username):
        """Configure XFCE settings for mobile/touchscreen (Plasma Mobile-like)."""
        print(f"Configuring XFCE settings for mobile/touchscreen user: {username}")

        config_dir = Path(f"/home/{username}/.config/xfce4/xfconf/xfce-perchannel-xml")
        ensure_directory_exists(config_dir)

        # Mobile-optimized panel configuration (bottom panel like mobile, larger icons)
        panel_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=10;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="size" type="uint" value="64"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="icon-size" type="uint" value="48"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
      </property>
    </property>
  </property>
</channel>
"""

        # Mobile-optimized window manager settings (touch-friendly)
        wm_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Default"/>
    <property name="title_font" type="string" value="Sans Bold 12"/>
    <property name="button_layout" type="string" value="CHM|"/>
    <property name="double_click_action" type="string" value="maximize"/>
    <property name="double_click_distance" type="int" value="5"/>
    <property name="double_click_time" type="int" value="250"/>
    <property name="raise_on_click" type="bool" value="true"/>
    <property name="raise_with_any_button" type="bool" value="true"/>
    <property name="click_to_focus" type="bool" value="true"/>
    <property name="focus_delay" type="int" value="250"/>
  </property>
</channel>
"""

        # Mobile-optimized desktop settings (larger icons, touch-friendly)
        desktop_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="image-style" type="int" value="5"/>
        </property>
      </property>
    </property>
  </property>
  <property name="desktop-icons" type="empty">
    <property name="icon-size" type="uint" value="64"/>
    <property name="tooltip-size" type="uint" value="80"/>
    <property name="single-click" type="bool" value="true"/>
  </property>
</channel>
"""

        # Session configuration
        session_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="SessionName" type="string" value="Default"/>
  <property name="IsManaged" type="bool" value="true"/>
  <property name="SaveOnExit" type="bool" value="true"/>
</channel>
"""

        # Write configuration files
        panel_file = config_dir / "xfce4-panel.xml"
        session_file = config_dir / "xfce4-session.xml"
        wm_file = config_dir / "xfwm4.xml"
        desktop_file = config_dir / "xfce4-desktop.xml"

        with open(panel_file, 'w') as f:
            f.write(panel_config)
        with open(session_file, 'w') as f:
            f.write(session_config)
        with open(wm_file, 'w') as f:
            f.write(wm_config)
        with open(desktop_file, 'w') as f:
            f.write(desktop_config)

        # Set ownership
        for config_file in [panel_file, session_file, wm_file, desktop_file]:
            execute_command(["sudo", "chown", f"{username}:{username}", str(config_file)])

        print(f"Configured XFCE settings for mobile/touchscreen")
        return True

    def configure_on_screen_keyboard(username):
        """Configure on-screen keyboard for touchscreen."""
        print(f"Configuring on-screen keyboard for user: {username}")

        autostart_dir = Path(f"/home/{username}/.config/autostart")
        ensure_directory_exists(autostart_dir)

        onboard_config = """[Desktop Entry]
Type=Application
Name=Onboard
Comment=On-screen keyboard for touchscreen
Exec=onboard
StartupNotify=false
Terminal=false
"""

        onboard_file = autostart_dir / "onboard.desktop"
        with open(onboard_file, 'w') as f:
            f.write(onboard_config)

        execute_command(["sudo", "chown", f"{username}:{username}", str(onboard_file)])

        print(f"Configured on-screen keyboard for touchscreen")
        return True

    if __name__ == "__main__":
        username = os.environ.get("TARGET_USER", "mia")

        success = True
        success &= configure_xfce_settings(username)
        success &= configure_on_screen_keyboard(username)

        if success:
            print(f"✓ Touchscreen desktop configured successfully for user {username}")
            sys.exit(0)
        else:
            print(f"✗ Failed to configure touchscreen desktop for user {username}")
            sys.exit(1)

except ImportError as e:
    print(f"SpareTools utilities not available: {e}")
    print("Falling back to shell-based desktop configuration...")

    # Fallback to shell commands
    import subprocess

    username = os.environ.get("TARGET_USER", "mia")
    home_dir = f"/home/{username}"

    # Configure XFCE settings
    config_dir = f"{home_dir}/.config/xfce4/xfconf/xfce-perchannel-xml"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", config_dir], check=True)

    panel_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=6;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
      </property>
    </property>
  </property>
</channel>
"""

    session_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="SessionName" type="string" value="Default"/>
  <property name="IsManaged" type="bool" value="true"/>
</channel>
"""

    with open("/tmp/xfce4-panel.xml", 'w') as f:
        f.write(panel_config)
    with open("/tmp/xfce4-session.xml", 'w') as f:
        f.write(session_config)

    subprocess.run(["sudo", "mv", "/tmp/xfce4-panel.xml", f"{config_dir}/"], check=True)
    subprocess.run(["sudo", "mv", "/tmp/xfce4-session.xml", f"{config_dir}/"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{config_dir}/xfce4-panel.xml"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{config_dir}/xfce4-session.xml"], check=True)

    # Configure on-screen keyboard
    autostart_dir = f"{home_dir}/.config/autostart"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", autostart_dir], check=True)

    onboard_config = """[Desktop Entry]
Type=Application
Name=Onboard
Comment=On-screen keyboard for touchscreen
Exec=onboard
StartupNotify=false
Terminal=false
"""
    with open("/tmp/onboard.desktop", 'w') as f:
        f.write(onboard_config)

    subprocess.run(["sudo", "mv", "/tmp/onboard.desktop", f"{autostart_dir}/"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{autostart_dir}/onboard.desktop"], check=True)

    print(f"✓ Touchscreen desktop configured for user {username} (fallback method)")
    sys.exit(0)
EOF

    run_remote "
        $(setup_python_env_for_sparetools)
        PY_CMD=\$($(get_bundled_python_cmd))
        \$PY_CMD /tmp/configure_touchscreen_desktop.py
    "

    echo -e "${GREEN}✓${NC} Touchscreen desktop configuration complete using SpareTools utilities"
}

# Function to setup user shell configuration using SpareTools utilities
setup_user_shell() {
    echo -e "${BLUE}Setting up user shell configuration using SpareTools utilities...${NC}"

    # Create Python script for shell configuration
    cat > /tmp/setup_user_shell.py << 'EOF'
#!/usr/bin/env python3
"""
Setup user shell configuration using SpareTools shared dev tools utilities.
"""

import sys
import os
from pathlib import Path

# Find SpareTools shared dev tools from Conan cache (similar to bootstrap scripts)
def find_sparetools_utils():
    """Find sparetools-shared-dev-tools in Conan cache."""
    import glob
    conan_cache = os.path.expanduser('~/.conan2/p')
    if os.path.exists(conan_cache):
        # Find sparetools-shared-dev-tools package directory
        pattern = os.path.join(conan_cache, 'sparetools-shared-dev-tools*', 'package', '*', 'shared_dev_tools')
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return None

# Add SpareTools shared dev tools to path
utils_path = find_sparetools_utils()
if utils_path:
    sys.path.insert(0, utils_path)

# Also check venv and bundled Python site-packages
for path_pattern in [
    '/opt/mia-python/lib/python3.*/site-packages',
    os.path.join(os.path.expanduser('~'), '.local', 'lib', 'python3.*', 'site-packages')
]:
    import glob
    matches = glob.glob(path_pattern)
    for match in matches:
        if match not in sys.path:
            sys.path.insert(0, match)

try:
    from shared_dev_tools.util.execute_command import execute_command
    from shared_dev_tools.util.file_operations import ensure_directory_exists
    from shared_dev_tools.core.utilities import setup_logging

    setup_logging("INFO")

    def configure_bashrc(username, deploy_dir, web_url, apk_url):
        """Configure .bashrc with MIA environment."""
        print(f"Configuring .bashrc for user: {username}")

        home_dir = Path(f"/home/{username}")
        bashrc_file = home_dir / ".bashrc"

        # Helper function to resolve Python paths at runtime (similar to bootstrap scripts)
        bashrc_content = f"""

# MIA Car Assistant Environment
# Resolve Python paths dynamically using SpareTools pattern
_mia_setup_python_path() {{
    local PYTHONPATH=\"\"
    
    # Add venv site-packages
    if [ -d \"{deploy_dir}/venv/lib\" ]; then
        local VENV_SITE=$(find \"{deploy_dir}/venv/lib\" -type d -name \"site-packages\" 2>/dev/null | head -1)
        if [ -n \"$VENV_SITE\" ]; then
            PYTHONPATH=\"$VENV_SITE\"
        fi
    fi
    
    # Add bundled Python site-packages
    if [ -x /opt/mia-python/bin/python3 ] && [ -d /opt/mia-python/lib ]; then
        local BUNDLED_SITE=$(find /opt/mia-python/lib -type d -name \"site-packages\" 2>/dev/null | head -1)
        if [ -n \"$BUNDLED_SITE\" ]; then
            PYTHONPATH=\"$BUNDLED_SITE:$PYTHONPATH\"
        fi
    fi
    
    # Add SpareTools utilities from Conan cache
    local CONAN_CACHE=\"$HOME/.conan2/p\"
    local SPARETOOLS_UTILS=$(find \"$CONAN_CACHE\" -type d -path \"*/sparetools-shared-dev-tools*/package/*/shared_dev_tools\" 2>/dev/null | head -1)
    if [ -n \"$SPARETOOLS_UTILS\" ]; then
        PYTHONPATH=\"$(dirname $SPARETOOLS_UTILS):$PYTHONPATH\"
    fi
    
    export PYTHONPATH
}}
_mia_setup_python_path

export PATH="/opt/mia-python/bin:{deploy_dir}/venv/bin:$PATH"

# MIA aliases
alias mia-status="sudo systemctl status mia-car-assistant"
alias mia-start="sudo systemctl start mia-car-assistant"
alias mia-stop="sudo systemctl stop mia-car-assistant"
alias mia-restart="sudo systemctl restart mia-car-assistant"
alias mia-logs="sudo journalctl -u mia-car-assistant -f"

# VNC aliases
alias vnc-start="sudo systemctl start vncserver@{username}"
alias vnc-stop="sudo systemctl stop vncserver@{username}"
alias vnc-status="sudo systemctl status vncserver@{username}"

"""

        # Append to existing .bashrc
        if bashrc_file.exists():
            with open(bashrc_file, 'a') as f:
                f.write(bashrc_content)
        else:
            with open(bashrc_file, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(bashrc_content)

        execute_command(["sudo", "chown", f"{username}:{username}", str(bashrc_file)])

        print(f"Configured .bashrc for MIA environment")
        return True

    def configure_profile(username, deploy_dir, web_url, apk_url):
        """Configure .profile with MIA settings."""
        print(f"Configuring .profile for user: {username}")

        home_dir = Path(f"/home/{username}")
        profile_file = home_dir / ".profile"

        profile_content = f"""

# MIA Car Assistant Profile Settings
export MIA_WEB_URL="{web_url}"
export MIA_APK_URL="{apk_url}"
export MIA_DEPLOY_DIR="{deploy_dir}"

"""

        # Append to existing .profile
        if profile_file.exists():
            with open(profile_file, 'a') as f:
                f.write(profile_content)
        else:
            with open(profile_file, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(profile_content)

        execute_command(["sudo", "chown", f"{username}:{username}", str(profile_file)])

        print(f"Configured .profile for MIA settings")
        return True

    if __name__ == "__main__":
        username = os.environ.get("TARGET_USER", "mia")
        deploy_dir = os.environ.get("DEPLOY_DIR", "/opt/mia-car-assistant")
        web_url = os.environ.get("MIA_WEB_URL", "http://localhost:8080")
        apk_url = os.environ.get("MIA_APK_URL", "https://github.com/sparesparrow/mia/releases/latest/download/mia-car-assistant.apk")

        success = True
        success &= configure_bashrc(username, deploy_dir, web_url, apk_url)
        success &= configure_profile(username, deploy_dir, web_url, apk_url)

        if success:
            print(f"✓ Shell configuration completed successfully for user {username}")
            sys.exit(0)
        else:
            print(f"✗ Failed to configure shell for user {username}")
            sys.exit(1)

except ImportError as e:
    print(f"SpareTools utilities not available: {e}")
    print("Falling back to shell-based configuration...")

    # Fallback to shell commands
    import subprocess

    username = os.environ.get("TARGET_USER", "mia")
    deploy_dir = os.environ.get("DEPLOY_DIR", "/opt/mia-car-assistant")
    web_url = os.environ.get("MIA_WEB_URL", "http://localhost:8080")
    apk_url = os.environ.get("MIA_APK_URL", "https://github.com/sparesparrow/mia/releases/latest/download/mia-car-assistant.apk")

    # Configure .bashrc
    bashrc_content = f"""

# MIA Car Assistant Environment
export PYTHONPATH="{deploy_dir}/venv/lib/python3.*/site-packages:/opt/mia-python/lib/python3.*/site-packages:$PYTHONPATH"
export PATH="/opt/mia-python/bin:{deploy_dir}/venv/bin:$PATH"

# MIA aliases
alias mia-status="sudo systemctl status mia-car-assistant"
alias mia-start="sudo systemctl start mia-car-assistant"
alias mia-stop="sudo systemctl stop mia-car-assistant"
alias mia-restart="sudo systemctl restart mia-car-assistant"
alias mia-logs="sudo journalctl -u mia-car-assistant -f"

# VNC aliases
alias vnc-start="sudo systemctl start vncserver@{username}"
alias vnc-stop="sudo systemctl stop vncserver@{username}"
alias vnc-status="sudo systemctl status vncserver@{username}"

"""
    subprocess.run(["sudo", "-u", username, "bash", "-c", f"echo '{bashrc_content}' >> ~/.bashrc"], check=True)

    # Configure .profile
    profile_content = f"""

# MIA Car Assistant Profile Settings
export MIA_WEB_URL="{web_url}"
export MIA_APK_URL="{apk_url}"
export MIA_DEPLOY_DIR="{deploy_dir}"

"""
    subprocess.run(["sudo", "-u", username, "bash", "-c", f"echo '{profile_content}' >> ~/.profile"], check=True)

    print(f"✓ Shell configuration completed for user {username} (fallback method)")
    sys.exit(0)
EOF

    run_remote "
        $(setup_python_env_for_sparetools)
        PY_CMD=\$($(get_bundled_python_cmd))
        \$PY_CMD /tmp/setup_user_shell.py
    "

    echo -e "${GREEN}✓${NC} User shell configuration complete using SpareTools utilities"
}

# Function to setup MOTD with QR codes
setup_motd_qr_codes() {
    echo -e "${BLUE}Setting up MOTD with QR codes and instructions...${NC}"

    run_remote "
        # Install qrencode for QR code generation
        sudo apt install -y qrencode

        # Create persistent directory for QR codes
        sudo mkdir -p $DEPLOY_DIR/qr-codes
        sudo chmod 755 $DEPLOY_DIR/qr-codes

        # Generate QR codes persistently (regenerate on each login if URLs change)
        WEB_URL=\"$MIA_WEB_URL\"
        APK_URL=\"$MIA_APK_URL\"
        CLOUDSMITH_URL=\"$MIA_APK_CLOUDSMITH_URL\"

        echo \"\$WEB_URL\" | qrencode -t ANSIUTF8 -o $DEPLOY_DIR/qr-codes/web_qr.txt
        echo \"\$APK_URL\" | qrencode -t ANSIUTF8 -o $DEPLOY_DIR/qr-codes/apk_qr.txt
        
        # Generate Cloudsmith QR code if provided
        if [ -n \"\$CLOUDSMITH_URL\" ]; then
            echo \"\$CLOUDSMITH_URL\" | qrencode -t ANSIUTF8 -o $DEPLOY_DIR/qr-codes/apk_cloudsmith_qr.txt
        fi

        # Create MOTD script
        cat > /tmp/mia-motd.sh << 'MOTDEOF'
#!/bin/bash

# MIA Car Assistant - Message of the Day
# Load URLs from environment or defaults
WEB_URL=\"\${MIA_WEB_URL:-http://\$(hostname -I | awk '{print \$1}'):8080}\"
APK_URL=\"\${MIA_APK_URL:-https://github.com/sparesparrow/mia/releases/latest/download/mia-car-assistant.apk}\"
CLOUDSMITH_URL=\"\${MIA_APK_CLOUDSMITH_URL:-}\"
VNC_IP=\"\$(hostname -I | awk '{print \$1}')\"
QR_DIR=\"$DEPLOY_DIR/qr-codes\"

# Regenerate QR codes if URLs have changed
if [ ! -f \"\$QR_DIR/web_qr.txt\" ] || ! grep -q \"\$WEB_URL\" \"\$QR_DIR/web_qr.txt\" 2>/dev/null; then
    echo \"\$WEB_URL\" | qrencode -t ANSIUTF8 -o \"\$QR_DIR/web_qr.txt\" 2>/dev/null || true
fi
if [ ! -f \"\$QR_DIR/apk_qr.txt\" ] || ! grep -q \"\$APK_URL\" \"\$QR_DIR/apk_qr.txt\" 2>/dev/null; then
    echo \"\$APK_URL\" | qrencode -t ANSIUTF8 -o \"\$QR_DIR/apk_qr.txt\" 2>/dev/null || true
fi
if [ -n \"\$CLOUDSMITH_URL\" ] && ([ ! -f \"\$QR_DIR/apk_cloudsmith_qr.txt\" ] || ! grep -q \"\$CLOUDSMITH_URL\" \"\$QR_DIR/apk_cloudsmith_qr.txt\" 2>/dev/null); then
    echo \"\$CLOUDSMITH_URL\" | qrencode -t ANSIUTF8 -o \"\$QR_DIR/apk_cloudsmith_qr.txt\" 2>/dev/null || true
fi

echo \"\"
echo \"╔══════════════════════════════════════════════════════════════════════════════╗\"
echo \"║                           🚗 MIA Car Assistant 🚗                           ║\"
echo \"║                                                                              ║\"
echo \"║  Mobile Intelligent Assistant for Automotive Applications                   ║\"
echo \"║                                                                              ║\"
echo \"║  Web Interface QR Code:                                                       ║\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"

# Display web interface QR code
if [ -f \"\$QR_DIR/web_qr.txt\" ]; then
    cat \"\$QR_DIR/web_qr.txt\"
else
    echo \"    Web URL: \$WEB_URL\"
fi

echo \"\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
echo \"║  APK Download QR Code (GitHub):                                              ║\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"

# Display GitHub APK download QR code
if [ -f \"\$QR_DIR/apk_qr.txt\" ]; then
    cat \"\$QR_DIR/apk_qr.txt\"
else
    echo \"    APK URL (GitHub): \$APK_URL\"
fi

# Display Cloudsmith QR code if available
if [ -n \"\$CLOUDSMITH_URL\" ] && [ -f \"\$QR_DIR/apk_cloudsmith_qr.txt\" ]; then
    echo \"\"
    echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
    echo \"║  APK Download QR Code (Cloudsmith):                                         ║\"
    echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
    cat \"\$QR_DIR/apk_cloudsmith_qr.txt\"
fi

echo \"\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
echo \"║  Remote Operation Instructions:                                              ║\"
echo \"║                                                                              ║\"
echo \"║  1. Scan web QR code above to access web interface                          ║\"
echo \"║  2. Scan APK QR code to download mobile app (GitHub or Cloudsmith)          ║\"
echo \"║  3. Connect via VNC: vnc://\$VNC_IP:5901                                      ║\"
echo \"║  4. Use touchscreen-friendly mobile interface (Plasma Mobile-like)          ║\"
echo \"║                                                                              ║\"
echo \"║  Commands:                                                                   ║\"
echo \"║    • mia-status   - Check MIA service status                                ║\"
echo \"║    • mia-start    - Start MIA service                                       ║\"
echo \"║    • mia-stop     - Stop MIA service                                        ║\"
echo \"║    • mia-restart  - Restart MIA service                                     ║\"
echo \"║    • mia-logs     - View MIA service logs                                   ║\"
echo \"║    • vnc-start    - Start VNC server                                        ║\"
echo \"║    • vnc-stop     - Stop VNC server                                         ║\"
echo \"║    • vnc-status   - Check VNC server status                                 ║\"
echo \"║                                                                              ║\"
echo \"║  Logs: sudo journalctl -u mia-car-assistant -f                             ║\"
echo \"║  VNC Logs: sudo journalctl -u vncserver@mia -f                              ║\"
echo \"║                                                                              ║\"
echo \"╚══════════════════════════════════════════════════════════════════════════════╝\"
echo \"\"
MOTDEOF

        # Install MOTD
        sudo mv /tmp/mia-motd.sh /etc/update-motd.d/99-mia-car-assistant
        sudo chmod +x /etc/update-motd.d/99-mia-car-assistant

        # Set environment variables for MOTD script
        sudo bash -c \"echo 'export MIA_WEB_URL=\\\"$MIA_WEB_URL\\\"' >> /etc/environment\"
        sudo bash -c \"echo 'export MIA_APK_URL=\\\"$MIA_APK_URL\\\"' >> /etc/environment\"
        if [ -n \"$MIA_APK_CLOUDSMITH_URL\" ]; then
            sudo bash -c \"echo 'export MIA_APK_CLOUDSMITH_URL=\\\"$MIA_APK_CLOUDSMITH_URL\\\"' >> /etc/environment\"
        fi

        # Disable default MOTD
        sudo chmod -x /etc/update-motd.d/10-uname 2>/dev/null || true

        echo '✓ MOTD configured with QR codes and remote operation instructions'
    "

    echo -e "${GREEN}✓${NC} MOTD with QR codes setup complete"
}

# Function to create MIA user using SpareTools utilities
create_mia_user() {
    echo -e "${BLUE}Creating MIA user ($TARGET_USER) using SpareTools utilities...${NC}"

    # Create Python script for user creation
    cat > /tmp/create_mia_user.py << 'EOF'
#!/usr/bin/env python3
"""
Create MIA user using SpareTools shared dev tools utilities.
"""

import sys
import os
import subprocess
from pathlib import Path

# Find SpareTools shared dev tools from Conan cache (similar to bootstrap scripts)
def find_sparetools_utils():
    """Find sparetools-shared-dev-tools in Conan cache."""
    import glob
    conan_cache = os.path.expanduser('~/.conan2/p')
    if os.path.exists(conan_cache):
        # Find sparetools-shared-dev-tools package directory
        pattern = os.path.join(conan_cache, 'sparetools-shared-dev-tools*', 'package', '*', 'shared_dev_tools')
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return None

# Add SpareTools shared dev tools to path
utils_path = find_sparetools_utils()
if utils_path:
    sys.path.insert(0, utils_path)

# Also check venv and bundled Python site-packages
for path_pattern in [
    '/opt/mia-python/lib/python3.*/site-packages',
    os.path.join(os.path.expanduser('~'), '.local', 'lib', 'python3.*', 'site-packages')
]:
    import glob
    matches = glob.glob(path_pattern)
    for match in matches:
        if match not in sys.path:
            sys.path.insert(0, match)

try:
    from shared_dev_tools.util.execute_command import execute_command
    from shared_dev_tools.util.file_operations import ensure_directory_exists
    from shared_dev_tools.core.utilities import setup_logging

    setup_logging("INFO")

    def create_user(username):
        """Create MIA user with proper configuration."""
        print(f"Creating user: {username}")

        # Check if user exists
        result = execute_command(["id", "-u", username], print_command=False, print_out=False)
        if result[0] == 0:
            print(f"User {username} already exists")
            return True

        # Create user
        result = execute_command(["sudo", "useradd", "-m", "-s", "/bin/bash", username])
        if result[0] != 0:
            print(f"Failed to create user {username}")
            return False

        print(f"Created user {username}")
        return True

    def configure_user(username):
        """Configure user with proper groups and directories."""
        print(f"Configuring user: {username}")

        # Add to groups
        groups = ["gpio", "video", "audio", "dialout"]
        for group in groups:
            execute_command(["sudo", "usermod", "-a", "-G", group, username], print_command=False)

        # Create MIA directories
        home_dir = Path(f"/home/{username}")
        mia_dir = home_dir / ".mia"
        config_dir = home_dir / ".config" / "mia"

        ensure_directory_exists(mia_dir)
        ensure_directory_exists(config_dir)

        # Set ownership
        execute_command(["sudo", "chown", "-R", f"{username}:{username}", str(mia_dir)])
        execute_command(["sudo", "chown", "-R", f"{username}:{username}", str(config_dir)])

        print(f"Configured user {username} with groups and directories")
        return True

    if __name__ == "__main__":
        username = os.environ.get("TARGET_USER", "mia")
        if create_user(username) and configure_user(username):
            print(f"✓ User {username} created and configured successfully")
            sys.exit(0)
        else:
            print(f"✗ Failed to create/configure user {username}")
            sys.exit(1)

except ImportError as e:
    print(f"SpareTools utilities not available: {e}")
    print("Falling back to shell-based user creation...")

    # Fallback to shell commands
    username = os.environ.get("TARGET_USER", "mia")

    # Create user if it doesn't exist
    result = subprocess.run(["id", "-u", username], capture_output=True)
    if result.returncode != 0:
        subprocess.run(["sudo", "useradd", "-m", "-s", "/bin/bash", username], check=True)

    # Add to groups
    groups = ["gpio", "video", "audio", "dialout"]
    for group in groups:
        subprocess.run(["sudo", "usermod", "-a", "-G", group, username])

    # Create directories
    subprocess.run(["sudo", "mkdir", "-p", f"/home/{username}/.mia"])
    subprocess.run(["sudo", "mkdir", "-p", f"/home/{username}/.config/mia"])
    subprocess.run(["sudo", "chown", "-R", f"{username}:{username}", f"/home/{username}/.mia"])
    subprocess.run(["sudo", "chown", "-R", f"{username}:{username}", f"/home/{username}/.config/mia"])

    print(f"✓ User {username} created and configured (fallback method)")
    sys.exit(0)
EOF

    run_remote "
        $(setup_python_env_for_sparetools)
        PY_CMD=\$($(get_bundled_python_cmd))
        \$PY_CMD /tmp/create_mia_user.py
    "

    echo -e "${GREEN}✓${NC} MIA user created and configured using SpareTools utilities"
}

# Function to setup VNC server using SpareTools utilities
setup_vnc_server() {
    echo -e "${BLUE}Setting up VNC server for touchscreen mobile access using SpareTools utilities...${NC}"

    # Create Python script for VNC server setup
    cat > /tmp/setup_vnc_server.py << 'EOF'
#!/usr/bin/env python3
"""
Setup VNC server using SpareTools shared dev tools utilities.
"""

import sys
import os
import subprocess
from pathlib import Path

# Find SpareTools shared dev tools from Conan cache (similar to bootstrap scripts)
def find_sparetools_utils():
    """Find sparetools-shared-dev-tools in Conan cache."""
    import glob
    conan_cache = os.path.expanduser('~/.conan2/p')
    if os.path.exists(conan_cache):
        # Find sparetools-shared-dev-tools package directory
        pattern = os.path.join(conan_cache, 'sparetools-shared-dev-tools*', 'package', '*', 'shared_dev_tools')
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return None

# Add SpareTools shared dev tools to path
utils_path = find_sparetools_utils()
if utils_path:
    sys.path.insert(0, utils_path)

# Also check venv and bundled Python site-packages
for path_pattern in [
    '/opt/mia-python/lib/python3.*/site-packages',
    os.path.join(os.path.expanduser('~'), '.local', 'lib', 'python3.*', 'site-packages')
]:
    import glob
    matches = glob.glob(path_pattern)
    for match in matches:
        if match not in sys.path:
            sys.path.insert(0, match)

try:
    from shared_dev_tools.util.execute_command import execute_command
    from shared_dev_tools.util.file_operations import ensure_directory_exists, symlink_with_check
    from shared_dev_tools.core.utilities import setup_logging

    setup_logging("INFO")

    def install_vnc_packages():
        """Install VNC and desktop packages."""
        print("Installing VNC and desktop packages...")

        packages = [
            "tigervnc-standalone-server",
            "x11vnc",
            "xfce4",
            "xfce4-goodies",
            "onboard"
        ]

        # Update package list
        execute_command(["sudo", "apt", "update"])

        # Install packages
        result = execute_command(["sudo", "apt", "install", "-y"] + packages)
        return result[0] == 0

    def configure_vnc_user(username):
        """Configure VNC for the specified user."""
        print(f"Configuring VNC for user: {username}")

        home_dir = Path(f"/home/{username}")
        vnc_dir = home_dir / ".vnc"

        # Create VNC directory
        ensure_directory_exists(vnc_dir)

        # Set password (use username as password for simplicity)
        passwd_file = vnc_dir / "passwd"
        result = execute_command(["sudo", "-u", username, "bash", "-c", f"echo '{username}' | vncpasswd -f > {passwd_file}"])
        if result[0] == 0:
            execute_command(["sudo", "chmod", "600", str(passwd_file)])

        # Create xstartup script
        xstartup_content = """#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec /usr/bin/startxfce4 &
"""
        xstartup_file = vnc_dir / "xstartup"
        with open(xstartup_file, 'w') as f:
            f.write(xstartup_content)
        execute_command(["sudo", "chmod", "+x", str(xstartup_file)])
        execute_command(["sudo", "chown", f"{username}:{username}", str(xstartup_file)])

        print(f"Configured VNC for user {username}")
        return True

    def create_vnc_service(username):
        """Create systemd service for VNC."""
        print(f"Creating VNC systemd service for user: {username}")

        service_content = f"""[Unit]
Description=VNC Server for {username} (Mobile/Touchscreen Optimized)
After=syslog.target network.target

[Service]
Type=forking
User={username}
Group={username}
WorkingDirectory=/home/{username}
ExecStartPre=-/usr/bin/vncserver -kill :1
# Mobile-optimized: 1280x720 for tablets, depth 24, pixel format optimized for mobile VNC clients
ExecStart=/usr/bin/vncserver :1 -geometry 1280x720 -depth 24 -pixelformat RGB888 -dpi 96
ExecStop=/usr/bin/vncserver -kill :1

[Install]
WantedBy=multi-user.target
"""

        service_file = f"/etc/systemd/system/vncserver@{username}.service"
        with open("/tmp/vnc_service", 'w') as f:
            f.write(service_content)

        execute_command(["sudo", "mv", "/tmp/vnc_service", service_file])
        execute_command(["sudo", "systemctl", "daemon-reload"])
        execute_command(["sudo", "systemctl", "enable", f"vncserver@{username}"])

        print(f"Created and enabled VNC service for {username}")
        return True

    if __name__ == "__main__":
        username = os.environ.get("TARGET_USER", "mia")

        success = True
        success &= install_vnc_packages()
        success &= configure_vnc_user(username)
        success &= create_vnc_service(username)

        if success:
            print(f"✓ VNC server configured successfully for user {username}")
            sys.exit(0)
        else:
            print(f"✗ Failed to configure VNC server for user {username}")
            sys.exit(1)

except ImportError as e:
    print(f"SpareTools utilities not available: {e}")
    print("Falling back to shell-based VNC setup...")

    # Fallback to shell commands
    username = os.environ.get("TARGET_USER", "mia")

    # Install packages
    subprocess.run(["sudo", "apt", "update"], check=True)
    subprocess.run(["sudo", "apt", "install", "-y",
                   "tigervnc-standalone-server", "x11vnc",
                   "xfce4", "xfce4-goodies", "onboard"], check=True)

    # Configure VNC for user
    home_dir = f"/home/{username}"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", f"{home_dir}/.vnc"], check=True)
    subprocess.run(["sudo", "-u", username, "bash", "-c",
                   f"echo '{username}' | vncpasswd -f > {home_dir}/.vnc/passwd"], check=True)
    subprocess.run(["sudo", "chmod", "600", f"{home_dir}/.vnc/passwd"], check=True)

    # Create xstartup
    xstartup_content = """#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec /usr/bin/startxfce4 &
"""
    with open("/tmp/xstartup", 'w') as f:
        f.write(xstartup_content)
    subprocess.run(["sudo", "mv", "/tmp/xstartup", f"{home_dir}/.vnc/xstartup"], check=True)
    subprocess.run(["sudo", "chmod", "+x", f"{home_dir}/.vnc/xstartup"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{home_dir}/.vnc/xstartup"], check=True)

    # Create systemd service
    service_content = f"""[Unit]
Description=VNC Server for {username}
After=syslog.target network.target

[Service]
Type=forking
User={username}
Group={username}
WorkingDirectory=/home/{username}
ExecStartPre=-/usr/bin/vncserver -kill :1
ExecStart=/usr/bin/vncserver :1 -geometry 1280x720
ExecStop=/usr/bin/vncserver -kill :1

[Install]
WantedBy=multi-user.target
"""
    with open("/tmp/vnc_service", 'w') as f:
        f.write(service_content)
    subprocess.run(["sudo", "mv", "/tmp/vnc_service", f"/etc/systemd/system/vncserver@{username}.service"], check=True)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", f"vncserver@{username}"], check=True)

    print(f"✓ VNC server configured for user {username} (fallback method)")
    sys.exit(0)
EOF

    run_remote "
        $(setup_python_env_for_sparetools)
        PY_CMD=\$($(get_bundled_python_cmd))
        \$PY_CMD /tmp/setup_vnc_server.py
    "

    echo -e "${GREEN}✓${NC} VNC server setup complete using SpareTools utilities"
}

# Function to configure touchscreen desktop using SpareTools utilities
configure_touchscreen_desktop() {
    echo -e "${BLUE}Configuring touchscreen-friendly desktop using SpareTools utilities...${NC}"

    # Create Python script for desktop configuration
    cat > /tmp/configure_touchscreen_desktop.py << 'EOF'
#!/usr/bin/env python3
"""
Configure touchscreen desktop using SpareTools shared dev tools utilities.
"""

import sys
import os
from pathlib import Path

# Find SpareTools shared dev tools from Conan cache (similar to bootstrap scripts)
def find_sparetools_utils():
    """Find sparetools-shared-dev-tools in Conan cache."""
    import glob
    conan_cache = os.path.expanduser('~/.conan2/p')
    if os.path.exists(conan_cache):
        # Find sparetools-shared-dev-tools package directory
        pattern = os.path.join(conan_cache, 'sparetools-shared-dev-tools*', 'package', '*', 'shared_dev_tools')
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return None

# Add SpareTools shared dev tools to path
utils_path = find_sparetools_utils()
if utils_path:
    sys.path.insert(0, utils_path)

# Also check venv and bundled Python site-packages
for path_pattern in [
    '/opt/mia-python/lib/python3.*/site-packages',
    os.path.join(os.path.expanduser('~'), '.local', 'lib', 'python3.*', 'site-packages')
]:
    import glob
    matches = glob.glob(path_pattern)
    for match in matches:
        if match not in sys.path:
            sys.path.insert(0, match)

try:
    from shared_dev_tools.util.execute_command import execute_command
    from shared_dev_tools.util.file_operations import ensure_directory_exists
    from shared_dev_tools.core.utilities import setup_logging

    setup_logging("INFO")

    def configure_xfce_settings(username):
        """Configure XFCE settings for mobile/touchscreen (Plasma Mobile-like)."""
        print(f"Configuring XFCE settings for mobile/touchscreen user: {username}")

        config_dir = Path(f"/home/{username}/.config/xfce4/xfconf/xfce-perchannel-xml")
        ensure_directory_exists(config_dir)

        # Mobile-optimized panel configuration (bottom panel like mobile, larger icons)
        panel_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=10;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="size" type="uint" value="64"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="icon-size" type="uint" value="48"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
      </property>
    </property>
  </property>
</channel>
"""

        # Mobile-optimized window manager settings (touch-friendly)
        wm_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Default"/>
    <property name="title_font" type="string" value="Sans Bold 12"/>
    <property name="button_layout" type="string" value="CHM|"/>
    <property name="double_click_action" type="string" value="maximize"/>
    <property name="double_click_distance" type="int" value="5"/>
    <property name="double_click_time" type="int" value="250"/>
    <property name="raise_on_click" type="bool" value="true"/>
    <property name="raise_with_any_button" type="bool" value="true"/>
    <property name="click_to_focus" type="bool" value="true"/>
    <property name="focus_delay" type="int" value="250"/>
  </property>
</channel>
"""

        # Mobile-optimized desktop settings (larger icons, touch-friendly)
        desktop_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="image-style" type="int" value="5"/>
        </property>
      </property>
    </property>
  </property>
  <property name="desktop-icons" type="empty">
    <property name="icon-size" type="uint" value="64"/>
    <property name="tooltip-size" type="uint" value="80"/>
    <property name="single-click" type="bool" value="true"/>
  </property>
</channel>
"""

        # Session configuration
        session_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="SessionName" type="string" value="Default"/>
  <property name="IsManaged" type="bool" value="true"/>
  <property name="SaveOnExit" type="bool" value="true"/>
</channel>
"""

        # Write configuration files
        panel_file = config_dir / "xfce4-panel.xml"
        session_file = config_dir / "xfce4-session.xml"
        wm_file = config_dir / "xfwm4.xml"
        desktop_file = config_dir / "xfce4-desktop.xml"

        with open(panel_file, 'w') as f:
            f.write(panel_config)
        with open(session_file, 'w') as f:
            f.write(session_config)
        with open(wm_file, 'w') as f:
            f.write(wm_config)
        with open(desktop_file, 'w') as f:
            f.write(desktop_config)

        # Set ownership
        for config_file in [panel_file, session_file, wm_file, desktop_file]:
            execute_command(["sudo", "chown", f"{username}:{username}", str(config_file)])

        print(f"Configured XFCE settings for mobile/touchscreen")
        return True

    def configure_on_screen_keyboard(username):
        """Configure on-screen keyboard for touchscreen."""
        print(f"Configuring on-screen keyboard for user: {username}")

        autostart_dir = Path(f"/home/{username}/.config/autostart")
        ensure_directory_exists(autostart_dir)

        onboard_config = """[Desktop Entry]
Type=Application
Name=Onboard
Comment=On-screen keyboard for touchscreen
Exec=onboard
StartupNotify=false
Terminal=false
"""

        onboard_file = autostart_dir / "onboard.desktop"
        with open(onboard_file, 'w') as f:
            f.write(onboard_config)

        execute_command(["sudo", "chown", f"{username}:{username}", str(onboard_file)])

        print(f"Configured on-screen keyboard for touchscreen")
        return True

    if __name__ == "__main__":
        username = os.environ.get("TARGET_USER", "mia")

        success = True
        success &= configure_xfce_settings(username)
        success &= configure_on_screen_keyboard(username)

        if success:
            print(f"✓ Touchscreen desktop configured successfully for user {username}")
            sys.exit(0)
        else:
            print(f"✗ Failed to configure touchscreen desktop for user {username}")
            sys.exit(1)

except ImportError as e:
    print(f"SpareTools utilities not available: {e}")
    print("Falling back to shell-based desktop configuration...")

    # Fallback to shell commands
    import subprocess

    username = os.environ.get("TARGET_USER", "mia")
    home_dir = f"/home/{username}"

    # Configure XFCE settings
    config_dir = f"{home_dir}/.config/xfce4/xfconf/xfce-perchannel-xml"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", config_dir], check=True)

    panel_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=6;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
      </property>
    </property>
  </property>
</channel>
"""

    session_config = """<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="SessionName" type="string" value="Default"/>
  <property name="IsManaged" type="bool" value="true"/>
</channel>
"""

    with open("/tmp/xfce4-panel.xml", 'w') as f:
        f.write(panel_config)
    with open("/tmp/xfce4-session.xml", 'w') as f:
        f.write(session_config)

    subprocess.run(["sudo", "mv", "/tmp/xfce4-panel.xml", f"{config_dir}/"], check=True)
    subprocess.run(["sudo", "mv", "/tmp/xfce4-session.xml", f"{config_dir}/"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{config_dir}/xfce4-panel.xml"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{config_dir}/xfce4-session.xml"], check=True)

    # Configure on-screen keyboard
    autostart_dir = f"{home_dir}/.config/autostart"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", autostart_dir], check=True)

    onboard_config = """[Desktop Entry]
Type=Application
Name=Onboard
Comment=On-screen keyboard for touchscreen
Exec=onboard
StartupNotify=false
Terminal=false
"""
    with open("/tmp/onboard.desktop", 'w') as f:
        f.write(onboard_config)

    subprocess.run(["sudo", "mv", "/tmp/onboard.desktop", f"{autostart_dir}/"], check=True)
    subprocess.run(["sudo", "chown", f"{username}:{username}", f"{autostart_dir}/onboard.desktop"], check=True)

    print(f"✓ Touchscreen desktop configured for user {username} (fallback method)")
    sys.exit(0)
EOF

    run_remote "
        $(setup_python_env_for_sparetools)
        PY_CMD=\$($(get_bundled_python_cmd))
        \$PY_CMD /tmp/configure_touchscreen_desktop.py
    "

    echo -e "${GREEN}✓${NC} Touchscreen desktop configuration complete using SpareTools utilities"
}

# Function to setup user shell configuration using SpareTools utilities
setup_user_shell() {
    echo -e "${BLUE}Setting up user shell configuration using SpareTools utilities...${NC}"

    # Create Python script for shell configuration
    cat > /tmp/setup_user_shell.py << 'EOF'
#!/usr/bin/env python3
"""
Setup user shell configuration using SpareTools shared dev tools utilities.
"""

import sys
import os
from pathlib import Path

# Find SpareTools shared dev tools from Conan cache (similar to bootstrap scripts)
def find_sparetools_utils():
    """Find sparetools-shared-dev-tools in Conan cache."""
    import glob
    conan_cache = os.path.expanduser('~/.conan2/p')
    if os.path.exists(conan_cache):
        # Find sparetools-shared-dev-tools package directory
        pattern = os.path.join(conan_cache, 'sparetools-shared-dev-tools*', 'package', '*', 'shared_dev_tools')
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return None

# Add SpareTools shared dev tools to path
utils_path = find_sparetools_utils()
if utils_path:
    sys.path.insert(0, utils_path)

# Also check venv and bundled Python site-packages
for path_pattern in [
    '/opt/mia-python/lib/python3.*/site-packages',
    os.path.join(os.path.expanduser('~'), '.local', 'lib', 'python3.*', 'site-packages')
]:
    import glob
    matches = glob.glob(path_pattern)
    for match in matches:
        if match not in sys.path:
            sys.path.insert(0, match)

try:
    from shared_dev_tools.util.execute_command import execute_command
    from shared_dev_tools.util.file_operations import ensure_directory_exists
    from shared_dev_tools.core.utilities import setup_logging

    setup_logging("INFO")

    def configure_bashrc(username, deploy_dir, web_url, apk_url):
        """Configure .bashrc with MIA environment."""
        print(f"Configuring .bashrc for user: {username}")

        home_dir = Path(f"/home/{username}")
        bashrc_file = home_dir / ".bashrc"

        # Helper function to resolve Python paths at runtime (similar to bootstrap scripts)
        bashrc_content = f"""

# MIA Car Assistant Environment
# Resolve Python paths dynamically using SpareTools pattern
_mia_setup_python_path() {{
    local PYTHONPATH=\"\"
    
    # Add venv site-packages
    if [ -d \"{deploy_dir}/venv/lib\" ]; then
        local VENV_SITE=$(find \"{deploy_dir}/venv/lib\" -type d -name \"site-packages\" 2>/dev/null | head -1)
        if [ -n \"$VENV_SITE\" ]; then
            PYTHONPATH=\"$VENV_SITE\"
        fi
    fi
    
    # Add bundled Python site-packages
    if [ -x /opt/mia-python/bin/python3 ] && [ -d /opt/mia-python/lib ]; then
        local BUNDLED_SITE=$(find /opt/mia-python/lib -type d -name \"site-packages\" 2>/dev/null | head -1)
        if [ -n \"$BUNDLED_SITE\" ]; then
            PYTHONPATH=\"$BUNDLED_SITE:$PYTHONPATH\"
        fi
    fi
    
    # Add SpareTools utilities from Conan cache
    local CONAN_CACHE=\"$HOME/.conan2/p\"
    local SPARETOOLS_UTILS=$(find \"$CONAN_CACHE\" -type d -path \"*/sparetools-shared-dev-tools*/package/*/shared_dev_tools\" 2>/dev/null | head -1)
    if [ -n \"$SPARETOOLS_UTILS\" ]; then
        PYTHONPATH=\"$(dirname $SPARETOOLS_UTILS):$PYTHONPATH\"
    fi
    
    export PYTHONPATH
}}
_mia_setup_python_path

export PATH="/opt/mia-python/bin:{deploy_dir}/venv/bin:$PATH"

# MIA aliases
alias mia-status="sudo systemctl status mia-car-assistant"
alias mia-start="sudo systemctl start mia-car-assistant"
alias mia-stop="sudo systemctl stop mia-car-assistant"
alias mia-restart="sudo systemctl restart mia-car-assistant"
alias mia-logs="sudo journalctl -u mia-car-assistant -f"

# VNC aliases
alias vnc-start="sudo systemctl start vncserver@{username}"
alias vnc-stop="sudo systemctl stop vncserver@{username}"
alias vnc-status="sudo systemctl status vncserver@{username}"

"""

        # Append to existing .bashrc
        if bashrc_file.exists():
            with open(bashrc_file, 'a') as f:
                f.write(bashrc_content)
        else:
            with open(bashrc_file, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(bashrc_content)

        execute_command(["sudo", "chown", f"{username}:{username}", str(bashrc_file)])

        print(f"Configured .bashrc for MIA environment")
        return True

    def configure_profile(username, deploy_dir, web_url, apk_url):
        """Configure .profile with MIA settings."""
        print(f"Configuring .profile for user: {username}")

        home_dir = Path(f"/home/{username}")
        profile_file = home_dir / ".profile"

        profile_content = f"""

# MIA Car Assistant Profile Settings
export MIA_WEB_URL="{web_url}"
export MIA_APK_URL="{apk_url}"
export MIA_DEPLOY_DIR="{deploy_dir}"

"""

        # Append to existing .profile
        if profile_file.exists():
            with open(profile_file, 'a') as f:
                f.write(profile_content)
        else:
            with open(profile_file, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(profile_content)

        execute_command(["sudo", "chown", f"{username}:{username}", str(profile_file)])

        print(f"Configured .profile for MIA settings")
        return True

    if __name__ == "__main__":
        username = os.environ.get("TARGET_USER", "mia")
        deploy_dir = os.environ.get("DEPLOY_DIR", "/opt/mia-car-assistant")
        web_url = os.environ.get("MIA_WEB_URL", "http://localhost:8080")
        apk_url = os.environ.get("MIA_APK_URL", "https://github.com/sparesparrow/mia/releases/latest/download/mia-car-assistant.apk")

        success = True
        success &= configure_bashrc(username, deploy_dir, web_url, apk_url)
        success &= configure_profile(username, deploy_dir, web_url, apk_url)

        if success:
            print(f"✓ Shell configuration completed successfully for user {username}")
            sys.exit(0)
        else:
            print(f"✗ Failed to configure shell for user {username}")
            sys.exit(1)

except ImportError as e:
    print(f"SpareTools utilities not available: {e}")
    print("Falling back to shell-based configuration...")

    # Fallback to shell commands
    import subprocess

    username = os.environ.get("TARGET_USER", "mia")
    deploy_dir = os.environ.get("DEPLOY_DIR", "/opt/mia-car-assistant")
    web_url = os.environ.get("MIA_WEB_URL", "http://localhost:8080")
    apk_url = os.environ.get("MIA_APK_URL", "https://github.com/sparesparrow/mia/releases/latest/download/mia-car-assistant.apk")

    # Configure .bashrc
    bashrc_content = f"""

# MIA Car Assistant Environment
export PYTHONPATH="{deploy_dir}/venv/lib/python3.*/site-packages:/opt/mia-python/lib/python3.*/site-packages:$PYTHONPATH"
export PATH="/opt/mia-python/bin:{deploy_dir}/venv/bin:$PATH"

# MIA aliases
alias mia-status="sudo systemctl status mia-car-assistant"
alias mia-start="sudo systemctl start mia-car-assistant"
alias mia-stop="sudo systemctl stop mia-car-assistant"
alias mia-restart="sudo systemctl restart mia-car-assistant"
alias mia-logs="sudo journalctl -u mia-car-assistant -f"

# VNC aliases
alias vnc-start="sudo systemctl start vncserver@{username}"
alias vnc-stop="sudo systemctl stop vncserver@{username}"
alias vnc-status="sudo systemctl status vncserver@{username}"

"""
    subprocess.run(["sudo", "-u", username, "bash", "-c", f"echo '{bashrc_content}' >> ~/.bashrc"], check=True)

    # Configure .profile
    profile_content = f"""

# MIA Car Assistant Profile Settings
export MIA_WEB_URL="{web_url}"
export MIA_APK_URL="{apk_url}"
export MIA_DEPLOY_DIR="{deploy_dir}"

"""
    subprocess.run(["sudo", "-u", username, "bash", "-c", f"echo '{profile_content}' >> ~/.profile"], check=True)

    print(f"✓ Shell configuration completed for user {username} (fallback method)")
    sys.exit(0)
EOF

    run_remote "
        $(setup_python_env_for_sparetools)
        PY_CMD=\$($(get_bundled_python_cmd))
        \$PY_CMD /tmp/setup_user_shell.py
    "

    echo -e "${GREEN}✓${NC} User shell configuration complete using SpareTools utilities"
}

# Function to setup MOTD with QR codes
setup_motd_qr_codes() {
    echo -e "${BLUE}Setting up MOTD with QR codes and instructions...${NC}"

    run_remote "
        # Install qrencode for QR code generation
        sudo apt install -y qrencode

        # Create persistent directory for QR codes
        sudo mkdir -p $DEPLOY_DIR/qr-codes
        sudo chmod 755 $DEPLOY_DIR/qr-codes

        # Generate QR codes persistently (regenerate on each login if URLs change)
        WEB_URL=\"$MIA_WEB_URL\"
        APK_URL=\"$MIA_APK_URL\"
        CLOUDSMITH_URL=\"$MIA_APK_CLOUDSMITH_URL\"

        echo \"\$WEB_URL\" | qrencode -t ANSIUTF8 -o $DEPLOY_DIR/qr-codes/web_qr.txt
        echo \"\$APK_URL\" | qrencode -t ANSIUTF8 -o $DEPLOY_DIR/qr-codes/apk_qr.txt
        
        # Generate Cloudsmith QR code if provided
        if [ -n \"\$CLOUDSMITH_URL\" ]; then
            echo \"\$CLOUDSMITH_URL\" | qrencode -t ANSIUTF8 -o $DEPLOY_DIR/qr-codes/apk_cloudsmith_qr.txt
        fi

        # Create MOTD script
        cat > /tmp/mia-motd.sh << 'MOTDEOF'
#!/bin/bash

# MIA Car Assistant - Message of the Day
# Load URLs from environment or defaults
WEB_URL=\"\${MIA_WEB_URL:-http://\$(hostname -I | awk '{print \$1}'):8080}\"
APK_URL=\"\${MIA_APK_URL:-https://github.com/sparesparrow/mia/releases/latest/download/mia-car-assistant.apk}\"
CLOUDSMITH_URL=\"\${MIA_APK_CLOUDSMITH_URL:-}\"
VNC_IP=\"\$(hostname -I | awk '{print \$1}')\"
QR_DIR=\"$DEPLOY_DIR/qr-codes\"

# Regenerate QR codes if URLs have changed
if [ ! -f \"\$QR_DIR/web_qr.txt\" ] || ! grep -q \"\$WEB_URL\" \"\$QR_DIR/web_qr.txt\" 2>/dev/null; then
    echo \"\$WEB_URL\" | qrencode -t ANSIUTF8 -o \"\$QR_DIR/web_qr.txt\" 2>/dev/null || true
fi
if [ ! -f \"\$QR_DIR/apk_qr.txt\" ] || ! grep -q \"\$APK_URL\" \"\$QR_DIR/apk_qr.txt\" 2>/dev/null; then
    echo \"\$APK_URL\" | qrencode -t ANSIUTF8 -o \"\$QR_DIR/apk_qr.txt\" 2>/dev/null || true
fi
if [ -n \"\$CLOUDSMITH_URL\" ] && ([ ! -f \"\$QR_DIR/apk_cloudsmith_qr.txt\" ] || ! grep -q \"\$CLOUDSMITH_URL\" \"\$QR_DIR/apk_cloudsmith_qr.txt\" 2>/dev/null); then
    echo \"\$CLOUDSMITH_URL\" | qrencode -t ANSIUTF8 -o \"\$QR_DIR/apk_cloudsmith_qr.txt\" 2>/dev/null || true
fi

echo \"\"
echo \"╔══════════════════════════════════════════════════════════════════════════════╗\"
echo \"║                           🚗 MIA Car Assistant 🚗                           ║\"
echo \"║                                                                              ║\"
echo \"║  Mobile Intelligent Assistant for Automotive Applications                   ║\"
echo \"║                                                                              ║\"
echo \"║  Web Interface QR Code:                                                       ║\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"

# Display web interface QR code
if [ -f \"\$QR_DIR/web_qr.txt\" ]; then
    cat \"\$QR_DIR/web_qr.txt\"
else
    echo \"    Web URL: \$WEB_URL\"
fi

echo \"\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
echo \"║  APK Download QR Code (GitHub):                                              ║\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"

# Display GitHub APK download QR code
if [ -f \"\$QR_DIR/apk_qr.txt\" ]; then
    cat \"\$QR_DIR/apk_qr.txt\"
else
    echo \"    APK URL (GitHub): \$APK_URL\"
fi

# Display Cloudsmith QR code if available
if [ -n \"\$CLOUDSMITH_URL\" ] && [ -f \"\$QR_DIR/apk_cloudsmith_qr.txt\" ]; then
    echo \"\"
    echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
    echo \"║  APK Download QR Code (Cloudsmith):                                         ║\"
    echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
    cat \"\$QR_DIR/apk_cloudsmith_qr.txt\"
fi

echo \"\"
echo \"╠══════════════════════════════════════════════════════════════════════════════╣\"
echo \"║  Remote Operation Instructions:                                              ║\"
echo \"║                                                                              ║\"
echo \"║  1. Scan web QR code above to access web interface                          ║\"
echo \"║  2. Scan APK QR code to download mobile app (GitHub or Cloudsmith)          ║\"
echo \"║  3. Connect via VNC: vnc://\$VNC_IP:5901                                      ║\"
echo \"║  4. Use touchscreen-friendly mobile interface (Plasma Mobile-like)          ║\"
echo \"║                                                                              ║\"
echo \"║  Commands:                                                                   ║\"
echo \"║    • mia-status   - Check MIA service status                                ║\"
echo \"║    • mia-start    - Start MIA service                                       ║\"
echo \"║    • mia-stop     - Stop MIA service                                        ║\"
echo \"║    • mia-restart  - Restart MIA service                                     ║\"
echo \"║    • mia-logs     - View MIA service logs                                   ║\"
echo \"║    • vnc-start    - Start VNC server                                        ║\"
echo \"║    • vnc-stop     - Stop VNC server                                         ║\"
echo \"║    • vnc-status   - Check VNC server status                                 ║\"
echo \"║                                                                              ║\"
echo \"║  Logs: sudo journalctl -u mia-car-assistant -f                             ║\"
echo \"║  VNC Logs: sudo journalctl -u vncserver@mia -f                              ║\"
echo \"║                                                                              ║\"
echo \"╚══════════════════════════════════════════════════════════════════════════════╝\"
echo \"\"
MOTDEOF

        # Install MOTD
        sudo mv /tmp/mia-motd.sh /etc/update-motd.d/99-mia-car-assistant
        sudo chmod +x /etc/update-motd.d/99-mia-car-assistant

        # Set environment variables for MOTD script
        sudo bash -c \"echo 'export MIA_WEB_URL=\\\"$MIA_WEB_URL\\\"' >> /etc/environment\"
        sudo bash -c \"echo 'export MIA_APK_URL=\\\"$MIA_APK_URL\\\"' >> /etc/environment\"
        if [ -n \"$MIA_APK_CLOUDSMITH_URL\" ]; then
            sudo bash -c \"echo 'export MIA_APK_CLOUDSMITH_URL=\\\"$MIA_APK_CLOUDSMITH_URL\\\"' >> /etc/environment\"
        fi

        # Disable default MOTD
        sudo chmod -x /etc/update-motd.d/10-uname 2>/dev/null || true

        echo '✓ MOTD configured with QR codes and remote operation instructions'
    "

    echo -e "${GREEN}✓${NC} MOTD with QR codes setup complete"
}

# Function to create backup
create_backup() {
    echo -e "${BLUE}Creating backup...${NC}"

    run_remote "sudo mkdir -p $BACKUP_DIR"
    run_remote "sudo cp -r $DEPLOY_DIR $BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true"

    echo -e "${GREEN}✓${NC} Backup created"
}

# Main deployment function
main() {
    echo -e "${GREEN}MIA Car Assistant Agent Deployment${NC}"
    echo "Target: $TARGET_USER@$TARGET_HOST"
    echo "Deploy Directory: $DEPLOY_DIR"
    echo ""

    # Pre-deployment checks
    echo -e "${BLUE}Pre-deployment checks...${NC}"
    check_raspberry_pi

    # Create backup if deploying to existing system
    if run_remote "test -d $DEPLOY_DIR"; then
        echo -e "${YELLOW}Existing deployment found. Creating backup...${NC}"
        create_backup
    fi

    # Run deployment steps
    install_system_dependencies
    install_python_dependencies
    create_mia_user
    setup_vnc_server
    configure_touchscreen_desktop
    setup_user_shell
    deploy_mia_codebase
    configure_mcp
    install_systemd_services
    configure_raspberry_pi
    setup_motd_qr_codes
    create_startup_scripts
    run_deployment_tests

    echo ""
    echo -e "${GREEN}🎉 Deployment Complete!${NC}"
    echo ""
    echo "MIA Car Assistant has been fully deployed with:"
    echo "  • User 'mia' with touchscreen-friendly VNC desktop"
    echo "  • VNC server running on port 5901"
    echo "  • On-screen keyboard for touchscreen input"
    echo "  • MOTD with QR codes for web interface and APK download"
    echo "  • Complete shell environment with MIA aliases"
    echo ""
    echo "Next steps:"
    echo "1. Connect OBD-II adapter to vehicle diagnostic port"
    echo "2. Connect RF antenna if using wireless features"
    echo "3. Configure power management for vehicle integration"
    echo "4. Start the system: $DEPLOY_DIR/start_production.sh"
    echo "5. Or use systemd: sudo systemctl start mia-car-assistant"
    echo "6. Start VNC server: sudo systemctl start vncserver@mia"
    echo ""
    echo "Remote access:"
    echo "  • VNC: vnc://$(run_remote 'hostname -I | awk '\''{print $1}'\'' || echo localhost'):5901"
    echo "  • Web Interface: $MIA_WEB_URL"
    echo "  • APK Download: $MIA_APK_URL"
    echo ""
    echo "Monitor logs:"
    echo "  • sudo journalctl -u mia-car-assistant -f"
    echo "  • sudo journalctl -u vncserver@mia -f"
    echo "  • tail -f /var/log/mia/*.log"
    echo ""
    echo "For development testing, use the local scripts:"
    echo "  • ./start_car_assistant.sh (development)"
    echo "  • ./stop_car_assistant.sh (development)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            TARGET_HOST="$2"
            shift 2
            ;;
        --user)
            TARGET_USER="$2"
            shift 2
            ;;
        --deploy-dir)
            DEPLOY_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--host HOSTNAME] [--user USERNAME] [--deploy-dir DIR]"
            echo ""
            echo "Options:"
            echo "  --host HOSTNAME    Target host for deployment (default: localhost)"
            echo "  --user USERNAME    Target user for deployment (default: pi)"
            echo "  --deploy-dir DIR   Deployment directory (default: /opt/mia-car-assistant)"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main deployment
main