#!/bin/bash
set -euo pipefail

echo "🚀 Setting up AI-Servis development environment..."

# Install Python development dependencies
echo "📦 Installing Python dependencies..."
pip install --user -r requirements-dev.txt
pip install --user pre-commit

# Install Conan for C++ dependency management
echo "🔧 Setting up Conan..."
pip install --user conan
conan profile detect --force

# Set up pre-commit hooks
echo "🔒 Setting up pre-commit hooks..."
pre-commit install

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p {logs,volumes/{core-config,core-data,discovery-data,audio-config,platform-config,mqtt-data,mqtt-logs,postgres-data-dev,redis-data-dev,prometheus-data,grafana-data}}

# Set permissions
echo "🔐 Setting permissions..."
sudo chown -R vscode:vscode /workspace/volumes
sudo chown -R vscode:vscode /workspace/logs

# Install additional development tools
echo "🛠️  Installing development tools..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    clang-format \
    clang-tidy \
    valgrind \
    gdb \
    htop \
    curl \
    jq \
    tree \
    ripgrep \
    fd-find \
    bat

# Install ESP32 development tools (for firmware development)
echo "🔌 Installing ESP32 tools..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-setuptools \
    git \
    wget \
    flex \
    bison \
    gperf \
    python3-serial \
    libffi-dev \
    libssl-dev \
    dfu-util \
    libusb-1.0-0

# Install Android development tools
echo "📱 Installing Android tools..."
sudo apt-get install -y openjdk-21-jdk

# Configure Git (if not already configured)
if [ -z "$(git config --global user.name)" ]; then
    echo "⚠️  Git user.name not configured. Please run:"
    echo "   git config --global user.name 'Your Name'"
    echo "   git config --global user.email 'your.email@example.com'"
fi

# Install Node.js dependencies for web development
echo "🌐 Installing Node.js dependencies..."
if [ -f "web/package.json" ]; then
    cd web && npm install && cd ..
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🔧 Available commands:"
echo "  - docker compose -f infra/docker/docker-compose.yml up -d              # Start all services"
echo "  - docker compose -f infra/docker/docker-compose.dev.yml up -d  # Start dev services"
echo "  - ./scripts/dev-setup.sh            # Run development setup"
echo "  - ./scripts/health-check.sh         # Check service health"
echo "  - conan install . --build missing   # Install C++ dependencies"
echo "  - pre-commit run --all-files        # Run code quality checks"
echo ""
echo "📖 Documentation: http://localhost:8000"
echo "📊 Monitoring: http://localhost:3000 (Grafana)"
echo "🔍 Metrics: http://localhost:9090 (Prometheus)"