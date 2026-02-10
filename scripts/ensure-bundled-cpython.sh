#!/bin/bash
#
# ensure-bundled-cpython.sh - Ensure bundled CPython is used for MIA execution
#
# This script ensures that MIA Python scripts use the bundled CPython executable
# instead of system Python. It should be run after MIA installation.
#
# Usage: ./ensure-bundled-cpython.sh [install_dir]
#

set -e

# Default installation directory
INSTALL_DIR="${1:-/opt/mia/rpi}"
CPYTHON_BIN="$INSTALL_DIR/bin/python3"

echo "🔍 Ensuring bundled CPython is available for MIA..."

# Check if bundled CPython exists
if [[ ! -x "$CPYTHON_BIN" ]]; then
    echo "❌ Bundled CPython not found at: $CPYTHON_BIN"
    echo "   Please ensure MIA is properly installed with sparetools-cpython dependency"
    exit 1
fi

echo "✅ Bundled CPython found at: $CPYTHON_BIN"

# Verify Python version and functionality
echo "📋 Verifying bundled Python functionality..."
if ! "$CPYTHON_BIN" --version >/dev/null 2>&1; then
    echo "❌ Bundled Python is not executable"
    exit 1
fi

if ! "$CPYTHON_BIN" -c "import sys; print(f'Python {sys.version}')"; then
    echo "❌ Bundled Python cannot import standard library"
    exit 1
fi

echo "✅ Bundled Python is functional"

# Create environment file for systemd services
ENV_FILE="/etc/mia/environment"
echo "📝 Creating environment configuration at: $ENV_FILE"

sudo mkdir -p "$(dirname "$ENV_FILE")"

sudo tee "$ENV_FILE" > /dev/null << EOF
# MIA Environment Configuration
# Ensures bundled CPython is used for all Python execution

# Python Configuration
PYTHONHOME=$INSTALL_DIR
PATH=$INSTALL_DIR/bin:/usr/bin:/usr/local/bin
PYTHONPATH=$INSTALL_DIR/lib/python3.12:$PYTHONPATH

# MIA Specific
MIA_INSTALL_DIR=$INSTALL_DIR
MIA_PYTHON=$CPYTHON_BIN
EOF

echo "✅ Environment configuration created"

# Verify systemd services are configured correctly
echo "🔧 Verifying systemd service configurations..."

SERVICES=(
    "mia-api.service"
    "mia-gpio-worker.service"
    "mia-serial-bridge.service"
    "mia-obd-worker.service"
    "mia-ble-obd.service"
)

for service in "${SERVICES[@]}"; do
    service_file="/etc/systemd/system/$service"
    if [[ -f "$service_file" ]]; then
        if ! grep -q "$CPYTHON_BIN" "$service_file"; then
            echo "⚠️  Service $service may not be using bundled Python"
            echo "   Please ensure ExecStart uses: $CPYTHON_BIN"
        else
            echo "✅ Service $service uses bundled Python"
        fi
    else
        echo "ℹ️  Service $service not installed yet"
    fi
done

# Create convenience script for manual execution
CONVENIENCE_SCRIPT="/usr/local/bin/mia-python"
echo "📝 Creating convenience script at: $CONVENIENCE_SCRIPT"

sudo tee "$CONVENIENCE_SCRIPT" > /dev/null << EOF
#!/bin/bash
# MIA Python wrapper - ensures bundled CPython is used
exec "$CPYTHON_BIN" "\$@"
EOF

sudo chmod +x "$CONVENIENCE_SCRIPT"

echo "✅ Convenience script created"

# Test the setup
echo "🧪 Testing MIA Python execution..."
if "$CPYTHON_BIN" -c "print('MIA Python setup successful!')"; then
    echo "✅ MIA Python setup verified"
else
    echo "❌ MIA Python setup failed"
    exit 1
fi

echo ""
echo "🎉 Bundled CPython setup complete!"
echo ""
echo "Usage:"
echo "  Direct execution: $CPYTHON_BIN script.py"
echo "  Convenience script: mia-python script.py"
echo "  Systemd services: Automatically configured"
echo ""
echo "Environment variables set in: $ENV_FILE"