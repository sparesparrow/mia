#!/bin/bash
set -e

echo "🔧 Setting up SpareTools for MIA..."

# 1. Configure Conan remote
echo "📦 Configuring Conan remote..."
conan remote add sparesparrow-conan \
  https://conan.cloudsmith.io/sparesparrow-conan/sparetools/ \
  --force || true

# 2. Install SpareTools packages
echo "📥 Installing SpareTools packages..."
conan install . --build=missing -g VirtualRunEnv

# 3. Install zipapps (optional)
if [ "$1" == "--with-zipapps" ]; then
  echo "📦 Installing SpareTools zipapps..."
  bash scripts/install-sparetools-zipapps.sh
fi

# 4. Activate environment
echo "✅ Setup complete!"
echo "Run: source .conan/activate.sh"